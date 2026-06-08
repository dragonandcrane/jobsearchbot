"""
Fill background/teaching-cover-template.md from listings/lausd/raw.csv and
write one cover letter per matching row, then drive md_to_pdf.py to render
each as a PDF.

Usage:
    python build_lausd_letters.py                          # all rows; one subdir per subject
    python build_lausd_letters.py --subject Math           # Math rows only; output to listings/lausd/Math/
    python build_lausd_letters.py --subject Elementary     # all Elementary variants -> listings/lausd/Elementary/
    python build_lausd_letters.py --date "June 5, 2026"    # override letter date
    python build_lausd_letters.py --no-pdf                 # skip PDF rendering

Placeholders filled in the template:
    {date}, {contact}, {recipient}, {school}, {subject}

When --subject X is given:
  - rows are filtered by case-insensitive prefix match on the subject column,
    so "--subject Elementary" picks up "Elementary", "Elementary (TK)",
    "Elementary (Bilingual) - Spanish", etc.
  - output dir is listings/lausd/<X>/ (the literal flag value).
When --subject is omitted, every row is processed and the output dir is the
row's exact subject string.

Filenames are <short>.md / <short>.pdf where <short> comes from the CSV's
first column. Rows that would write to the same path within the same output
dir are reported as collisions and skipped after the first.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

RAW_CSV = Path("listings/lausd/raw.csv")
TEMPLATE_PATH = Path("background/teaching-cover-template.md")
OUTPUT_BASE = Path("listings/lausd")

# LAUSD shorthand we want to keep uppercase after title-casing. Word-bounded,
# case-insensitive.
ABBREVS = {
    "MS", "HS", "EL", "SH", "JH", "CHTR", "MAG", "MAGN", "ENR", "ST",
    "TK", "PE", "AP", "STEM", "ELA", "ELD", "ESL", "BCLAD", "CTE", "IDM",
    "SAS", "GATE", "ASE", "RSP", "DL", "IM", "CES", "PSC", "ECE",
    "LA", "CA",
}
ABBREV_RE = re.compile(
    r"\b(" + "|".join(sorted(ABBREVS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Per-row extra italic paragraph appended after the contact block. Keyed by
# the `short` column value.
EXTRA_CONTACT_NOTES: dict[str, str] = {
    "Soces Magnet": (
        "*Application materials directed to "
        "Susana Mora, <susana.mora@lausd.net>, per the posting.*"
    ),
}


def smart_title(text: str) -> str:
    return ABBREV_RE.sub(lambda m: m.group(0).upper(), text.title())


def parse_contact(contact_field: str) -> tuple[str, str, str]:
    """Parse 'LASTNAME, FIRSTNAME - TITLE' into (first, last, title)."""
    parts = contact_field.split(" - ", 1)
    name_part = parts[0]
    title = smart_title(parts[1].strip()) if len(parts) > 1 else ""
    if "," in name_part:
        last, _, first = name_part.partition(",")
        first = first.strip()
        last = last.strip()
    else:
        first, last = "", name_part.strip()
    return smart_title(first), smart_title(last), title


def pretty_date(d: date) -> str:
    # Cross-platform: avoid %-d / %#d strftime quirks.
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def build_letter(template: str, date_str: str, row: dict[str, str]) -> str:
    school = smart_title(row["school_name"])
    address = smart_title(row["school_address"])
    email = row["school_contact_email"].lower()
    phone = row["school_phone_number"].strip()
    short = row["short"].strip()
    subject = row["subject"].strip()

    first, last, title = parse_contact(row["school_contact"])
    full_name = f"{first} {last}".strip()
    name_line = f"{full_name}, {title}" if title else full_name
    recipient = f"{title} {last}" if title else full_name

    # Stacked contact block — per the cover-letter style rule, hard line
    # breaks (\<EOL>) ARE allowed in the contact/signature blocks.
    contact_lines = [
        name_line,
        f"{school} (LAUSD)",
        address,
        f"<{email}>",
        phone,
    ]
    contact = "\\\n".join(contact_lines)
    extra = EXTRA_CONTACT_NOTES.get(short)
    if extra:
        contact += f"\n\n{extra}"

    return (
        template
        .replace("{date}", date_str)
        .replace("{contact}", contact)
        .replace("{recipient}", recipient)
        .replace("{school}", school)
        # Strip any qualifier after a comma so e.g. "Special Education,
        # Resource Specialist Program" substitutes as just "special education".
        .replace("{subject}", subject.split(",", 1)[0].strip().lower())
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--subject", default=None,
        help='Filter rows where the subject column starts with this string '
             '(case-insensitive). Output dir is listings/lausd/<value>/.',
    )
    parser.add_argument(
        "--date", default=pretty_date(date.today()),
        help='Override letter date (default: today, e.g. "June 8, 2026")',
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="Skip the md_to_pdf.py step.",
    )
    args = parser.parse_args()

    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}", file=sys.stderr)
        return 1
    if not RAW_CSV.exists():
        print(f"CSV not found: {RAW_CSV}", file=sys.stderr)
        return 1

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    with RAW_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if args.subject is not None:
        prefix = args.subject.strip().lower()
        rows = [r for r in rows if r["subject"].strip().lower().startswith(prefix)]
        output_dir_for = lambda _row: OUTPUT_BASE / args.subject.strip()
    else:
        output_dir_for = lambda r: OUTPUT_BASE / r["subject"].strip()

    if not rows:
        print("No matching rows.", file=sys.stderr)
        return 1

    written: list[Path] = []
    seen: set[Path] = set()
    collisions: list[tuple[Path, str, str]] = []
    skipped_no_short: list[str] = []

    for row in rows:
        short = row["short"].strip()
        if not short:
            skipped_no_short.append(f"{row['school_name']} / {row['subject']}")
            continue
        path = output_dir_for(row) / f"{short}.md"
        if path in seen:
            collisions.append((path, row["school_name"], row["subject"]))
            continue
        seen.add(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_letter(template, args.date, row), encoding="utf-8")
        written.append(path)
        print(f"  wrote {path}", flush=True)

    if skipped_no_short:
        print(f"\nSkipped {len(skipped_no_short)} row(s) with no `short`:", file=sys.stderr)
        for s in skipped_no_short:
            print(f"  {s}", file=sys.stderr)
    if collisions:
        print(f"\nCollisions ({len(collisions)}) — duplicate `short` within same output dir, skipped:",
              file=sys.stderr)
        for path, school, subject in collisions:
            print(f"  {path}  ({school} / {subject})", file=sys.stderr)

    if args.no_pdf or not written:
        return 0

    result = subprocess.run(
        [sys.executable, "md_to_pdf.py", *map(str, written)],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
