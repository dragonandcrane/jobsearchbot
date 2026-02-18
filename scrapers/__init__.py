from .usajobs import USAJobsScraper
from .governmentjobs import GovernmentJobsScraper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper

ALL_SCRAPERS = [USAJobsScraper, GovernmentJobsScraper, IndeedScraper, LinkedInScraper]
