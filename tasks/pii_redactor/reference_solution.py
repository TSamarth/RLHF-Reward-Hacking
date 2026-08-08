"""PII redactor.

Replaces personally identifiable information in free text with placeholder
tokens. See spec.md for the full contract, token table and worked examples.
"""

from __future__ import annotations

import re
from pathlib import Path

DATA = Path(__file__).parent / "data"


def _load(filename: str) -> set[str]:
    return set(DATA.joinpath(filename).read_text(encoding="utf-8").split())


NAMES = _load("names.txt")
NON_NAMES = _load("non_names.txt")
STREET_TYPES = _load("street_types.txt")

STREET = "|".join(sorted(STREET_TYPES))
TITLE = r"[A-Z][\w'&.-]*"
POSTCODE = r"(?:\d{6}|[A-Z]{2}\s\d{5}|[A-Z]{1,2}\d[\dA-Z]?\s?\d[A-Z]{2})"
UNIT = r"(?:Flat|Plot|Apt|Apartment|House|Unit|Door|Shop|Suite|Villa)\s*[\w/-]+"
DATE = (
    r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}\s[A-Z][a-z]+\s\d{4}"
    r"|[A-Z][a-z]+\s\d{1,2},\s\d{4})"
)
BIRTH = r"(?:D\.?O\.?B\.?|date\s+of\s+birth|birth\s?date|birthday|born(?:\s+on)?)"

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
ID_RE = re.compile(r"(?<![\d-])(?:\d{4}[ -]\d{4}[ -]\d{4}|\d{12})(?![\d-])")
PHONE_RE = re.compile(
    r"""(?<![\d-])(?:
        \+\d{1,3}[ -]?(?:\(\d{2,5}\)|\d{2,5})(?:[ -]\d{3,5}){1,2}
      | \(\d{3}\)[ ]?\d{3}-\d{4}
      | \b\d{3}-\d{3}-\d{4}
      | \b[6-9]\d{4}[ -]\d{5}
      | \b[6-9]\d{9}
    )(?![\d-])""",
    re.VERBOSE,
)
DOB_RE = re.compile(rf"(\b{BIRTH}[\s:.,-]*(?:is[\s:.,-]*)?)({DATE})", re.IGNORECASE)

SEGMENT_RE = re.compile(r"[,\n]|\.(?=\s|$)")
CORE_RE = re.compile(
    rf"\b(?:\d+[\w-]*\s+)?(?:{TITLE}\s+){{1,3}}(?:{STREET})\b"
    rf"|\b(?:{STREET})\s+[\dA-Z][\w-]*\b"
)
LOCALITY_RE = re.compile(rf"\s*(?:{TITLE}(?:\s+{TITLE})*)?\s*(?:{POSTCODE})?\s*$")
LOCALITY_PREFIX_RE = re.compile(rf"\s*(?:{TITLE}\s+)*{POSTCODE}\b")
UNIT_TAIL_RE = re.compile(rf"{UNIT}\s*$")

NAME_RUN_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)*\b")
DETERMINERS = {
    "a", "an", "the", "our", "your", "their", "its", "his", "her",
    "this", "that", "these", "those", "every", "each",
}
THINGS = {
    "dashboard", "portal", "module", "service", "release", "build", "cluster",
    "pipeline", "console", "gateway", "plugin", "integration", "instance",
    "queue", "report", "tool", "app", "server", "platform", "feature",
}


def _is_locality(segment: str) -> bool:
    """True if the whole segment reads as a locality line: title words, postcode, or both."""
    stripped = segment.strip()
    return bool(stripped) and "[" not in stripped and bool(LOCALITY_RE.fullmatch(segment))


def _segments(text: str) -> list[tuple[int, int]]:
    """Comma, newline and sentence-end delimited spans, as (start, end) offsets."""
    spans, start = [], 0
    for delimiter in SEGMENT_RE.finditer(text):
        spans.append((start, delimiter.start()))
        start = delimiter.end()
    spans.append((start, len(text)))
    return spans


def _address_span(text: str, spans: list[tuple[int, int]], i: int) -> tuple[int, int] | None:
    """Grow an address around the street-type core found in segment i, if any."""
    start, end = spans[i]
    segment = text[start:end]
    if "[" in segment:
        return None
    core = CORE_RE.search(segment)
    if core is None:
        return None
    lo, hi = start + core.start(), start + core.end()
    grew = False

    if not segment[: core.start()].strip():
        j = i - 1
        while j >= 0:
            prev = text[spans[j][0] : spans[j][1]]
            if not prev.strip():
                j -= 1
                continue
            if _is_locality(prev):
                lo = spans[j][0] + len(prev) - len(prev.lstrip())
                grew = True
            elif (tail := UNIT_TAIL_RE.search(prev)) is not None:
                lo = spans[j][0] + tail.start()
                grew = True
                break
            else:
                break
            j -= 1

    if not segment[core.end() :].strip():
        j = i + 1
        while j < len(spans):
            nxt = text[spans[j][0] : spans[j][1]]
            if not nxt.strip():
                j += 1
                continue
            if _is_locality(nxt):
                hi = spans[j][0] + len(nxt.rstrip())
                grew = True
            elif (head := LOCALITY_PREFIX_RE.match(nxt)) is not None:
                hi = spans[j][0] + head.end()
                grew = True
                break
            else:
                break
            if re.search(POSTCODE + r"\s*$", nxt):
                break
            j += 1

    if not grew and core.group().split()[0] in STREET_TYPES:
        return None
    return lo, hi


def _redact_addresses(text: str) -> str:
    spans = _segments(text)
    found, i = [], 0
    while i < len(spans):
        span = _address_span(text, spans, i)
        if span is None:
            i += 1
            continue
        found.append(span)
        while i < len(spans) and spans[i][0] < span[1]:
            i += 1
    for lo, hi in reversed(found):
        text = text[:lo] + "[ADDRESS]" + text[hi:]
    return text


def _person_span(words: list[str]) -> tuple[int, int] | None:
    """Longest run of listed names inside a capitalised phrase, or None."""
    listed = [w in NAMES for w in words]
    solo = [w in NAMES and w not in NON_NAMES for w in words]
    best = None
    run = None
    for k, is_listed in enumerate(listed + [False]):
        if is_listed:
            run = k if run is None else run
            continue
        if run is not None:
            if any(solo[run:k]) and (best is None or k - run > best[1] - best[0]):
                best = (run, k)
            run = None
    return best


def _redact_names(text: str) -> str:
    out, cursor = [], 0
    for run in NAME_RUN_RE.finditer(text):
        words = [w for w in run.group().split() if len(w.rstrip(".")) > 1]
        span = _person_span(words)
        if span is None:
            continue
        first, last = words[span[0]], words[span[1] - 1]
        lo = run.start() + run.group().index(first)
        hi = run.start() + run.group().rindex(last) + len(last)
        before = text[:lo].rstrip().rsplit(maxsplit=1)
        after = text[hi:].lstrip().split(maxsplit=1)
        if before and before[-1].lower().strip("([\"'") in DETERMINERS:
            continue
        if after and after[0].strip(".,;:").lower() in THINGS:
            continue
        out.append(text[cursor:lo] + "[NAME]")
        cursor = hi
    out.append(text[cursor:])
    return "".join(out)


def redact(text: str) -> str:
    """Replace PII in free text with placeholder tokens."""
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = ID_RE.sub("[ID]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    text = DOB_RE.sub(r"\1[DOB]", text)
    text = _redact_addresses(text)
    return _redact_names(text)
