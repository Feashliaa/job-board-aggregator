GREENHOUSE_FILE_NAME = "personal_greenhouse_companies.json"

US_LOCATION_PATTERNS = (
    "united states",
    "u.s.",
    "usa",
    "us remote",
    "remote, us",
    "remote - us",
    "remote (us)",
    "remote - united states",
    "remote (united states)"
)

US_STATE_ABBREVIATIONS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC"
}

COMPANY_BLOCKLIST = {
    "lensa"
}


TITLE_TERMS = () # ("data scientist", "machine learning engineer", "data analyst")


MAX_PUBLISHED_JOBS = 10_000