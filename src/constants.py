"""Application constants to avoid magic numbers and strings."""

# Time and Date Constants
DEFAULT_TIMEZONE = 'Europe/Berlin'
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60

# Rate Limiting
DEFAULT_RATE_LIMIT_REQUESTS = 20
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds
AI_RATE_LIMIT_REQUESTS = 10
AI_RATE_LIMIT_WINDOW = 60

# Message Limits
MAX_TELEGRAM_MESSAGE_LENGTH = 4096
MAX_APPOINTMENT_TITLE_LENGTH = 200
MAX_MEMO_TITLE_LENGTH = 200

# Pagination
DEFAULT_APPOINTMENTS_LIMIT = 10
MAX_APPOINTMENTS_LIMIT = 50

# Email Processing
EMAIL_FETCH_LIMIT = 500
EMAIL_SYNC_INTERVAL = 300  # seconds

# Notion API
NOTION_PAGE_SIZE = 100
NOTION_MAX_RETRIES = 3

# Bot Commands
BOT_COMMANDS = [
    ("start", "🎛️ Hauptmenü öffnen"),
    ("menu", "🎛️ Menü anzeigen"), 
    ("today", "📅 Heutige Termine"),
    ("tomorrow", "📅 Morgige Termine"),
    ("add", "➕ Termin hinzufügen"),
    ("list", "📋 Alle Termine"),
    ("reminder", "⚙️ Erinnerungen"),
    ("help", "❓ Hilfe")
]

# Status Messages
class StatusEmojis:
    SUCCESS = "✅"
    ERROR = "❌" 
    WARNING = "⚠️"
    INFO = "ℹ️"
    PENDING = "⏳"
    PRIVATE = "👤"
    SHARED = "🌐"

# Menu Buttons
class MenuButtons:
    TODAY_TOMORROW = "📅 Termine Heute & Morgen"
    RECENT_MEMOS = "📝 Letzte 10 Memos" 
    NEW_APPOINTMENT = "➕ Neuer Termin"
    NEW_MEMO = "➕ Neues Memo"
    HELP = "❓ Hilfe"
    
# Callback Data
class CallbackData:
    TODAY_TOMORROW = "today_tomorrow"
    RECENT_MEMOS = "recent_memos"
    ADD_APPOINTMENT = "add_appointment"
    ADD_MEMO = "add_memo"
    HELP = "help"
    PARTNER_RELEVANT_YES = "partner_relevant_yes"
    PARTNER_RELEVANT_NO = "partner_relevant_no"

# Default Values
DEFAULT_REMINDER_TIME = "08:00"
DEFAULT_MEMO_STATUS = "Nicht begonnen"

# Validation
MIN_PASSWORD_LENGTH = 8
MAX_INPUT_LENGTH = 1000
MAX_DESCRIPTION_LENGTH = 1000
MAX_LOCATION_LENGTH = 200
MAX_MEMO_NOTES_LENGTH = 2000
MAX_CATEGORY_LENGTH = 100
MAX_PROJECT_LENGTH = 100
MAX_ERROR_MESSAGE_LENGTH = 100
MAX_NOTES_PREVIEW_LENGTH = 100

# File Paths
USERS_CONFIG_FILE = "users_config.json"
LOG_FILE = "bot.log"

# AI Service
AI_MODEL = "gpt-4o-mini"
AI_TEMPERATURE = 0.2
AI_MAX_TOKENS = 500
AI_MAX_RETRIES = 3
AI_RETRY_DELAY = 1
AI_TIMEOUT = 30
AI_FALLBACK_CONFIDENCE = 0.6
AI_MIN_CONFIDENCE = 0.5

# Email Processing
EMAIL_RECONNECT_MAX_ATTEMPTS = 3
EMAIL_CONNECTION_TIMEOUT = 10
BUSINESS_CALENDAR_LOOKBACK_DAYS = 30

# Memo Status
MEMO_STATUS_NOT_STARTED = "Nicht begonnen"
MEMO_STATUS_IN_PROGRESS = "In Arbeit"
MEMO_STATUS_COMPLETED = "Erledigt"

# Time Parsing
DEFAULT_TIME = "09:00"
QUARTER_MINUTES = 15
HALF_HOUR_MINUTES = 30
THREE_QUARTER_MINUTES = 45

# Partner Sync
PARTNER_SYNC_INTERVAL_HOURS = 2

# Debug
MAX_DEBUG_OUTPUT_LENGTH = 30000