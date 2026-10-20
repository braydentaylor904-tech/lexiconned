"""Turn a Wiktionary IPA string into the game's plain respelling, e.g. /dɪˈfɛnɪstɹeɪt/ -> dih-FEN-ih-strayt."""
import re

VOWELS = ["eɪ", "aɪ", "ɔɪ", "aʊ", "oʊ", "əʊ", "ɪə", "ɛə", "eə", "ʊə", "ɑː", "ɔː", "iː", "uː", "ɜː",
          "ɝ", "ɚ", "æ", "ɑ", "ɒ", "ɛ", "e", "ɪ", "i", "ʊ", "u", "ʌ", "ə", "ɔ", "o", "a", "ɜ"]
CONS = ["tʃ", "dʒ", "p", "b", "t", "d", "k", "g", "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h", "m", "n",
        "ŋ", "l", "r", "j", "w", "x"]
ONSETS = {("p", "l"), ("b", "l"), ("k", "l"), ("g", "l"), ("f", "l"), ("s", "l"), ("p", "r"), ("b", "r"),
          ("t", "r"), ("d", "r"), ("k", "r"), ("g", "r"), ("f", "r"), ("θ", "r"), ("ʃ", "r"), ("s", "w"),
          ("t", "w"), ("k", "w"), ("d", "w"), ("g", "w"), ("s", "m"), ("s", "n"), ("s", "p"), ("s", "t"),
          ("s", "k"), ("p", "j"), ("b", "j"), ("k", "j"), ("m", "j"), ("f", "j"), ("v", "j"), ("h", "j"),
          ("s", "p", "l"), ("s", "p", "r"), ("s", "t", "r"), ("s", "k", "r"), ("s", "k", "w"), ("s", "k", "j")}
C_OUT = {"tʃ": "ch", "dʒ": "j", "θ": "th", "ð": "th", "ʃ": "sh", "ʒ": "zh", "ŋ": "ng", "j": "y", "x": "kh"}
V_OPEN = {"æ": "a", "ɑ": "ah", "ɑː": "ah", "a": "ah", "ɒ": "ah", "ɛ": "eh", "e": "eh", "ɪ": "ih", "i": "ee",
          "iː": "ee", "ʊ": "uu", "u": "oo", "uː": "oo", "ʌ": "uh", "ə": "uh", "ɔ": "aw", "ɔː": "aw", "o": "oh",
          "eɪ": "ay", "ɔɪ": "oy", "aʊ": "ow", "oʊ": "oh", "əʊ": "oh", "ɪə": "eer", "ɛə": "air", "eə": "air",
          "ʊə": "oor", "ɜː": "ur", "ɜ": "ur", "ɝ": "ur", "ɚ": "er"}
LAX = {"ɪ", "ɛ", "e", "æ", "ʌ", "ʊ", "ɒ"}
V_OPEN["ʊ"] = "oo"
V_CLOSED = {**V_OPEN, "ʊ": "uu", "ɒ": "o", "ɛ": "e", "e": "e", "ɪ": "i", "ʌ": "u", "ə": "u", "a": "a"}
V_R = {"ɑ": "ar", "ɑː": "ar", "a": "ar", "ɒ": "or", "ɔ": "or", "ɔː": "or", "o": "or", "ɛ": "air", "e": "air",
       "eə": "air", "ɛə": "air", "ɪ": "eer", "i": "eer", "iː": "eer", "ɪə": "eer", "ʊ": "oor", "u": "oor",
       "ʊə": "oor", "ə": "er", "ʌ": "ur", "ɜ": "ur", "ɜː": "ur", "æ": "ar", "aɪ": "ire", "aʊ": "our"}


def tokenize(s):
    s = s.split(",")[0].strip().strip("/[]")
    s = s.replace("(", "").replace(")", "")
    for a, b in [("͡", ""), ("ɹ", "r"), ("ɾ", "t"), ("ɫ", "l"), ("ɡ", "g"), ("ʍ", "w"), ("ɐ", "ə"), ("ᵻ", "ɪ"),
                 ("ɵ", "ə"), ("ɘ", "ə"), ("ɨ", "ɪ"), ("ʔ", ""), ("‿", ""), ("ʰ", ""), ("̃", ""), ("̯", ""),
                 ("ʲ", ""), ("ˑ", ""), ("ɚ", "ər"), ("ɝ", "ɜr"), ("ʉ", "u"), ("ä", "a"), ("ɞ", "ɜ"), ("ʏ", "ɪ"),
                 ("ø", "ɜ"), ("œ", "ɜ"), ("y", "i"), ("ɲ", "nj"), ("ʎ", "lj"), ("ɣ", "g"), ("β", "v")]:
        s = s.replace(a, b)
    s = re.sub(r"([nlm])̩", r"ə\1", s).replace("̩", "")
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch in "ˈˌ.":
            out.append(("B", ch)); i += 1; continue
        for kind, inv in (("V", VOWELS), ("C", CONS)):
            hit = next((p for p in inv if s.startswith(p, i)), None)
            if hit:
                out.append((kind, hit)); i += len(hit); break
        else:
            i += 1
    return out


def respell(ipa):
    toks = tokenize(ipa)
    nuclei = [k for k, t in enumerate(toks) if t[0] == "V"]
    if not nuclei:
        return ipa.strip("/")
    sylls = [{"on": [], "v": toks[n][1], "co": [], "stress": False, "sec": False} for n in nuclei]
    pending_stress = None
    for k, t in enumerate(toks[: nuclei[0]]):
        if t[0] == "C": sylls[0]["on"].append(t[1])
        elif t[1] == "ˈ": pending_stress = 0
        elif t[1] == "ˌ": sylls[0]["sec"] = True
    if pending_stress == 0: sylls[0]["stress"] = True
    for si in range(len(nuclei)):
        a = nuclei[si]
        b = nuclei[si + 1] if si + 1 < len(nuclei) else len(toks)
        between = toks[a + 1: b]
        if si + 1 == len(nuclei):
            sylls[si]["co"] = [t[1] for t in between if t[0] == "C"]
            break
        marks = [j for j, t in enumerate(between) if t[0] == "B"]
        if marks:
            j = marks[-1]
            sylls[si]["co"] = [t[1] for t in between[:j] if t[0] == "C"]
            sylls[si + 1]["on"] = [t[1] for t in between[j + 1:] if t[0] == "C"]
            if between[j][1] == "ˈ": sylls[si + 1]["stress"] = True
            if between[j][1] == "ˌ": sylls[si + 1]["sec"] = True
        else:
            cl = [t[1] for t in between if t[0] == "C"]
            split = len(cl)
            for n in range(len(cl), -1, -1):
                tail = tuple(cl[len(cl) - n:])
                if n == 0 or (n == 1 and tail[0] != "ŋ") or tail in ONSETS:
                    split = len(cl) - n; break
            # A short vowel can't end a syllable in respelling: FEN-ih, not FEH-nih.
            cur = sylls[si]
            if split == 0 and cl and cur["v"] in LAX and (cur["stress"] or cur["sec"] or cur["v"] not in ("ɪ", "ʊ")):
                split = 1
            sylls[si]["co"], sylls[si + 1]["on"] = cl[:split], cl[split:]
    parts = []
    for s in sylls:
        on = "".join(C_OUT.get(c, c) for c in s["on"])
        co = list(s["co"])
        v = s["v"]
        if co and co[0] == "r" and v in V_R:
            vs = V_R[v]; co = co[1:]
        elif v == "aɪ":
            if not co: vs = "y" if on else "eye"
            elif len(co) == 1 and co[0] not in ("r", "ŋ"): vs = "i"; co = co + ["_e"]
            else: vs = "eye"
        else:
            vs = (V_CLOSED if co else V_OPEN)[v]
        coda = "".join("e" if c == "_e" else C_OUT.get(c, c) for c in co)
        syl = on + vs + coda
        parts.append(syl.upper() if s["stress"] else syl)
    return "-".join(parts)


if __name__ == "__main__":
    for t in ["/dɪˈfɛnɪstɹeɪt/", "/ˌsɛskwɪpɪˈdeɪli.ən/", "/əbˈstɹɛpəɹəs/", "/ləˈɡuːbɹi.əs/", "/ˈpɛtɹɪkɔɹ/",
              "/kəmˈpleɪsənt/", "/ˈwɪloʊi/", "/biˈhoʊv/", "/ˈʌŋ(k)(t)ʃəwəs/", "/ˈkɹæpjʊlənt/", "/vaɪˈtuːpəɹeɪt/"]:
        print(t, respell(t))
