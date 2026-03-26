import logging
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class JobListing:
    job_site: str = ""
    full_url: str = ""
    location: str = ""
    agency_department: str = ""
    position: str = ""
    salary_range: str = ""
    qualification: str = ""
    education_requirement: str = ""
    full_description: str = ""
    # Detail page metadata
    job_type: str = ""
    remote: str = ""
    department: str = ""
    closing_date: str = ""
    # Contact info
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    # These are populated by processing steps, not scrapers
    org_boilerplate: str = ""
    role_description: str = ""
    keywords_swe: list[str] = field(default_factory=list)
    keywords_general: list[str] = field(default_factory=list)
    keywords_domain: list[str] = field(default_factory=list)


class BaseScraper(ABC):
    name: str = "base"

    def __init__(self):
        self.logger = logging.getLogger(f"scrapers.{self.name}")

    @abstractmethod
    def scrape(self, limit: int | None = None) -> list[JobListing]:
        """Run the scraper and return a list of raw JobListings.

        limit: stop early after collecting this many listings.
        """
        ...

    def safe_scrape(self, limit: int | None = None) -> list[JobListing]:
        """Wrap scrape() with error handling so one scraper can't crash the run."""
        try:
            results = self.scrape(limit=limit)
            self.logger.info(f"{self.name}: found {len(results)} listings")
            return results
        except Exception:
            self.logger.exception(f"{self.name}: scraper failed")
            return []
