"""
Database Layer - SQLite Persistence for Event Registration System
Provides normalized schema, thread-safe connection management, foreign key enforcement,
WAL mode, transactions, and idempotent initialization.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "events_system.db")

# Thread-local storage for SQLite connections to ensure safe multi-threaded access
_local = threading.local()


def get_connection(db_path: str = DATABASE_FILE) -> sqlite3.Connection:
    """
    Get or create a thread-local SQLite connection with optimal concurrency settings.
    - WAL mode enabled for concurrent reads and writes
    - Foreign keys enforced
    - 30-second busy timeout to handle lock contention gracefully
    """
    conn = getattr(_local, "connection", None)
    if conn is None:
        conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging for high-concurrency read/write operations
        conn.execute("PRAGMA journal_mode = WAL;")
        # Enforce foreign key constraints strictly
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        _local.connection = conn
    return conn


@contextlib.contextmanager
def get_db_cursor(db_path: str = DATABASE_FILE) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager providing an atomic database cursor wrapped in a transaction.
    Commits on successful completion; rolls back on unhandled exception.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def init_db(db_path: str = DATABASE_FILE, reset: bool = False) -> None:
    """
    Initialize the SQLite database schema and seed essential demo records.
    Idempotent: safe to run multiple times.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if reset:
        cursor.executescript("""
            DROP TABLE IF EXISTS attendance;
            DROP TABLE IF EXISTS audit_logs;
            DROP TABLE IF EXISTS waitlist;
            DROP TABLE IF EXISTS registrations;
            DROP TABLE IF EXISTS events;
            DROP TABLE IF EXISTS users;
        """)

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Student', 'Organizer', 'Administrator')),
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Suspended'))
        );
    """)

    # 2. Events Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL DEFAULT 'Technical',
            venue TEXT NOT NULL,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK(capacity >= 0),
            status TEXT NOT NULL DEFAULT 'Published' CHECK(status IN ('Draft', 'Published', 'Closed', 'Completed', 'Cancelled')),
            organizer_id TEXT NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # 3. Registrations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK(status IN ('CONFIRMED', 'CANCELLED', 'WAITLISTED', 'ATTENDED')),
            ticket_id TEXT UNIQUE,
            registered_at TEXT NOT NULL,
            cancelled_at TEXT
        );
    """)

    # Partial unique index: A user can only have ONE active registration (CONFIRMED or WAITLISTED) per event
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_active_reg 
        ON registrations(event_id, user_id) 
        WHERE status IN ('CONFIRMED', 'WAITLISTED');
    """)

    # 4. Waitlist Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS waitlist (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            queue_position INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'WAITING' CHECK(status IN ('WAITING', 'PROMOTED', 'CANCELLED')),
            joined_at TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_active_waitlist 
        ON waitlist(event_id, user_id) 
        WHERE status = 'WAITING';
    """)

    # 5. Attendance Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id TEXT PRIMARY KEY,
            registration_id TEXT NOT NULL UNIQUE REFERENCES registrations(id) ON DELETE CASCADE,
            event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            checked_in_at TEXT NOT NULL,
            checked_in_by TEXT NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'PRESENT' CHECK(status IN ('PRESENT', 'EXCUSED'))
        );
    """)

    # 6. Audit Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id TEXT,
            event_id TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );
    """)

    conn.commit()
    seed_demo_data(db_path)


def seed_demo_data(db_path: str = DATABASE_FILE) -> None:
    """Seed initial demo accounts and workshops if the database is newly initialized."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Check if admin already exists
    cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE id = 'admin_sys'")
    if cursor.fetchone()["cnt"] > 0:
        return  # Data already seeded

    now = datetime.now().isoformat()

    # Import hash_password from auth for genuine PBKDF2 hashes
    import auth
    demo_password_hash = auth.hash_password("Password123!", iterations=100000)

    demo_users = [
        ("admin_sys", "System Administrator", "admin@university.edu", demo_password_hash, "Administrator", now),
        ("prof_turner", "Prof. Alan Turner", "turner@cs.university.edu", demo_password_hash, "Organizer", now),
        ("student_alice", "Alice Johnson", "alice@student.edu", demo_password_hash, "Student", now),
        ("student_bob", "Bob Smith", "bob@student.edu", demo_password_hash, "Student", now),
        ("student_carol", "Carol Williams", "carol@student.edu", demo_password_hash, "Student", now),
        ("S1", "Student S1", "s1@student.edu", demo_password_hash, "Student", now),
        ("S2", "Student S2", "s2@student.edu", demo_password_hash, "Student", now),
        ("S3", "Student S3", "s3@student.edu", demo_password_hash, "Student", now),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO users (id, display_name, email, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, demo_users)

    demo_events = [
        (
            "E1",
            "Python Concurrency Workshop",
            "Deep dive into multi-threading, mutual exclusion (threading.Lock), and OS race conditions.",
            "Systems & OS",
            "Turing Lab 301",
            "2026-11-15 10:00:00",
            "2026-11-15 13:00:00",
            2,
            "Published",
            "prof_turner",
            now,
            now,
        ),
        (
            "E2",
            "Distributed Systems Seminar",
            "Exploration of consensus protocols, Paxos, Raft, and distributed mutual exclusion.",
            "Distributed Systems",
            "Lovelace Auditorium",
            "2026-11-22 14:00:00",
            "2026-11-22 17:00:00",
            5,
            "Published",
            "prof_turner",
            now,
            now,
        ),
        (
            "E3",
            "Operating Systems Masterclass",
            "Deadlock prevention, Coffman conditions, paging architectures, and kernel CPU scheduling.",
            "Core Systems",
            "Von Neumann Hall",
            "2026-12-05 09:30:00",
            "2026-12-05 12:30:00",
            10,
            "Published",
            "prof_turner",
            now,
            now,
        ),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO events 
        (id, title, description, category, venue, start_datetime, end_datetime, capacity, status, organizer_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, demo_events)

    conn.commit()

    # Automatically seed the 20 sample events into fresh installations
    try:
        import seed_events
        seed_events.seed_events(db_path)
    except Exception:
        pass


# Auto-initialize database on module import
init_db()
