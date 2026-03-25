"""USAJobs.gov scraper using the official REST API."""

import httpx
from bs4 import BeautifulSoup

import config
from scrapers.base import BaseScraper, JobListing

API_URL = "https://data.usajobs.gov/api/search"
RESULTS_PER_PAGE = 250


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "lxml").get_text(separator="\n").strip()


class USAJobsScraper(BaseScraper):
    name = "usajobs"

    def scrape(self) -> list[JobListing]:
        if not config.USAJOBS_API_KEY or not config.USAJOBS_EMAIL:
            self.logger.warning("USAJobs API key or email not set, skipping")
            return []

        headers = {
            "Authorization-Key": config.USAJOBS_API_KEY,
            "User-Agent": config.USAJOBS_EMAIL,
            "Host": "data.usajobs.gov",
        }

        all_listings: list[JobListing] = []
        for keyword in config.SEARCH_KEYWORDS:
            listings = self._search_keyword(keyword, headers)
            all_listings.extend(listings)
        return all_listings

    def _search_keyword(self, keyword: str, headers: dict) -> list[JobListing]:
        listings: list[JobListing] = []
        page = 1
        while True:
            params = {
                "Keyword": keyword,
                "RemoteIndicator": "True",
                "LocationName": "Los Angeles, CA",
                "ResultsPerPage": RESULTS_PER_PAGE,
                "Page": page,
            }
            resp = httpx.get(API_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("SearchResult", {}).get("SearchResultItems", [])
            if not results:
                break

            for item in results:
                obj = item.get("MatchedObjectDescriptor", {})
                listing = self._parse_result(obj)
                if listing:
                    listings.append(listing)

            total = int(
                data.get("SearchResult", {}).get("SearchResultCountAll", 0)
            )
            if page * RESULTS_PER_PAGE >= total:
                break
            page += 1

        self.logger.info(f"  keyword '{keyword}': {len(listings)} results")
        return listings

    def _parse_result(self, obj: dict) -> JobListing | None:
        details = obj.get("UserArea", {}).get("Details", {})

        # Build salary range string
        salary = ""
        remuneration = obj.get("PositionRemuneration", [])
        if remuneration:
            r = remuneration[0]
            lo = r.get("MinimumRange", "")
            hi = r.get("MaximumRange", "")
            period = r.get("Description", "")
            if lo and hi:
                salary = f"${lo} - ${hi} {period}"

        # Extract schedule info
        schedules = obj.get("PositionSchedule", [])
        schedule_name = schedules[0].get("Name", "") if schedules else ""

        # Build full description from major duties + qualifications
        major_duties = _strip_html(details.get("MajorDuties", [""])[0] if details.get("MajorDuties") else "")
        qualifications = _strip_html(details.get("QualificationSummary", ""))
        education = _strip_html(details.get("Education", ""))

        full_description = "\n\n".join(
            part for part in [major_duties, qualifications, education] if part
        )

        org = obj.get("OrganizationName", "")
        dept = obj.get("DepartmentName", "")
        agency = f"{dept} / {org}" if dept and org and dept != org else (dept or org)

        # Contact info
        contact_name = details.get("AgencyContactName", "")
        contact_phone = details.get("AgencyContactPhone", "")
        contact_email = details.get("AgencyContactEmail", "")

        return JobListing(
            job_site="usajobs.gov",
            full_url=obj.get("PositionURI", ""),
            agency_department=agency,
            position=f"{obj.get('PositionTitle', '')} ({schedule_name})",
            salary_range=salary,
            qualification=qualifications,
            education_requirement=education,
            full_description=full_description,
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
        )


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    scraper = USAJobsScraper()
    results = scraper.safe_scrape()
    for r in results[:5]:
        print(f"{r.position} | {r.agency_department} | {r.salary_range}")
    print(f"Total: {len(results)}")
