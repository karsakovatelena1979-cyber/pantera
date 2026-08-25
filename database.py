import aiosqlite
import logging

logger = logging.getLogger(__name__)
DB_PATH = "bot.db"


class Database:
    def __init__(self):
        self.db: aiosqlite.Connection | None = None

    async def init(self):
        self.db = await aiosqlite.connect(DB_PATH)
        self.db.row_factory = aiosqlite.Row
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT    DEFAULT '',
                is_paid     INTEGER DEFAULT 0,
                state       TEXT    DEFAULT 'start',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                message_id  INTEGER,
                status      TEXT    DEFAULT 'pending',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self.db.commit()
        logger.info("БД инициализирована")

    # ─── USERS ──────────────────────────────────────

    async def add_user(self, user_id: int, username: str):
        await self.db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        # Обновляем username если изменился
        await self.db.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id)
        )
        await self.db.commit()

    async def add_paid_user(self, user_id: int):
        await self.db.execute(
            "UPDATE users SET is_paid = 1 WHERE user_id = ?",
            (user_id,)
        )
        await self.db.commit()

    async def get_user_state(self, user_id: int) -> str:
        async with self.db.execute(
            "SELECT state FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row["state"] if row else "start"

    async def set_user_state(self, user_id: int, state: str):
        await self.db.execute(
            "UPDATE users SET state = ? WHERE user_id = ?",
            (state, user_id)
        )
        await self.db.commit()

    async def get_all_users(self) -> list[int]:
        async with self.db.execute("SELECT user_id FROM users") as cur:
            rows = await cur.fetchall()
            return [r["user_id"] for r in rows]

    async def get_all_users_info(self) -> list[dict]:
        async with self.db.execute(
            "SELECT user_id, username FROM users ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # ─── REQUESTS ───────────────────────────────────

    async def create_request(self, user_id: int, message_id: int) -> int:
        async with self.db.execute(
            "INSERT INTO requests (user_id, message_id) VALUES (?, ?)",
            (user_id, message_id)
        ) as cur:
            await self.db.commit()
            return cur.lastrowid

    async def has_pending_request(self, user_id: int) -> bool:
        async with self.db.execute(
            "SELECT id FROM requests WHERE user_id = ? AND status = 'pending'",
            (user_id,)
        ) as cur:
            return await cur.fetchone() is not None

    async def update_request_status(self, request_id: int, status: str):
        await self.db.execute(
            "UPDATE requests SET status = ? WHERE id = ?",
            (status, request_id)
        )
        await self.db.commit()

    async def get_pending_requests(self) -> list[dict]:
        async with self.db.execute("""
            SELECT r.id, r.user_id, u.username
            FROM requests r
            LEFT JOIN users u ON u.user_id = r.user_id
            WHERE r.status = 'pending'
            ORDER BY r.created_at
        """) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # ─── STATS ──────────────────────────────────────

    async def get_stats(self) -> dict:
        async with self.db.execute("SELECT COUNT(*) as c FROM users") as cur:
            total_users = (await cur.fetchone())["c"]

        async with self.db.execute("SELECT COUNT(*) as c FROM users WHERE is_paid = 1") as cur:
            paid_users = (await cur.fetchone())["c"]

        async with self.db.execute("SELECT COUNT(*) as c FROM requests") as cur:
            total_requests = (await cur.fetchone())["c"]

        async with self.db.execute("SELECT COUNT(*) as c FROM requests WHERE status = 'pending'") as cur:
            pending = (await cur.fetchone())["c"]

        async with self.db.execute("SELECT COUNT(*) as c FROM requests WHERE status = 'approved'") as cur:
            approved = (await cur.fetchone())["c"]

        async with self.db.execute("SELECT COUNT(*) as c FROM requests WHERE status = 'rejected'") as cur:
            rejected = (await cur.fetchone())["c"]

        return {
            "total_users": total_users,
            "paid_users": paid_users,
            "total_requests": total_requests,
            "pending_requests": pending,
            "approved_requests": approved,
            "rejected_requests": rejected,
        }
