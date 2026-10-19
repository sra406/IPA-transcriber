#!/usr/bin/env python3
"""Transcribe English text to broad Canadian English IPA.

Known words are looked up in CMUdict. Unknown words are predicted by g2p-en.
Both sources use ARPAbet; this module maps that phone set to broad IPA.
"""

from __future__ import annotations

import argparse
import re
import sys
from functools import lru_cache

try:
    import cmudict
except ImportError as exc:  # pragma: no cover - exercised by CLI users
    raise SystemExit("Missing dependencies. Install them with: python -m pip install -r requirements.txt") from exc


# Broad North American/Canadian English values; stress affects rules and is
# shown in the IPA output. Unstressed AH is rendered as schwa.
CONSONANTS = {
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f",
    "G": "ɡ", "HH": "h", "JH": "dʒ", "K": "k", "L": "l",
    "M": "m", "N": "n", "NG": "ŋ", "P": "p", "R": "ɹ",
    "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v",
    "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ",
}
VOWELS = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ̯",
    "AY": "aɪ̯", "EH": "ɛ", "ER": "ɚ", "EY": "əɪ̯", "IH": "ɪ",
    "IY": "i", "OW": "oʊ̯", "OY": "ɔɪ̯", "UH": "ʊ", "UW": "u",
}
WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
# Common English syllable onsets, expressed in the CMU phone inventory. The
# estimate assigns the longest legal onset from an intervocalic consonant run.
LEGAL_ONSETS = {
    ("P",), ("B",), ("T",), ("D",), ("K",), ("G",), ("F",), ("V",),
    ("TH",), ("DH",), ("S",), ("Z",), ("SH",), ("ZH",), ("HH",),
    ("CH",), ("JH",), ("M",), ("N",), ("NG",), ("L",), ("R",),
    ("W",), ("Y",),
    ("P", "R"), ("B", "R"), ("T", "R"), ("D", "R"), ("K", "R"), ("G", "R"),
    ("F", "R"), ("TH", "R"), ("SH", "R"),
    ("P", "L"), ("B", "L"), ("K", "L"), ("G", "L"), ("F", "L"),
    ("K", "W"), ("G", "W"), ("S", "P"), ("S", "T"), ("S", "K"),
    ("S", "F"), ("S", "M"), ("S", "N"), ("S", "L"), ("S", "W"),
    ("S", "P", "R"), ("S", "P", "L"), ("S", "T", "R"), ("S", "K", "R"),
    ("S", "K", "W"),
}


def _syllable_starts(parsed: list[tuple[str, str]]) -> set[int]:
    """Estimate syllable onsets with a longest-legal-onset heuristic."""
    nuclei = [i for i, (base, _) in enumerate(parsed) if base in VOWELS]
    starts: set[int] = set()
    for left, right in zip(nuclei, nuclei[1:]):
        cluster = tuple(base for base, _ in parsed[left + 1:right])
        onset_size = 0
        for size in range(1, len(cluster) + 1):
            if cluster[-size:] in LEGAL_ONSETS:
                onset_size = size
        starts.add(right - onset_size)
    return starts


def _mark_phrase_boundaries(separator: str) -> str:
    """Convert punctuation in a text gap to phrase boundary markers."""
    separator = re.sub(r"[,;:]+", "|", separator)
    separator = re.sub(r"[.!?]+", "‖", separator)
    return re.sub(r"\n\s*\n", " ‖ ", separator)


def _to_ipa(phones: list[str]) -> str:
    """Map ARPAbet phones to IPA and apply the attached allophonic rules.

    A dictionary/G2P word supplies no reliable syllable boundaries. Stress and
    immediate phone context are used as practical approximations for syllable
    onset, coda, and inter-vocalic environments.
    """
    parsed = []
    for phone in phones:
        match = re.fullmatch(r"([A-Z]+)([012]?)", phone.upper())
        if match:
            parsed.append(match.groups())

    # Insert a glottal stop between adjacent vowel nuclei.
    with_hiatus = []
    for phone in parsed:
        if with_hiatus and with_hiatus[-1][0] in VOWELS and phone[0] in VOWELS:
            with_hiatus.append(("ʔ", ""))
        with_hiatus.append(phone)
    parsed = with_hiatus
    syllable_starts = _syllable_starts(parsed)
    stress_at: dict[int, str] = {}
    for nucleus, (base, stress) in enumerate(parsed):
        if base not in VOWELS or stress not in {"1", "2"}:
            continue
        onset = max((start for start in syllable_starts if start <= nucleus), default=0)
        # An inserted glottal stop is the onset of the following hiatus syllable.
        if onset > 0 and parsed[onset - 1][0] == "ʔ":
            onset -= 1
        stress_at[onset] = "ˈ" if stress == "1" else "ˌ"

    out: list[str] = []
    for i, (base, stress) in enumerate(parsed):
        if i in syllable_starts:
            out.append(".")
        if i in stress_at:
            out.append(stress_at[i])
        if base == "ʔ":
            out.append("ʔ")
            continue
        prev = parsed[i - 1][0] if i else None
        nxt = parsed[i + 1][0] if i + 1 < len(parsed) else None
        is_vowel = base in VOWELS
        value = ("ɝ" if base == "ER" and stress in {"1", "2"} else VOWELS[base]) if is_vowel else CONSONANTS.get(base, "")

        if is_vowel and stress == "0" and base == "AH":
            value = "ə"
        # Nasalization applies to every vowel quality, including schwa.
        if is_vowel and nxt in {"M", "N", "NG"}:
            if base in {"AW", "AY", "EY", "OW", "OY"}:
                value = value.replace("̯", "̯̃")
            else:
                value += "̃"

        # Canadian raising: stressed /aɪ, aʊ/ before a voiceless consonant.
        if stress == "1" and nxt in {"P", "T", "K", "F", "TH", "S", "SH", "CH", "HH"}:
            if base == "AY":
                value = "ʌɪ̯"
            elif base == "AW":
                value = "ʌʊ̯"

        # Aspiration at word onset or before a stressed vowel, unless /s/ precedes.
        aspirated = base in {"P", "T", "K"} and prev != "S" and (
            i == 0 or (nxt in VOWELS and parsed[i + 1][1] in {"1", "2"})
        )
        if aspirated:
            value += "ʰ"

        # Approximants after an aspirated onset are devoiced.
        if base in {"W", "Y", "R", "L"} and prev in {"P", "T", "K"}:
            prev_prev = parsed[i - 2][0] if i >= 2 else None
            prev_aspirated = prev_prev != "S" and (i - 1 == 0 or (stress in {"1", "2"}))
            if prev_aspirated:
                value += "̥"

        # Intervocalic tapping before an unstressed vowel. /n/ and /nt, nd/
        # surface as a nasalized flap in that same environment.
        if base in {"T", "D"} and prev in VOWELS and nxt in VOWELS and parsed[i + 1][1] == "0":
            value = "ɾ"
        elif base == "N" and prev in VOWELS and nxt in VOWELS and parsed[i + 1][1] == "0":
            value = "ɾ̃"
        elif (
            base in {"T", "D"}
            and prev == "N"
            and i >= 2
            and parsed[i - 2][0] in VOWELS
            and nxt in VOWELS
            and parsed[i + 1][1] == "0"
        ):
            out[-1] = "ɾ̃"
            continue

        # Dentalize alveolars before dental fricatives.
        if nxt in {"TH", "DH"} and base in {"T", "D", "N", "S", "Z", "L"}:
            value += "̪"

        # Dark /l/ in a coda (not before a following vowel).
        if base == "L" and nxt not in VOWELS:
            value = "ɫ"

        # Mark stops at word ends and phrase ends as unreleased.
        if i == len(parsed) - 1 and base in {"P", "B", "T", "D", "K", "G"}:
            value += "̚"
        out.append(value)

    return "".join(out)


@lru_cache(maxsize=1)
def _dictionary() -> dict[str, list[list[str]]]:
    return cmudict.dict()


@lru_cache(maxsize=1)
def _g2p():
    try:
        from g2p_en import G2p
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install the fallback model with: python -m pip install -r requirements.txt") from exc
    return G2p()


def pronounce(
    word: str,
    epenthetic_t: bool = False,
) -> tuple[str, str]:
    """Return (IPA, source) for a word. Source is 'dictionary' or 'g2p'."""
    key = word.lower().replace("’", "'")
    variants = _dictionary().get(key)
    if variants:
        phones = list(variants[0])
        if epenthetic_t and key.endswith(("nce", "nse")) and phones and phones[-1].startswith("S"):
            phones.insert(len(phones) - 1, "T")
        return _to_ipa(phones), "dictionary"
    # g2p-en can emit spaces, punctuation, and non-phone tokens; retain only
    # ARPAbet phone tokens, then convert them through the same IPA map.
    phones = [p for p in _g2p()(key) if re.fullmatch(r"[A-Z]+[012]?", p)]
    if epenthetic_t and key.endswith(("nce", "nse")) and phones and phones[-1].startswith("S"):
        phones.insert(len(phones) - 1, "T")
    return _to_ipa(phones), "g2p"


def transcribe(
    text: str,
    show_sources: bool = False,
    epenthetic_t: bool = False,
) -> str:
    matches = list(WORD_RE.finditer(text))
    if not matches:
        return f"[{text}]"
    out: list[str] = ["["]
    cursor = 0
    for match in matches:
        out.append(_mark_phrase_boundaries(text[cursor:match.start()]))
        word = match.group(0)
        ipa, source = pronounce(
            word,
            epenthetic_t=epenthetic_t,
        )
        # Stress marks precede the syllable onset, so skip them when detecting
        # vowel-initial words and keep them before the inserted glottal stop.
        stress_marks = re.match(r"[ˈˌ]*", ipa).group(0)
        ipa_body = ipa[len(stress_marks):]
        if ipa_body and ipa_body[0] in "ɑæʌɔaɛɪɝeiuoʊʊ":
            ipa = stress_marks + "ʔ" + ipa_body
        out.append(f"{ipa}⟨{source}⟩" if show_sources else ipa)
        cursor = match.end()
    out.append(_mark_phrase_boundaries(text[cursor:]))
    out.append("]")
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe English text to broad Canadian English IPA.")
    parser.add_argument("text", nargs="*", help="Text to transcribe; reads standard input when omitted.")
    parser.add_argument("--sources", action="store_true", help="Label each word as dictionary or g2p.")
    parser.add_argument("--epenthetic-t", action="store_true", help="Apply [t] to English words ending in -nce or -nse.")
    args = parser.parse_args()
    text = " ".join(args.text) if args.text else sys.stdin.read()
    try:
        print(transcribe(
            text,
            show_sources=args.sources,
            epenthetic_t=args.epenthetic_t,
        ))
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
