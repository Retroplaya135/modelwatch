"""Normalize a supported copied-text catalog format into Markdown."""

from __future__ import annotations

import re

NBSP = "\u00a0"
OBJECT_REPLACEMENT = "\ufffc"
TOKEN_RE = re.compile(r"\(free\)\s*([0-9.]+[KMB]?)\s*tokens\b", re.IGNORECASE)
GOING_AWAY_RE = re.compile(r"^Going away\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*", re.IGNORECASE)
CATEGORY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9.+/&-]*)\s*\(#(\d+)\)\s*")


def normalize_text(value: str) -> str:
    value = value.replace(NBSP, " ").replace(OBJECT_REPLACEMENT, " ")
    return re.sub(r"\s+", " ", value).strip()


def parse_entry(line: str) -> tuple[str, str, str, list[str], str]:
    value = normalize_text(line)
    token_match = TOKEN_RE.search(value)
    if not token_match:
        return value, "", "", [], ""
    token_size = f"{token_match.group(1)} tokens"
    title = value[: token_match.start()].strip()
    remainder = value[token_match.end() :].strip()
    going_away = ""
    date_match = GOING_AWAY_RE.match(remainder)
    if date_match:
        going_away = date_match.group(1)
        remainder = remainder[date_match.end() :].strip()
    categories: list[str] = []
    while category_match := CATEGORY_RE.match(remainder):
        categories.append(f"{category_match.group(1)} (#{category_match.group(2)})")
        remainder = remainder[category_match.end() :].strip()
    return title, token_size, going_away, categories, remainder


def format_entry(entry: tuple[str, str, str, list[str], str]) -> str:
    title, token_size, going_away, categories, description = entry
    header = f"- **{title}**"
    if token_size:
        header += f" — **{token_size}**"
    if going_away:
        header += f" — Going away {going_away}"
    if categories:
        header += " — " + ", ".join(categories)
    return header if not description else f"{header}\n  {description}"


def clean_text(raw: str, *, title: str = "Zero-priced model catalog") -> str:
    lines = []
    for original in raw.splitlines():
        line = re.sub(r"^\s*\*\s*", "", original.replace(OBJECT_REPLACEMENT, " ")).strip()
        if line:
            lines.append(line)
    entries = [format_entry(parse_entry(line)) for line in lines]
    return f"## {title}\n\n" + "\n\n".join(entries) + "\n"
