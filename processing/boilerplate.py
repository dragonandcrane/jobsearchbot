"""Detect org-generic boilerplate vs role-specific description text.

Strategy: maintain a cache of description paragraphs per org. When a paragraph
appears across 2+ listings from the same org (similarity >= 0.85), it's
boilerplate. Everything else is role-specific.
"""

import json
import logging
from difflib import SequenceMatcher
from pathlib import Path

import config
from scrapers.base import JobListing

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.85


def _load_cache() -> dict[str, list[list[str]]]:
    """Load org -> [[paragraphs from listing 1], [paragraphs from listing 2], ...]"""
    if config.ORG_CACHE_PATH.exists():
        try:
            return json.loads(config.ORG_CACHE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt org cache, starting fresh")
    return {}


def _save_cache(cache: dict[str, list[list[str]]]) -> None:
    config.ORG_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.ORG_CACHE_PATH.write_text(json.dumps(cache, indent=2))


def _split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _is_similar(a: str, b: str) -> bool:
    """Check if two paragraphs are similar enough to be boilerplate."""
    if not a or not b:
        return False
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= SIMILARITY_THRESHOLD


def detect_boilerplate(listing: JobListing) -> tuple[str, str]:
    """Split listing.full_description into (boilerplate, role_specific).

    Returns (org_boilerplate, role_description) strings.
    """
    org = listing.agency_department.strip()
    if not org or not listing.full_description:
        return "", listing.full_description

    cache = _load_cache()
    paragraphs = _split_paragraphs(listing.full_description)

    org_history = cache.get(org, [])

    boilerplate_paragraphs = []
    role_paragraphs = []

    for para in paragraphs:
        is_boilerplate = False
        # Check if this paragraph appears in any previous listing from same org
        for prev_listing_paras in org_history:
            for prev_para in prev_listing_paras:
                if _is_similar(para, prev_para):
                    is_boilerplate = True
                    break
            if is_boilerplate:
                break

        if is_boilerplate:
            boilerplate_paragraphs.append(para)
        else:
            role_paragraphs.append(para)

    # Add current listing's paragraphs to cache
    org_history.append(paragraphs)
    # Keep last 20 listings per org to avoid unbounded growth
    cache[org] = org_history[-20:]
    _save_cache(cache)

    return (
        "\n\n".join(boilerplate_paragraphs),
        "\n\n".join(role_paragraphs) if role_paragraphs else listing.full_description,
    )


def process_boilerplate(listings: list[JobListing]) -> list[JobListing]:
    """Process all listings to split descriptions into boilerplate + role-specific."""
    for listing in listings:
        boilerplate, role_desc = detect_boilerplate(listing)
        listing.org_boilerplate = boilerplate
        listing.role_description = role_desc
    return listings
