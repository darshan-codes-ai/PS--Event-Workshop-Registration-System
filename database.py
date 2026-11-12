"""
database.py - Database Layer for EventFlow OS
Simple, robust SQLite persistence with WAL mode and foreign key enforcement.
"""

import contextlib
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "events_system.db")
_local = threading.local()

# 10 Required Academic Workshops
SAMPLE_EVENTS = [
    {
        "event_id": "EVT-01",
        "title": "AI & Machine Learning Workshop",
        "description": "Hands-on neural networks, deep learning models, and real-time computer vision deployment.",
        "date": "2026-11-20 10:00 AM",
        "venue": "Auditorium Hall A",
        "capacity": 35,
    },
    {
        "event_id": "EVT-02",
        "title": "Python Programming Bootcamp",
        "description": "Master clean code, OOP architecture, concurrency primitives, and asynchronous Python.",
        "date": "2026-11-22 09:30 AM",
        "venue": "Software Lab 3",
        "capacity": 50,
    },
    {
        "event_id": "EVT-03",
        "title": "Cloud Computing with AWS",
        "description": "Architecting resilient distributed systems using EC2, Lambda, S3, and VPC networking.",
        "date": "2026-11-25 11:00 AM",
        "venue": "Cloud Computing Center",
        "capacity": 35,
    },
    {
        "event_id": "EVT-04",
        "title": "Cybersecurity Essentials",
        "description": "Network penetration testing, cryptographic protocols, defense in depth, and threat modeling.",
        "date": "2026-11-28 02:00 PM",
        "venue": "Cyber Defense Lab",
        "capacity": 40,
    },
    {
        "event_id": "EVT-05",
        "title": "Full-Stack Web Development Hackathon",
        "description": "Build and ship complete production web applications with modern frontend and REST APIs.",
        "date": "2026-12-01 09:00 AM",
        "venue": "Innovation Hub Room 102",
        "capacity": 40,
    },
    {
        "event_id": "EVT-06",
        "title": "Data Science & Analytics Workshop",
        "description": "Exploratory data analysis, statistical inferencing, predictive modeling, and data pipelines.",
        "date": "2026-12-04 10:30 AM",
        "venue": "Data Systems Lab 2",
        "capacity": 35,
    },
    {
        "event_id": "EVT-07",
        "title": "IoT & Smart Embedded Systems",
        "description": "Interfacing microcontrollers, sensor telemetry streams, MQTT messaging, and Edge AI.",
        "date": "2026-12-07 01:30 PM",
        "venue": "Hardware & Embedded Lab",
        "capacity": 30,
    },
    {
        "event_id": "EVT-08",
        "title": "Git & GitHub Masterclass",
        "description": "Branching strategies, interactive rebasing, merge conflict resolution, and CI/CD workflows.",
        "date": "2026-12-10 11:00 AM",
        "venue": "Seminar Hall B",
        "capacity": 45,
    },
    {
        "event_id": "EVT-09",
        "title": "Competitive Programming & DSA",
        "description": "Advanced tree structures, dynamic programming paradigms, graph algorithms, and Big-O mastery.",
        "date": "2026-12-14 10:00 AM",
        "venue": "Algorithms Theater",
        "capacity": 60,
    },
    {
        "event_id": "EVT-10",
        "title": "Tech Startup & Innovation Seminar",
        "description": "From ideation to MVP: product-market fit, software unit economics, and pitching to investors.",
        "date": "2026-12-18 03:00 PM",
        "venue": "Main Campus Auditorium",
        "capacity": 50,
    },
]


def get_connection(db_path: str = DATABASE_FILE) -> sqlite3.Connection:
    """Get or create a thread-local SQLite connection with WAL mode and foreign keys enabled."""
    abs_path = os.path.abspath(db_path)
    connections = getattr(_local, "connections", None)
    if connections is None:
        connections = {}
        _local.connections = connections

    conn = connections.get(abs_path)
    if conn is None:
        conn = sqlite3.connect(abs_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        connections[abs_path] = conn
    return conn


def close_connection(db_path: Optional[str] = None) -> None:
    """Close thread-local connection for a specific path or all active connections."""
    connections = getattr(_local, "connections", None)
    if not connections:
        return
    if db_path is not None:
        abs_path = os.path.abspath(db_path)
        conn = connections.pop(abs_path, None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    else:
        for conn in list(connections.values()):
            try:
                conn.close()
            except Exception:
                pass
        connections.clear()


@contextlib.contextmanager
def get_db_cursor(db_path: str = DATABASE_FILE) -> Generator[sqlite3.Cursor, None, None]:
    """Transactional cursor context manager with automatic commit and rollback."""
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
    """Initialize essential SQLite tables and seed default events idempotently."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if reset:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.executescript("""
            DROP TABLE IF EXISTS attendance;
            DROP TABLE IF EXISTS audit_logs;
            DROP TABLE IF EXISTS waitlist;
            DROP TABLE IF EXISTS registrations;
            DROP TABLE IF EXISTS events;
            DROP TABLE IF EXISTS users;
        """)
        cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            venue TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK(capacity > 0)
        );

        CREATE TABLE IF NOT EXISTS registrations (
            registration_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
            student_name TEXT NOT NULL,
            email TEXT NOT NULL,
            registration_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK(status IN ('CONFIRMED', 'CANCELLED'))
        );

        CREATE INDEX IF NOT EXISTS idx_reg_event ON registrations(event_id);
        CREATE INDEX IF NOT EXISTS idx_reg_email ON registrations(email);
        CREATE INDEX IF NOT EXISTS idx_reg_status ON registrations(status);
    """)
    conn.commit()

    seed_events(db_path)
    if os.path.abspath(db_path) == os.path.abspath(DATABASE_FILE):
        seed_sample_registrations(db_path)


def seed_events(db_path: str = DATABASE_FILE) -> None:
    """Idempotently seed the 10 standard academic workshops."""
    with get_db_cursor(db_path) as cursor:
        for ev in SAMPLE_EVENTS:
            cursor.execute("SELECT COUNT(*) AS cnt FROM events WHERE event_id = ?", (ev["event_id"],))
            if cursor.fetchone()["cnt"] == 0:
                cursor.execute("""
                    INSERT INTO events (event_id, title, description, date, venue, capacity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (ev["event_id"], ev["title"], ev["description"], ev["date"], ev["venue"], ev["capacity"]))


def seed_sample_registrations(db_path: str = DATABASE_FILE) -> None:
    """Seed a small realistic baseline of sample registrations."""
    with get_db_cursor(db_path) as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM registrations")
        if cursor.fetchone()["cnt"] > 0:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        samples = [
            ("REG-1001", "EVT-01", "Alice Johnson", "alice@student.edu", now, "CONFIRMED"),
            ("REG-1002", "EVT-01", "Bob Smith", "bob@student.edu", now, "CONFIRMED"),
            ("REG-1003", "EVT-02", "Alice Johnson", "alice@student.edu", now, "CONFIRMED"),
            ("REG-1004", "EVT-03", "Carol White", "carol@student.edu", now, "CONFIRMED"),
        ]
        cursor.executemany("""
            INSERT INTO registrations (registration_id, event_id, student_name, email, registration_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, samples)


def get_all_events(db_path: str = DATABASE_FILE) -> List[Dict[str, Any]]:
    """Retrieve all events along with active confirmed registration counts and available seats."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            e.event_id,
            e.title,
            e.description,
            e.date,
            e.venue,
            e.capacity,
            COUNT(CASE WHEN r.status = 'CONFIRMED' THEN 1 END) AS confirmed_count,
            (e.capacity - COUNT(CASE WHEN r.status = 'CONFIRMED' THEN 1 END)) AS available_seats
        FROM events e
        LEFT JOIN registrations r ON e.event_id = r.event_id
        GROUP BY e.event_id
        ORDER BY e.event_id ASC
    """)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_event_by_id(event_id: str, db_path: str = DATABASE_FILE) -> Optional[Dict[str, Any]]:
    """Retrieve a single event by ID with available seats calculation."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            e.event_id,
            e.title,
            e.description,
            e.date,
            e.venue,
            e.capacity,
            COUNT(CASE WHEN r.status = 'CONFIRMED' THEN 1 END) AS confirmed_count,
            (e.capacity - COUNT(CASE WHEN r.status = 'CONFIRMED' THEN 1 END)) AS available_seats
        FROM events e
        LEFT JOIN registrations r ON e.event_id = r.event_id
        WHERE e.event_id = ?
        GROUP BY e.event_id
    """, (event_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_registrations_by_email(email: str, db_path: str = DATABASE_FILE) -> List[Dict[str, Any]]:
    """Retrieve active registrations for a given student email."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            r.registration_id,
            r.event_id,
            e.title AS event_title,
            e.date AS event_date,
            e.venue AS event_venue,
            r.student_name,
            r.email,
            r.registration_date,
            r.status
        FROM registrations r
        JOIN events e ON r.event_id = e.event_id
        WHERE LOWER(TRIM(r.email)) = LOWER(TRIM(?)) AND r.status = 'CONFIRMED'
        ORDER BY r.registration_date DESC
    """, (email,))
    return [dict(row) for row in cursor.fetchall()]


def get_all_registrations(db_path: str = DATABASE_FILE) -> List[Dict[str, Any]]:
    """Retrieve all registrations for display or audit."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            r.registration_id,
            r.event_id,
            e.title AS event_title,
            r.student_name,
            r.email,
            r.registration_date,
            r.status
        FROM registrations r
        JOIN events e ON r.event_id = e.event_id
        ORDER BY r.registration_date DESC
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_kpis(db_path: str = DATABASE_FILE) -> Dict[str, int]:
    """Calculate the 4 core dashboard KPI numbers."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total_events, COALESCE(SUM(capacity), 0) AS total_capacity FROM events")
    row_ev = cursor.fetchone()
    total_events = row_ev["total_events"] if row_ev else 0
    total_capacity = row_ev["total_capacity"] if row_ev else 0

    cursor.execute("SELECT COUNT(*) AS total_confirmed FROM registrations WHERE status = 'CONFIRMED'")
    row_reg = cursor.fetchone()
    total_confirmed = row_reg["total_confirmed"] if row_reg else 0

    available_seats = max(0, total_capacity - total_confirmed)

    return {
        "total_events": total_events,
        "total_registrations": total_confirmed,
        "available_seats": available_seats,
        "total_capacity": total_capacity,
    }


if __name__ == "__main__":
    init_db(reset=True)
    print("Database initialized successfully.")
    print("KPIs:", get_kpis())
