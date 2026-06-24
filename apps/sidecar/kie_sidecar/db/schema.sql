CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_usage (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    credits_spent REAL DEFAULT 0,
    started_at TEXT NOT NULL
);

INSERT OR IGNORE INTO session_usage (id, credits_spent, started_at)
VALUES (1, 0, datetime('now'));

CREATE TABLE IF NOT EXISTS chat_folders (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    folder_id TEXT REFERENCES chat_folders(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    model_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content_json TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    credits REAL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chats_updated_at ON chats(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_folder_id ON chats(folder_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id, created_at);

CREATE TABLE IF NOT EXISTS generations (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    model_id TEXT NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL,
    prompt TEXT,
    params_json TEXT,
    credits_used REAL,
    remote_url TEXT,
    local_path TEXT,
    error_msg TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_generations_type_created ON generations(type, created_at DESC);

CREATE TABLE IF NOT EXISTS models_cache (
    id TEXT NOT NULL,
    category TEXT NOT NULL,
    price_hint TEXT,
    estimate_credits REAL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (id, category)
);
