"""Generate fakes, roots and sentences through the Message Batches API (one request per word).

FAKES.md is the system prompt (prompt-cached); validate.py checks every answer. Work order is the frozen
sequence: first the unwritten year-one WordNet spares (in_031..), then the Wiktionary pool (wk_in_NNN).

    python batch_generate.py prepare               cut data/wk_pool.json into data/batches/wk_in_NNN.json
    python batch_generate.py estimate [--count N]  cost estimate, no API spend (--exact counts tokens via the free endpoint)
    python batch_generate.py submit --count N      send the next N unwritten words as one batch (asks before spending)
    python batch_generate.py submit --retry        resend words whose answers failed validation, with the problems listed
    python batch_generate.py status                progress of submitted batches
    python batch_generate.py collect               fetch finished batches, validate, write generated/*.json, report spend

State lives in data/api/ (batches.json, results.jsonl). Needs ANTHROPIC_API_KEY for submit/status/collect.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from sequence import BATCH, clean_ety
from validate import check_entry

ROOT = Path(__file__).resolve().parent.parent
BATCHES = ROOT / "data" / "batches"
GEN = ROOT / "pipeline" / "generated"
API = ROOT / "data" / "api"
STATE = API / "batches.json"
RESULTS = API / "results.jsonl"

MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TOKENS = 8000
# Message Batches prices, USD per million tokens (half the standard rate). Cache writes use the 5-minute TTL (1.25x).
PRICES = {
    "claude-opus-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.10, "cache_write": 2.50},
    "claude-sonnet-5-5": {"in": 1.00, "out": 5.00, "cache_read": 0.10, "cache_write": 1.25},
    "claude-haiku-5-5": {"in": 0.05, "out": 0.25, "cache_read": 0.005, "cache_write": 0.0625},
}
# Rough thinking tokens per word by effort, used only until a pilot batch gives measured numbers.
THINKING_GUESS = {"low": 400, "medium": 1200, "high": 3000}
CHARS_PER_TOKEN = 3.2

SCHEMA = {
    "type": "object",
    "properties": {
        "w": {"type": "string"},
        "ok": {"type": "boolean"},
        "d": {"type": "string"},
        "f": {"type": "array", "items": {"type": "string"}},
        "r": {"type": "string"},
        "s": {"type": "string"},
        "s_new": {"type": "boolean"},
        "p": {"type": "string"},
    },
    "required": ["w", "ok", "d", "f", "r", "s", "s_new", "p"],
    "additionalProperties": False,
}
CONTRACT = """
# Output for this request

You get one word per request. Reply with a single JSON object: {"w", "ok", "d", "f", "r", "s", "s_new", "p"}.
- Year-one (WordNet) words: the real definition is given as "d"; return "d" and "p" as empty strings.
- Wiktionary words: choose the word (keep or reject), then return "d" as an excerpt of one of "senses", and "p" per the Pronunciation rules.
- "s_new" is true only when you wrote the sentence yourself because no example fits.
- When rejecting: "ok": false and empty strings / empty list everywhere else.
- If the request lists problems with an earlier answer, fix every one of them.
"""


def system_blocks():
    return [{"type": "text", "text": (ROOT / "pipeline" / "FAKES.md").read_text() + CONTRACT,
             "cache_control": {"type": "ephemeral"}}]


# ---------- work list ----------

def wk_row(r):
    return {"w": r["w"], "pos": r["pos"], "senses": r["senses"], "ety": clean_ety(r["ety"])[:600],
            "examples": r["examples"], "p": r["p"]}


def prepare():
    pool = json.loads((ROOT / "data" / "wk_pool.json").read_text())
    BATCHES.mkdir(parents=True, exist_ok=True)
    wrote = 0
    for b in range(0, len(pool), BATCH):
        path = BATCHES / f"wk_in_{b // BATCH:03d}.json"
        rows = [wk_row(r) for r in pool[b:b + BATCH]]
        if path.exists():
            if json.loads(path.read_text()) != rows:
                sys.exit(f"{path.name} already exists with different words; the pool must not change once cut")
            continue
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=0))
        wrote += 1
    print(f"{len(pool)} Wiktionary words in {-(-len(pool) // BATCH)} batches ({wrote} new files)")


def batch_names():
    """Every batch in sequence order: WordNet in_NNN first, then Wiktionary wk_in_NNN."""
    wn = sorted(p.stem[3:] for p in BATCHES.glob("in_*.json"))
    wk = sorted("wk_" + p.stem[6:] for p in BATCHES.glob("wk_in_*.json"))
    return wn + wk


def src_path(n):
    return BATCHES / (f"wk_in_{n[3:]}.json" if n.startswith("wk_") else f"in_{n}.json")


def out_path(n):
    return GEN / (f"wk_out_{n[3:]}.json" if n.startswith("wk_") else f"out_{n}.json")


def load_results():
    """Latest result per custom_id."""
    res = {}
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines():
            r = json.loads(line)
            res[r["custom_id"]] = r
    return res


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"batches": []}


def save_state(st):
    API.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1))


def items():
    """(custom_id, row, existing_output) for every word in sequence order."""
    for n in batch_names():
        src = json.loads(src_path(n).read_text())
        done = json.loads(out_path(n).read_text()) if out_path(n).exists() else []
        for i, row in enumerate(src):
            yield f"{n}-{i:02d}", row, (done[i] if i < len(done) else None)


def pending(retry=False):
    res = load_results()
    in_flight = {c for b in load_state()["batches"] if not b.get("collected") for c in b["custom_ids"]}
    for cid, row, done in items():
        if done is not None or cid in in_flight:
            continue
        r = res.get(cid)
        if retry:
            if r and r["errors"]:
                yield cid, row, r
        elif r is None:
            yield cid, row, None


# ---------- requests ----------

def user_message(row, prev=None):
    msg = "Word entry:\n" + json.dumps(row, ensure_ascii=False, indent=1)
    if "senses" not in row:
        msg += "\n\nThis is a year-one WordNet word: \"d\" above is the fixed real definition."
    if prev:
        msg += ("\n\nYour earlier answer:\n" + json.dumps(prev["out"], ensure_ascii=False)
                + "\nProblems found by the validator:\n- " + "\n- ".join(prev["errors"]))
    return msg


def params(row, model, effort, prev=None):
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system_blocks(),
        "messages": [{"role": "user", "content": user_message(row, prev)}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
    }


# ---------- cost ----------

def measured():
    """Average output tokens per word from collected results, if any."""
    rows = [r for r in load_results().values() if r.get("usage")]
    if not rows:
        return None
    return sum(r["usage"]["output_tokens"] for r in rows) / len(rows), len(rows)


def estimate(count, model, effort, exact):
    work = list(pending())[:count] if count else list(pending())
    if not work:
        print("Nothing pending.")
        return 0.0
    price = PRICES[model]
    sys_text = system_blocks()[0]["text"]
    if exact:
        import anthropic
        client = anthropic.Anthropic()
        sample = work[:: max(1, len(work) // 25)][:25]
        base = client.messages.count_tokens(model=model, system=sys_text,
                                            messages=[{"role": "user", "content": "x"}]).input_tokens
        per = [client.messages.count_tokens(model=model, system=sys_text,
                                            messages=[{"role": "user", "content": user_message(r)}]).input_tokens
               for _, r, _ in sample]
        sys_tok = base
        user_tok = sum(per) / len(per) - base
        how = f"counted with the token-counting endpoint on {len(sample)} sample words"
    else:
        sys_tok = len(sys_text) / CHARS_PER_TOKEN
        user_tok = sum(len(user_message(r)) for _, r, _ in work) / len(work) / CHARS_PER_TOKEN
        how = f"approximated at {CHARS_PER_TOKEN} characters per token (use --exact once a key is set)"
    m = measured()
    if m:
        out_tok, n_meas = m
        out_how = f"measured average from {n_meas} collected words"
    else:
        out_tok = 220 + THINKING_GUESS[effort]
        out_how = f"guess: ~220 answer tokens + ~{THINKING_GUESS[effort]} thinking tokens at effort {effort}"
    n = len(work)
    out_cost = n * out_tok * price["out"] / 1e6
    user_cost = n * user_tok * price["in"] / 1e6
    sys_nocache = n * sys_tok * price["in"] / 1e6
    # Batch requests hit the cache on a best-effort basis; assume about half do.
    sys_cache = n * sys_tok * (0.5 * price["cache_read"] + 0.5 * price["cache_write"]) / 1e6
    lo, hi = user_cost + out_cost + sys_cache, user_cost + out_cost + sys_nocache
    print(f"{n} words with {model} (Message Batches pricing, effort {effort})")
    print(f"  input:  system prompt ~{sys_tok:,.0f} tokens + word ~{user_tok:,.0f} tokens ({how})")
    print(f"  output: ~{out_tok:,.0f} tokens per word ({out_how})")
    print(f"  system prompt ${sys_cache:,.2f} (half cached) to ${sys_nocache:,.2f} (no cache hits)")
    print(f"  words   ${user_cost:,.2f}   output ${out_cost:,.2f}")
    print(f"  total   ${lo:,.2f} to ${hi:,.2f}, plus retries for answers that fail validation")
    return hi


# ---------- API steps ----------

def submit(count, retry, model, effort, yes):
    import anthropic
    work = list(pending(retry))
    if not retry:
        work = work[:count]
    if not work:
        print("Nothing to submit.")
        return
    if not yes:
        print(f"About to submit {len(work)} {'retries' if retry else 'words'}, starting at {work[0][0]} ({work[0][1]['w']}).")
        estimate(len(work), model, effort, exact=False) if not retry else None
        if input("Submit and spend? [y/N] ").strip().lower() != "y":
            print("Not submitted.")
            return
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=[
        {"custom_id": cid, "params": params(row, model, effort, prev)} for cid, row, prev in work])
    st = load_state()
    st["batches"].append({"id": batch.id, "created": dt.datetime.now().isoformat(timespec="seconds"),
                          "model": model, "effort": effort, "custom_ids": [c for c, _, _ in work]})
    save_state(st)
    print(f"Submitted {batch.id}: {len(work)} requests. Run `collect` when `status` shows it ended (usually under an hour).")


def status():
    import anthropic
    client = anthropic.Anthropic()
    for b in load_state()["batches"]:
        if b.get("collected"):
            print(f"{b['id']}  collected  ({len(b['custom_ids'])} words)")
            continue
        r = client.messages.batches.retrieve(b["id"])
        c = r.request_counts
        print(f"{b['id']}  {r.processing_status}  processing {c.processing}, succeeded {c.succeeded}, "
              f"errored {c.errored}, expired {c.expired}, canceled {c.canceled}")


def collect():
    import anthropic
    client = anthropic.Anthropic()
    st = load_state()
    rows = {cid: row for cid, row, _ in items()}
    spent = 0.0
    tally = {"accepted": 0, "rejected": 0, "invalid": 0, "failed": 0}
    API.mkdir(parents=True, exist_ok=True)
    with RESULTS.open("a") as log:
        for b in st["batches"]:
            if b.get("collected"):
                continue
            if client.messages.batches.retrieve(b["id"]).processing_status != "ended":
                print(f"{b['id']} still running")
                continue
            price = PRICES[b["model"]]
            for res in client.messages.batches.results(b["id"]):
                cid, rec = res.custom_id, {"custom_id": res.custom_id, "batch": b["id"]}
                if res.result.type != "succeeded":
                    # errored / canceled / expired: leave unrecorded so the word is picked up again by submit.
                    tally["failed"] += 1
                    continue
                msg = res.result.message
                u = msg.usage
                rec["usage"] = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                                "cache_read": u.cache_read_input_tokens or 0,
                                "cache_write": u.cache_creation_input_tokens or 0}
                spent += (u.input_tokens * price["in"] + u.output_tokens * price["out"]
                          + rec["usage"]["cache_read"] * price["cache_read"]
                          + rec["usage"]["cache_write"] * price["cache_write"]) / 1e6
                row = rows[cid]
                if msg.stop_reason == "refusal":
                    out = {"w": row["w"], "ok": False, "d": "", "f": [], "r": "", "s": "", "s_new": False, "p": ""}
                    rec.update(out=out, errors=[], note="refusal")
                elif msg.stop_reason == "max_tokens":
                    rec.update(out=None, errors=["answer was cut off at max_tokens"])
                else:
                    text = next((blk.text for blk in msg.content if blk.type == "text"), "")
                    try:
                        out = json.loads(text)
                        rec.update(out=out, errors=check_entry(row, out))
                    except json.JSONDecodeError:
                        rec.update(out=None, errors=["reply was not valid JSON"])
                if rec["errors"]:
                    tally["invalid"] += 1
                elif rec["out"]["ok"]:
                    tally["accepted"] += 1
                else:
                    tally["rejected"] += 1
                log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            b["collected"] = True
            b["cost"] = round(spent, 4)
    save_state(st)
    write_outputs()
    print(f"accepted {tally['accepted']}, rejected {tally['rejected']}, failed validation {tally['invalid']} "
          f"(resend with `submit --retry`), API errors {tally['failed']} (resent by the next `submit`)")
    print(f"spent this collect: ${spent:,.2f}")


def write_outputs():
    """Extend each generated/*.json with valid answers, in order, stopping at the first word still missing."""
    res = load_results()
    for n in batch_names():
        src = json.loads(src_path(n).read_text())
        out = json.loads(out_path(n).read_text()) if out_path(n).exists() else []
        grew = False
        for i in range(len(out), len(src)):
            r = res.get(f"{n}-{i:02d}")
            if not r or r["errors"]:
                break
            o = dict(r["out"])
            if "senses" not in src[i]:
                o = {k: o[k] for k in ("w", "f", "r", "s", "ok")}
            elif not o["ok"]:
                o = {"w": o["w"], "ok": False}
            out.append(o)
            grew = True
        if grew:
            GEN.mkdir(exist_ok=True)
            out_path(n).write_text("[\n" + ",\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n]\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["prepare", "estimate", "submit", "status", "collect"])
    ap.add_argument("--count", type=int, default=0, help="number of words (estimate: default all pending)")
    ap.add_argument("--retry", action="store_true")
    ap.add_argument("--model", default=MODEL, choices=sorted(PRICES))
    ap.add_argument("--effort", default=EFFORT, choices=sorted(THINKING_GUESS))
    ap.add_argument("--exact", action="store_true", help="estimate: count input tokens with the API (free)")
    ap.add_argument("--yes", action="store_true", help="submit without the confirmation prompt")
    a = ap.parse_args()
    if a.cmd == "prepare":
        prepare()
    elif a.cmd == "estimate":
        estimate(a.count, a.model, a.effort, a.exact)
    elif a.cmd == "submit":
        if not a.retry and a.count <= 0:
            sys.exit("submit needs --count N (start with a pilot of 40 to measure real cost and quality)")
        submit(a.count, a.retry, a.model, a.effort, a.yes)
    elif a.cmd == "status":
        status()
    else:
        collect()


if __name__ == "__main__":
    main()
