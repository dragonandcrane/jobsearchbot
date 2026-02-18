"""Extract and categorize keywords from job descriptions."""

import re
import logging

import config
from scrapers.base import JobListing

logger = logging.getLogger(__name__)


def _find_keywords(text: str, keyword_list: list[str]) -> list[str]:
    """Case-insensitive keyword matching against a description text."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for kw in keyword_list:
        # Use word boundary matching for short keywords to avoid false positives
        # For multi-word keywords or those with special chars, use simple containment
        if len(kw) <= 3 or not kw.isalpha():
            pattern = re.escape(kw.lower())
            if re.search(rf"\b{pattern}\b", text_lower):
                found.append(kw)
        else:
            if kw.lower() in text_lower:
                found.append(kw)
    return sorted(set(found))


def extract_keywords(listing: JobListing) -> JobListing:
    """Populate the three keyword fields from the role description."""
    # Use role_description if available, fall back to full_description
    text = listing.role_description or listing.full_description
    combined = f"{text}\n{listing.qualification}\n{listing.education_requirement}"

    listing.keywords_swe = _find_keywords(combined, config.SWE_KEYWORDS)
    listing.keywords_general = _find_keywords(combined, config.GENERAL_KEYWORDS)
    listing.keywords_domain = _find_keywords(combined, config.DOMAIN_KEYWORDS)
    return listing


def process_keywords(listings: list[JobListing]) -> list[JobListing]:
    """Extract keywords for all listings."""
    for listing in listings:
        extract_keywords(listing)
    return listings
