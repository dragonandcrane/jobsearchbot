import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
USAJOBS_API_KEY = os.getenv("USAJOBS_API_KEY", "")
USAJOBS_EMAIL = os.getenv("USAJOBS_EMAIL", "")

# --- Paths ---
CSV_PATH = Path(
    "/mnt/c/Users/drago/OneDrive - Los Angeles Community College District"
    "/Personal/career/job search 2026/listings.csv"
)
DATA_DIR = Path.home() / ".jobsearchbot"
ORG_CACHE_PATH = DATA_DIR / "org_descriptions.json"
LOG_PATH = DATA_DIR / "bot.log"

# --- Search Terms ---
SEARCH_KEYWORDS = [
    "DevOps Engineer",
    "Software Engineer",
    "Software Developer",
    "SDET",
    "QA Engineer",
    "Site Reliability Engineer",
    "Systems Administrator",
    "IT Specialist",
    "Information Security",
    "Cybersecurity Analyst",
    "Cloud Engineer",
    "Platform Engineer",
    "Infrastructure Engineer",
]

REMOTE_TERMS = ["remote", "telework", "work from home"]

# --- Keyword Lists for Classification ---
SWE_KEYWORDS = [
    "git", "github", "gitlab", "bitbucket",
    "kubernetes", "k8s", "docker", "containers", "podman",
    "aws", "azure", "gcp", "cloud",
    "terraform", "ansible", "puppet", "chef", "saltstack",
    "jenkins", "ci/cd", "github actions", "gitlab ci", "circleci", "argo",
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "c#", ".net",
    "ruby", "perl", "bash", "powershell", "shell scripting",
    "linux", "unix", "windows server", "rhel", "ubuntu", "centos",
    "sql", "postgresql", "mysql", "oracle", "sql server",
    "mongodb", "redis", "elasticsearch", "dynamodb", "cassandra",
    "kafka", "rabbitmq", "sqs", "sns",
    "grafana", "prometheus", "datadog", "splunk", "nagios", "elk",
    "nginx", "apache", "load balancer", "cdn",
    "rest api", "graphql", "grpc", "microservices",
    "react", "angular", "vue", "node.js",
    "selenium", "cypress", "playwright", "pytest", "junit", "testng",
    "vpc", "iam", "s3", "ec2", "lambda", "cloudformation", "cdk",
    "helm", "istio", "service mesh",
    "api gateway", "oauth", "jwt", "saml", "sso",
    "machine learning", "ml", "ai",
    "data pipeline", "etl", "airflow", "spark",
]

GENERAL_KEYWORDS = [
    "powerpoint", "excel", "word", "ms office", "microsoft office",
    "sharepoint", "teams", "outlook",
    "project management", "program management",
    "agile", "scrum", "kanban", "waterfall", "lean",
    "jira", "confluence", "trello", "asana",
    "communication", "stakeholder", "leadership",
    "budget", "procurement", "rfp", "rfi",
    "documentation", "technical writing",
    "training", "mentoring", "onboarding",
    "vendor management", "contract management",
    "itil", "itsm", "servicenow",
    "business continuity", "disaster recovery",
    "change management", "incident management",
    "help desk", "service desk", "tier 1", "tier 2", "tier 3",
    "inventory management", "asset management",
]

DOMAIN_KEYWORDS = [
    "hipaa", "ferpa", "fisma", "fedramp", "fed-ramp",
    "sox", "pci-dss", "pci dss", "pci compliance",
    "nist", "nist 800-53", "nist csf", "rmf", "risk management framework",
    "ato", "authority to operate",
    "508 compliance", "section 508", "ada compliance", "wcag",
    "foia", "freedom of information",
    "clearance", "secret clearance", "top secret", "public trust",
    "cjis", "criminal justice",
    "fips", "cmmc",
    "ehr", "electronic health record", "epic", "cerner",
    "erp", "sap", "peoplesoft", "workday",
    "double-entry accounting", "2-sided accounting", "gaap", "gasb",
    "grant management", "federal grant",
    "student information system", "sis", "banner", "ellucian",
    "lms", "learning management", "canvas", "blackboard", "moodle",
    "gis", "geographic information", "arcgis", "esri",
    "scada", "ics", "industrial control",
    "e-government", "digital services", "civic tech",
]
