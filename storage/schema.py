"""
SQLite schema definitions for all capability databases.

Each capability has its own SQLite database file.
Schema is initialized by scripts/setup_storage.py.
All paths come from CHITRA_DATA_DIR environment variable.
"""

CONTACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    relationship TEXT,
    phone TEXT,
    email TEXT,
    notes TEXT DEFAULT '',
    last_interaction TEXT,
    communication_preference TEXT DEFAULT ''
);
"""

CALENDAR_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    notes TEXT DEFAULT '',
    participants TEXT DEFAULT '[]'
);
"""

REMINDERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    trigger_at TEXT NOT NULL,
    repeat TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'fired', 'dismissed')),
    contact_id TEXT
);
"""

TASKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    notes TEXT DEFAULT '',
    due_date TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'done')),
    priority TEXT DEFAULT 'normal' CHECK(priority IN ('high', 'normal', 'low')),
    created_at TEXT NOT NULL
);
"""

MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL CHECK(category IN ('preference', 'fact', 'observation', 'relationship')),
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'stated' CHECK(source IN ('stated', 'inferred')),
    contact_id TEXT,
    created_at TEXT NOT NULL,
    last_referenced TEXT NOT NULL,
    active INTEGER DEFAULT 1
);
"""

# Map of capability name to (database filename, schema SQL)
SCHEMAS = {
    "contacts": ("contacts.db", CONTACTS_SCHEMA),
    "calendar": ("calendar.db", CALENDAR_SCHEMA),
    "reminders": ("reminders.db", REMINDERS_SCHEMA),
    "tasks": ("tasks.db", TASKS_SCHEMA),
    "memory": ("memory.db", MEMORY_SCHEMA),
}
