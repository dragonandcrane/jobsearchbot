"""Write per-listing detail directories and listing.md files.

For each JobListing, creates:
  listings/<job_site>/<slug>/listing.md

Slug is derived from the listing URL path.  The file is only written if it
does not already exist, making this step idempotent.
"""

import re
import logging
from pathlib import Path
from urllib.parse import urlparse

from scrapers.base import JobListing

logger = logging.getLogger(__name__)

_LISTINGS_DIR = Path(__file__).parent / "listings"

# Path segments that are site navigation, not part of the listing identity
_SKIP_PATH_SEGMENTS = {
    "careers", "career", "jobs", "job", "j",
    "position", "listing", "details", "home", "index",
}


def url_to_slug(url: str) -> str:
    """Derive a filesystem-safe slug from a job listing URL.

    Example:
        https://www.governmentjobs.com/jobs/60587-1/cloud-engineer
        -> 60587-1-cloud-engineer
    """
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    # Drop all leading segments that are generic navigation prefixes
    while parts and parts[0].lower() in _SKIP_PATH_SEGMENTS:
        parts = parts[1:]
    slug = "-".join(parts)
    # Sanitize to alphanumerics and hyphens
    slug = re.sub(r"[^\w-]", "-", slug.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


# Bare email: not already inside <, (, or [; lookahead includes \w to block TLD backtracking
_BARE_EMAIL_RE = re.compile(
    r'(?<![<(\[])([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})(?![>)\]\w])'
)
# Bare URL: not already inside <, (, or "; greedy \S+ then trailing punct stripped in callback
_BARE_URL_RE = re.compile(r'(?<![<("(\["])(https?://\S+)')


def _autolink(s: str) -> str:
    """Wrap bare emails and URLs in angle brackets for markdownlint MD034."""
    def _wrap_url(m: re.Match) -> str:
        url = m.group(1)
        stripped = url.rstrip(".,;:!?)")
        return f"<{stripped}>{url[len(stripped):]}"

    s = _BARE_EMAIL_RE.sub(r"<\1>", s)
    s = _BARE_URL_RE.sub(_wrap_url, s)
    return s


def _format_description(text: str) -> str:
    """Apply heuristics to convert plain scraped text to markdown.

    Heuristics applied (in order):
    - Existing bullet markers (-, *, •) are normalised to '- '
    - Numbered list items (1. or 1)) are converted to '- '
    - ALL-CAPS short lines become ### headers
    - Short lines ending with ':' become ### headers
    - Everything else is kept as-is (paragraph text)
    """
    if not text:
        return ""

    lines = text.splitlines()
    result: list[str] = []

    for line in lines:
        s = line.strip()

        if not s:
            # Collapse consecutive blank lines to one
            if result and result[-1] != "":
                result.append("")
            continue

        # Already a markdown header — pass through unchanged
        if s.startswith("#"):
            result.append(_autolink(s))
            continue

        # Normalise existing list markers
        if s.startswith(("- ", "* ", "• ", "· ")):
            result.append(f"- {_autolink(s[2:].strip())}")
            continue

        # Numbered list: "1. foo" or "1) foo"
        if re.match(r"^\d+[.)]\s+\S", s):
            result.append("- " + _autolink(re.sub(r"^\d+[.)]\s+", "", s)))
            continue

        # ALL-CAPS header
        alpha = [c for c in s if c.isalpha()]
        if alpha and len(s) <= 80 and sum(c.isupper() for c in alpha) / len(alpha) > 0.75:
            result.append(f"\n### {s.title()}\n")
            continue

        # Short line ending with colon → section label
        if s.endswith(":") and len(s) <= 60:
            result.append(f"\n### {s.rstrip(':')}\n")
            continue

        result.append(_autolink(s))

    return "\n".join(result).strip()


def _lint_fix(text: str) -> str:
    """Fix trivial markdownlint issues in generated markdown.

    - MD012: collapse 3+ consecutive blank lines to one
    - MD001: heading levels must only increment by one at a time
    """
    # MD012: no multiple consecutive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # MD001: heading levels increment at most by one
    lines = text.splitlines()
    result: list[str] = []
    current_level = 0
    for line in lines:
        m = re.match(r"^(#{1,6})(\s+.*)$", line)
        if m:
            raw_level = len(m.group(1))
            if current_level > 0 and raw_level > current_level + 1:
                raw_level = current_level + 1
                line = "#" * raw_level + m.group(2)
            current_level = raw_level
        result.append(line)
    return "\n".join(result)


def _build_markdown(listing: JobListing) -> str:
    """Render a JobListing as a markdown document."""
    title = listing.position or "Job Listing"
    url = listing.full_url

    lines: list[str] = [f"# [{title}]({url})", ""]

    # Metadata table — only include populated fields
    table_rows = [
        ("Employer", listing.agency_department),
        ("Salary", listing.salary_range),
        ("Location", listing.location),
        ("Job Type", listing.job_type),
        ("Remote Employment", listing.remote),
        ("Department", listing.department),
        ("Closing Date", listing.closing_date),
        ("Education", listing.education_requirement),
        ("Contact", listing.contact_name),
        ("Phone", listing.contact_phone),
        ("Email", listing.contact_email),
    ]
    filled = [(k, re.sub(r"\s*\|\s*", " - ", v)) for k, v in table_rows if v]
    if filled:
        key_width = max(len("Field"), max(len(k) for k, _ in filled))
        val_width = max(len("Value"), max(len(v) for _, v in filled))
        lines.append(f"| {'Field':<{key_width}} | {'Value':<{val_width}} |")
        lines.append(f"|{'-' * (key_width + 2)}|{'-' * (val_width + 2)}|")
        for k, v in filled:
            lines.append(f"| {k:<{key_width}} | {v:<{val_width}} |")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Body: full scraped text takes priority, then processed role description
    body = listing.full_description or listing.role_description
    if body:
        lines.append(_format_description(body))

    if listing.qualification:
        lines.append("")
        lines.append("## Qualifications")
        lines.append("")
        lines.append(_format_description(listing.qualification))

    # Org boilerplate at the end, separated by a rule
    if listing.org_boilerplate:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(_format_description(listing.org_boilerplate))

    return _lint_fix("\n".join(lines).strip()) + "\n"


_RESUME_SOURCE = Path(__file__).parent / "background" / "resume.md"


def write_resume_file(listing: JobListing, force: bool = False) -> Path | None:
    """Copy background/resume.md to listings/<job_site>/<slug>/resume.md.

    Skips silently if the file already exists, unless force=True.
    Returns the Path written, or None if skipped or on error.
    """
    if not listing.full_url:
        return None

    slug = url_to_slug(listing.full_url)
    if not slug:
        return None

    site = listing.job_site or urlparse(listing.full_url).netloc.removeprefix("www.")
    listing_dir = _LISTINGS_DIR / site / slug
    resume_path = listing_dir / "resume.md"

    if resume_path.exists() and not force:
        return None

    if not _RESUME_SOURCE.exists():
        logger.warning(f"Resume source not found: {_RESUME_SOURCE}")
        return None

    try:
        listing_dir.mkdir(parents=True, exist_ok=True)
        resume_path.write_text(_RESUME_SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info(f"Wrote {resume_path.relative_to(_LISTINGS_DIR.parent)}")
        return resume_path
    except OSError as e:
        logger.warning(f"Failed to write resume file for {listing.full_url}: {e}")
        return None


def listing_has_description(url: str, job_site: str) -> bool:
    """Return True if the listing.md file has content after the --- separator."""
    slug = url_to_slug(url)
    if not slug:
        return True  # can't determine; don't trigger unnecessary fetches
    listing_path = _LISTINGS_DIR / job_site / slug / "listing.md"
    if not listing_path.exists():
        return False
    content = listing_path.read_text(encoding="utf-8")
    sep_idx = content.rfind("---")
    return sep_idx != -1 and content[sep_idx + 3:].strip() != ""


def write_listing_file(listing: JobListing, force: bool = False) -> Path | None:
    """Write listings/<job_site>/<slug>/listing.md for a listing.

    Skips silently if the file already exists, unless force=True.
    Returns the Path written, or None if skipped or on error.
    """
    if not listing.full_url:
        return None

    slug = url_to_slug(listing.full_url)
    if not slug:
        return None

    # job_site is already 'governmentjobs.com' etc; fall back to URL hostname
    site = listing.job_site or urlparse(listing.full_url).netloc.removeprefix("www.")
    listing_dir = _LISTINGS_DIR / site / slug
    listing_path = listing_dir / "listing.md"

    if listing_path.exists() and not force:
        return None

    try:
        listing_dir.mkdir(parents=True, exist_ok=True)
        listing_path.write_text(_build_markdown(listing), encoding="utf-8")
        logger.info(f"Wrote {listing_path.relative_to(_LISTINGS_DIR.parent)}")
        return listing_path
    except OSError as e:
        logger.warning(f"Failed to write listing file for {listing.full_url}: {e}")
        return None
