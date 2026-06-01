"""
Convert one or more Markdown files to styled PDFs using Microsoft Edge
in headless print-to-PDF mode.

Usage:
    python md_to_pdf.py PATH [PATH ...]

PATH may be a file or directory. Directories are scanned for *.md (non-recursive).
For each input X.md the script writes X.pdf alongside it.

Notes on the Windows workarounds:
  - Edge needs a private --user-data-dir, or it silently delegates the print
    job to a running desktop Edge and the parent process returns rc=0 with no
    PDF written.
  - --print-to-pdf must be an absolute path; relative paths also return rc=0
    with no usable output.
  - The parent msedge.exe exits before its backgrounded worker finishes
    writing the PDF, so we poll for the output file after subprocess.run.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import markdown

EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

STYLE = """
@page { size: letter; margin: 0.9in 1.0in; }

:root {
    --ink:      #2b2622;
    --ink-soft: #574c44;
    --rule:     #d8cfc4;
    --accent:   #6b4a2b;
}

html, body {
    margin: 0;
    padding: 0;
    color: var(--ink);
    font-family: "EB Garamond", Garamond, Georgia, "Times New Roman", serif;
    font-size: 11.5pt;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
}

p { margin: 0.55rem 0; }

a { color: inherit; text-decoration: none; border-bottom: 1px dotted var(--rule); }

hr {
    border: none;
    border-top: 1px solid var(--rule);
    margin: 1.1rem 0 1.2rem;
}

em { color: var(--ink-soft); }
"""


def find_edge() -> Path:
    for candidate in EDGE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise SystemExit("Microsoft Edge not found in standard install locations.")


def render_html(md_text: str) -> str:
    # Python-Markdown does not treat a trailing backslash as a hard line break
    # (it expects two trailing spaces). Translate the project's `\<EOL>`
    # convention to the two-space form so header blocks render as multi-line.
    md_text = md_text.replace("\\\n", "  \n")
    body = markdown.markdown(md_text, extensions=["extra", "sane_lists"])
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{STYLE}</style></head><body>{body}</body></html>"
    )


def md_to_pdf(md_path: Path, edge: Path, keep_html: bool) -> Path:
    html = render_html(md_path.read_text(encoding="utf-8"))

    html_path = md_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")

    pdf_path = md_path.with_suffix(".pdf").resolve()
    file_url = "file:///" + str(html_path.resolve()).replace("\\", "/")

    profile_dir = Path(tempfile.mkdtemp(prefix="md_to_pdf_edge_"))

    if pdf_path.exists():
        pdf_path.unlink()

    cmd = [
        str(edge),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={profile_dir}",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        file_url,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
    )

    deadline = time.time() + 30.0
    while time.time() < deadline and not pdf_path.exists():
        time.sleep(0.25)

    shutil.rmtree(profile_dir, ignore_errors=True)

    if not pdf_path.exists():
        raise RuntimeError(
            f"Edge did not produce PDF for {md_path} within 30s "
            f"(rc={result.returncode})."
        )

    if not keep_html:
        html_path.unlink()

    return pdf_path


def expand_inputs(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.glob("*.md")))
        elif p.is_file() and p.suffix.lower() == ".md":
            files.append(p)
        else:
            print(f"skipping (not a .md file or directory): {p}", file=sys.stderr)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--keep-html", action="store_true",
                        help="Do not delete the intermediate .html file.")
    args = parser.parse_args()

    edge = find_edge()
    files = expand_inputs(args.paths)
    if not files:
        print("No .md files to process.", file=sys.stderr)
        return 1

    for md in files:
        try:
            pdf = md_to_pdf(md, edge, args.keep_html)
            print(f"  {md.name} -> {pdf.name}")
        except Exception as exc:
            print(f"FAILED {md}: {exc}", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
