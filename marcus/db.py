import secrets
import sqlite3
import string
from pathlib import Path

class Database:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS identities (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    platform TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    identity_id TEXT NOT NULL REFERENCES identities(id),
                    display_name TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(platform, user_id)
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_messages_context
                    ON messages(platform, chat_id, id);
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_id TEXT NOT NULL REFERENCES identities(id),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_memories_identity ON memories(identity_id, id);
                CREATE TABLE IF NOT EXISTS link_codes (
                    code TEXT PRIMARY KEY,
                    identity_id TEXT NOT NULL REFERENCES identities(id),
                    expires_at INTEGER NOT NULL
                );
            """)

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def ensure_identity(self, platform: str, user_id: str, display_name: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT identity_id FROM accounts WHERE platform=? AND user_id=?",
                (platform, user_id),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE accounts SET display_name=? WHERE platform=? AND user_id=?",
                    (display_name, platform, user_id),
                )
                return row[0]
            identity_id = secrets.token_hex(16)
            conn.execute("INSERT INTO identities(id) VALUES (?)", (identity_id,))
            conn.execute(
                "INSERT INTO accounts(platform,user_id,identity_id,display_name) VALUES(?,?,?,?)",
                (platform, user_id, identity_id, display_name),
            )
            return identity_id

    def add_message(self, platform: str, chat_id: str, user_id: str, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages(platform,chat_id,user_id,role,content) VALUES(?,?,?,?,?)",
                (platform, chat_id, user_id, role, content[:8000]),
            )

    def history(self, platform: str, chat_id: str, limit: int) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role,content FROM messages WHERE platform=? AND chat_id=? ORDER BY id DESC LIMIT ?",
                (platform, chat_id, limit),
            ).fetchall()
        rows.reverse()
        return [{"role": role, "content": content} for role, content in rows]

    def remember(self, identity_id: str, content: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO memories(identity_id,content) VALUES(?,?)",
                (identity_id, content.strip()[:500]),
            )
            return int(cursor.lastrowid)

    def memories(self, identity_id: str, limit: int = 20) -> list[tuple[int, str]]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT id,content FROM memories WHERE identity_id=? ORDER BY id DESC LIMIT ?",
                (identity_id, limit),
            ).fetchall()

    def forget_memory(self, identity_id: str, memory_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE identity_id=? AND id=?",
                (identity_id, memory_id),
            )
            return cursor.rowcount > 0

    def create_link_code(self, identity_id: str) -> str:
        alphabet = string.ascii_uppercase + string.digits
        with self._connect() as conn:
            conn.execute("DELETE FROM link_codes WHERE expires_at < strftime('%s','now')")
            for _ in range(10):
                code = "".join(secrets.choice(alphabet) for _ in range(8))
                try:
                    conn.execute(
                        "INSERT INTO link_codes(code,identity_id,expires_at) VALUES(?,?,strftime('%s','now')+600)",
                        (code, identity_id),
                    )
                    return code
                except sqlite3.IntegrityError:
                    continue
        raise RuntimeError("ساخت کد پیوند ناموفق بود.")

    def redeem_link_code(self, platform: str, user_id: str, display_name: str, code: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT identity_id FROM link_codes WHERE code=? AND expires_at>=strftime('%s','now')",
                (code.strip().upper(),),
            ).fetchone()
            if not row:
                return False
            identity_id = row[0]
            existing = conn.execute(
                "SELECT identity_id FROM accounts WHERE platform=? AND user_id=?",
                (platform, user_id),
            ).fetchone()
            if existing and existing[0] != identity_id:
                return False
            conn.execute(
                "INSERT INTO accounts(platform,user_id,identity_id,display_name) VALUES(?,?,?,?) "
                "ON CONFLICT(platform,user_id) DO UPDATE SET identity_id=excluded.identity_id,display_name=excluded.display_name",
                (platform, user_id, identity_id, display_name),
            )
            conn.execute("DELETE FROM link_codes WHERE code=?", (code.strip().upper(),))
            return True

    def forget_user(self, platform: str, user_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT identity_id FROM accounts WHERE platform=? AND user_id=?",
                (platform, user_id),
            ).fetchone()
            cursor = conn.execute(
                "DELETE FROM messages WHERE platform=? AND user_id=?",
                (platform, user_id),
            )
            deleted = cursor.rowcount
            if row:
                conn.execute("DELETE FROM memories WHERE identity_id=?", (row[0],))
                conn.execute("DELETE FROM link_codes WHERE identity_id=?", (row[0],))
                conn.execute("DELETE FROM accounts WHERE platform=? AND user_id=?", (platform, user_id))
            return deleted
