"""SQLite database for tracking application links and status."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class Database:
    """Manages SQLite database for tracking internship applications."""

    def __init__(self, db_path: str = "data/applications.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    resolved_url TEXT,
                    source_account TEXT,
                    story_timestamp TEXT,
                    discovered_at TEXT NOT NULL,
                    status TEXT DEFAULT 'new',
                    company_name TEXT,
                    job_title TEXT,
                    platform TEXT,
                    notes TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_id INTEGER NOT NULL,
                    applied_at TEXT NOT NULL,
                    form_data TEXT,
                    status TEXT DEFAULT 'submitted',
                    follow_up_date TEXT,
                    notes TEXT,
                    FOREIGN KEY (link_id) REFERENCES links(id)
                )
            """)
            conn.commit()

    def add_link(
        self,
        url: str,
        source_account: str,
        story_timestamp: Optional[str] = None,
        resolved_url: Optional[str] = None,
    ) -> Optional[int]:
        """Add a new link to the database. Returns link ID or None if duplicate."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO links (url, resolved_url, source_account, story_timestamp, discovered_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        url,
                        resolved_url,
                        source_account,
                        story_timestamp,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def link_exists(self, url: str) -> bool:
        """Check if a link already exists in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT 1 FROM links WHERE url = ?", (url,))
            return cursor.fetchone() is not None

    def get_new_links(self) -> list[dict]:
        """Get all links with 'new' status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM links WHERE status = 'new' ORDER BY discovered_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_all_links(self, status: Optional[str] = None) -> list[dict]:
        """Get all links, optionally filtered by status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                cursor = conn.execute(
                    "SELECT * FROM links WHERE status = ? ORDER BY discovered_at DESC",
                    (status,),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM links ORDER BY discovered_at DESC"
                )
            return [dict(row) for row in cursor.fetchall()]

    def update_link_status(self, link_id: int, status: str) -> None:
        """Update the status of a link."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE links SET status = ? WHERE id = ?",
                (status, link_id),
            )
            conn.commit()

    def update_link_info(
        self,
        link_id: int,
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        platform: Optional[str] = None,
        resolved_url: Optional[str] = None,
    ) -> None:
        """Update link metadata."""
        updates = []
        values = []
        if company_name is not None:
            updates.append("company_name = ?")
            values.append(company_name)
        if job_title is not None:
            updates.append("job_title = ?")
            values.append(job_title)
        if platform is not None:
            updates.append("platform = ?")
            values.append(platform)
        if resolved_url is not None:
            updates.append("resolved_url = ?")
            values.append(resolved_url)

        if updates:
            values.append(link_id)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"UPDATE links SET {', '.join(updates)} WHERE id = ?",
                    values,
                )
                conn.commit()

    def record_application(
        self,
        link_id: int,
        form_data: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Record a submitted application."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO applications (link_id, applied_at, form_data, notes)
                VALUES (?, ?, ?, ?)
                """,
                (link_id, datetime.now().isoformat(), form_data, notes),
            )
            conn.execute(
                "UPDATE links SET status = 'applied' WHERE id = ?",
                (link_id,),
            )
            conn.commit()
            return cursor.lastrowid

    def get_applications(self) -> list[dict]:
        """Get all recorded applications with link info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT a.*, l.url, l.company_name, l.job_title, l.platform
                FROM applications a
                JOIN links l ON a.link_id = l.id
                ORDER BY a.applied_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """Get statistics about links and applications."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            cursor = conn.execute(
                "SELECT status, COUNT(*) FROM links GROUP BY status"
            )
            stats["links_by_status"] = dict(cursor.fetchall())
            cursor = conn.execute("SELECT COUNT(*) FROM applications")
            stats["total_applications"] = cursor.fetchone()[0]
            return stats
