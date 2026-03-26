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

        # Normalise existing list markers
        if s.startswith(("- ", "* ", "• ", "· ")):
            result.append(f"- {s[2:].strip()}")
            continue

        # Numbered list: "1. foo" or "1) foo"
        if re.match(r"^\d+[.)]\s+\S", s):
            result.append(f"- {re.sub(r'^\d+[.)]\s+', '', s)}")
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

        result.append(s)

    return "\n".join(result).strip()


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
    filled = [(k, v) for k, v in table_rows if v]
    if filled:
        key_width = max(len(k) for k, _ in filled)
        lines.append(f"| {'Field':<{key_width}} | Value |")
        lines.append(f"|{'-' * (key_width + 2)}|-------|")
        for k, v in filled:
            lines.append(f"| {k:<{key_width}} | {v} |")
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

    return "\n".join(lines).strip() + "\n"


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


def delete_listing_file(url: str, job_site: str) -> bool:
    """Delete the listing.md and its directory for a given URL.

    Returns True if the file was deleted, False if it didn't exist or on error.
    """
    slug = url_to_slug(url)
    if not slug:
        return False
    listing_dir = _LISTINGS_DIR / job_site / slug
    listing_path = listing_dir / "listing.md"
    if not listing_path.exists():
        return False
    try:
        listing_path.unlink()
        listing_dir.rmdir()  # only succeeds if dir is now empty
        logger.info(f"Deleted {listing_path.relative_to(_LISTINGS_DIR.parent)}")
        return True
    except OSError as e:
        logger.warning(f"Failed to delete listing file for {url}: {e}")
        return False
