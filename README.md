Topic: Job Search Bot

write a simple bot in python that scrapes the web for job openings that meet my requirements:
- DevOps, SWE, SDET, IT, InfoSec, or related
- public or nonprofit sector
- 100% remote
- full time with flexible hours or part time - i am unavailable between 4-9pm
- prioritize stability and flexibility over salary and excitement

store fields:
- job site (eg governmentjobs.com)
- full job url
- agency/department
- position
- salary range
- qualification
- education requirement
- org-generic boilerplate*
- role-specific description (block of text)
- keywords: SWE tools and technologies (eg "git", "kubernetes")
- keywords: non-SWE industry-wide (eg "powerpoint", "project management")
- keywords: domain- or vertical-specific ("2-sided accounting", "HIPAA compliance")

* to determine which part of role description is boilerplate, check other listings (including non-technical ones) from the same role

the search should run automatically daily at 9am and 6pm

the output of the search should update a CSV file stored on my OneDrive to ensure sync across my devices:
C:\Users\drago\OneDrive - Los Angeles Community College District\Personal\career\job search 2026\listings.csv



