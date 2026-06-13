# =========================================================
# GOOGLE OAUTH
# =========================================================

GOOGLE_AUTH_URL = (
    "https://accounts.google.com/o/oauth2/v2/auth"
)

GOOGLE_TOKEN_URL = (
    "https://oauth2.googleapis.com/token"
)

GOOGLE_REVOKE_URL = (
    "https://oauth2.googleapis.com/revoke"
)

GOOGLE_USER_INFO_URL = (
    "https://www.googleapis.com/oauth2/v2/userinfo"
)

# =========================================================
# GOOGLE CALENDAR
# =========================================================

GOOGLE_CALENDAR_BASE_URL = (
    "https://www.googleapis.com/calendar/v3"
)

GOOGLE_CALENDAR_EVENTS_URL = (
    "https://www.googleapis.com/calendar/v3/calendars"
)

# =========================================================
# SCOPES
# =========================================================

GOOGLE_SCOPES = [

    # Identity

    "openid",

    "email",

    "profile",

    # Calendar

    "https://www.googleapis.com/auth/calendar.events",
]

# =========================================================
# DEFAULTS
# =========================================================

GOOGLE_DEFAULT_CALENDAR_ID = (
    "primary"
)

REQUEST_TIMEOUT_SECONDS = 15