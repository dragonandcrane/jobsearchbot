"""
Fill background/teaching-cover-template.md once per LAUSD listing and write
the resulting cover letters to listings/lausd/<short>.md, then drive
md_to_pdf.py to render each as a PDF.

Usage:
    python build_lausd_letters.py                       # today's date, md + pdf
    python build_lausd_letters.py --date "June 5, 2026" # override date
    python build_lausd_letters.py --no-pdf              # md only, skip PDFs

Adding/removing/editing schools: edit the SCHOOLS list below. The order of
columns matches: short filename, display school name, address, principal
first name, principal last name, title, contact email, contact phone.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

# (short, school display name, address, first, last, title, email, phone)
SCHOOLS = [
    ("Nobel MS",      "Alfred B. Nobel Charter Middle School",
     "9950 Tampa Ave, Northridge, CA 91324",
     "Nidhi", "Batra", "Principal", "NXB0873@lausd.net", "(818) 773-4700"),
    ("Chavez Magnet", "Cesar Chavez LA Arts Magnet",
     "1001 Arroyo Street, San Fernando, CA 91340",
     "Anne", "Maschler", "Principal", "ACM0248@lausd.net", "(818) 837-6428"),
    ("Chavez",        "Cesar Chavez LA ASE",
     "1001 Arroyo Street, San Fernando, CA 91340",
     "Angelyque", "Jensen Cachon", "Principal", "AXJ0519@lausd.net", "(818) 838-3926"),
    ("Cleveland HS",  "Cleveland Charter High School",
     "8140 Vanalden Ave, Reseda, CA 91335",
     "Cindy", "Duong", "Principal", "cindy.duong@lausd.net", "(818) 885-2300"),
    ("Kennedy HS",    "John F. Kennedy Senior High School",
     "11254 Gothic Ave, Granada Hills, CA 91344",
     "Oscar", "Vazquez", "Principal", "OXV1741@lausd.net", "(818) 271-2900"),
    ("Mulholland MS", "Mulholland Middle School",
     "17120 Vanowen St, Lake Balboa, CA 91406",
     "Raquel", "Segal", "Principal", "rsegal1@lausd.net", "(818) 609-2500"),
    ("Northridge MS", "Northridge Middle School, Medical & Health Careers Magnet",
     "17960 Chase St, Northridge, CA 91325",
     "Piedad", "Sanchez", "Principal", "PPS8982@lausd.net", "(818) 678-5100"),
    ("Portola MS",    "Portola Charter Middle School",
     "18720 Linnet St, Tarzana, CA 91356",
     "Javier", "Tapia", "Principal", "jtapia1@lausd.net", "(818) 654-3300"),
    ("Reseda HS",     "Reseda Charter High School Science Magnet",
     "18230 Kittridge St, Reseda, CA 91335",
     "Pia Maria", "Damonte", "Principal", "PXD1774@lausd.net", "(818) 758-3600"),
    ("Soces Magnet",  "Sherman Oaks Center for Enriched Studies Magnet",
     "18605 Erwin St, Reseda, CA 91335",
     "Anabel", "Bonney", "Principal", "anabel.bonney@lausd.net", "(818) 758-5600"),
]

# SOCES routes the application through Susana Mora per the posting. The note
# is an italic paragraph after the contact block in the rendered letter.
SOCES_NOTE = (
    "*Application materials directed to "
    "Susana Mora, <susana.mora@lausd.net>, per the posting.*"
)

TEMPLATE_PATH = Path("background/teaching-cover-template.md")
OUTPUT_DIR = Path("listings/lausd")


def pretty_date(d: date) -> str:
    # Cross-platform: avoid %-d / %#d strftime quirks.
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def build_letter(template: str, date_str: str, short: str, school: str,
                 addr: str, first: str, last: str, title: str,
                 email: str, phone: str) -> str:
    name = f"{first} {last}"
    recipient = f"{title} {last}"

    # Stacked contact block: trailing backslash + newline is markdown's hard
    # line break, which we WANT here (per David's style rule: stacked lines
    # OK in contact/signature blocks, not in body prose).
    contact_lines = [
        f"{name}, {title}",
        f"{school} (LAUSD)",
        addr,
        f"<{email}>",
        phone,
    ]
    contact = "\\\n".join(contact_lines)
    if short == "Soces Magnet":
        contact += f"\n\n{SOCES_NOTE}"

    return (template
            .replace("{date}", date_str)
            .replace("{contact}", contact)
            .replace("{recipient}", recipient)
            .replace("{school}", school))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=pretty_date(date.today()),
                        help='Override letter date (default: today, e.g. "June 5, 2026")')
    parser.add_argument("--no-pdf", action="store_true",
                        help="Skip the md_to_pdf.py step")
    args = parser.parse_args()

    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}", file=sys.stderr)
        return 1

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for row in SCHOOLS:
        short = row[0]
        text = build_letter(template, args.date, *row)
        path = OUTPUT_DIR / f"{short}.md"
        path.write_text(text, encoding="utf-8")
        print(f"  wrote {path}", flush=True)

    if args.no_pdf:
        return 0

    result = subprocess.run(
        [sys.executable, "md_to_pdf.py", str(OUTPUT_DIR)],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
