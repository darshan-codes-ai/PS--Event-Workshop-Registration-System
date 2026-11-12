"""
services.py - Business Logic and Mutex-Protected Registration Services
Enforces critical section synchronization around seat checks, duplicate prevention, and booking.
"""

import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import database

# Process-level Mutex Lock for critical section protection
_system_lock = threading.Lock()


def get_system_lock() -> threading.Lock:
    """Return the shared system mutex lock."""
    return _system_lock


def register_student(
    event_id: str,
    student_name: str,
    email: str,
    db_path: str = database.DATABASE_FILE,
    lock: Optional[threading.Lock] = None,
) -> Dict[str, Any]:
    """
    Register a student for a workshop with mutex protection.
    The mutex guarantees that checking availability and inserting registration
    are executed atomically without concurrent race conditions.
    """
    event_id_clean = event_id.strip()
    name_clean = student_name.strip()
    email_clean = email.strip().lower()

    if not event_id_clean:
        return {"success": False, "status": "ERROR", "message": "Event ID is required."}
    if not name_clean:
        return {"success": False, "status": "ERROR", "message": "Student name cannot be empty."}
    if not email_clean or "@" not in email_clean:
        return {"success": False, "status": "ERROR", "message": "A valid email address is required."}

    sync_lock = lock if lock is not None else _system_lock

    # Acquire Mutex to enter Critical Section
    sync_lock.acquire()
    try:
        # --- CRITICAL SECTION BEGINS ---
        with database.get_db_cursor(db_path) as cursor:
            # 1. Fetch event and capacity
            cursor.execute("SELECT event_id, title, capacity FROM events WHERE event_id = ?", (event_id_clean,))
            event = cursor.fetchone()
            if not event:
                return {"success": False, "status": "NOT_FOUND", "message": f"Workshop '{event_id_clean}' not found."}

            capacity = event["capacity"]
            title = event["title"]

            # 2. Check for duplicate registration (same email on same event with CONFIRMED status)
            cursor.execute("""
                SELECT registration_id FROM registrations 
                WHERE event_id = ? AND LOWER(email) = ? AND status = 'CONFIRMED'
            """, (event_id_clean, email_clean))
            existing = cursor.fetchone()
            if existing:
                return {
                    "success": False,
                    "status": "DUPLICATE",
                    "message": f"Student '{name_clean}' ({email_clean}) is already registered for '{title}'.",
                    "registration_id": existing["registration_id"],
                }

            # 3. Check current confirmed registrations count
            cursor.execute("""
                SELECT COUNT(*) AS confirmed_count FROM registrations 
                WHERE event_id = ? AND status = 'CONFIRMED'
            """, (event_id_clean,))
            confirmed_count = cursor.fetchone()["confirmed_count"]

            if confirmed_count >= capacity:
                return {
                    "success": False,
                    "status": "FULL",
                    "message": f"Workshop '{title}' is FULL ({confirmed_count}/{capacity} seats booked).",
                    "available_seats": 0,
                }

            # 4. Capacity is available: proceed with registration
            reg_id = f"REG-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO registrations (registration_id, event_id, student_name, email, registration_date, status)
                VALUES (?, ?, ?, ?, ?, 'CONFIRMED')
            """, (reg_id, event_id_clean, name_clean, email_clean, now))

            remaining_seats = capacity - (confirmed_count + 1)

            return {
                "success": True,
                "status": "CONFIRMED",
                "message": f"Registration successful for '{title}'. Seat confirmed!",
                "registration_id": reg_id,
                "event_id": event_id_clean,
                "event_title": title,
                "student_name": name_clean,
                "email": email_clean,
                "available_seats": remaining_seats,
            }
        # --- CRITICAL SECTION ENDS ---
    finally:
        sync_lock.release()


def cancel_registration(
    registration_id: str,
    db_path: str = database.DATABASE_FILE,
    lock: Optional[threading.Lock] = None,
) -> Dict[str, Any]:
    """
    Cancel an active registration and free up the seat.
    Protected with the mutex lock to prevent concurrent state discrepancies.
    """
    reg_id_clean = registration_id.strip()
    if not reg_id_clean:
        return {"success": False, "status": "ERROR", "message": "Registration ID is required."}

    sync_lock = lock if lock is not None else _system_lock

    sync_lock.acquire()
    try:
        with database.get_db_cursor(db_path) as cursor:
            cursor.execute("""
                SELECT r.registration_id, r.event_id, r.status, e.title 
                FROM registrations r
                JOIN events e ON r.event_id = e.event_id
                WHERE r.registration_id = ?
            """, (reg_id_clean,))
            reg = cursor.fetchone()

            if not reg:
                return {"success": False, "status": "NOT_FOUND", "message": f"Registration '{reg_id_clean}' not found."}

            if reg["status"] != "CONFIRMED":
                return {"success": False, "status": "ALREADY_CANCELLED", "message": f"Registration is already {reg['status']}."}

            cursor.execute("""
                UPDATE registrations 
                SET status = 'CANCELLED' 
                WHERE registration_id = ?
            """, (reg_id_clean,))

            return {
                "success": True,
                "status": "CANCELLED",
                "message": f"Registration '{reg_id_clean}' for '{reg['title']}' was successfully cancelled. Seat released.",
                "event_id": reg["event_id"],
            }
    finally:
        sync_lock.release()


def get_events(db_path: str = database.DATABASE_FILE) -> List[Dict[str, Any]]:
    """Retrieve all workshops with live seat counts."""
    return database.get_all_events(db_path)


def get_event(event_id: str, db_path: str = database.DATABASE_FILE) -> Optional[Dict[str, Any]]:
    """Retrieve details for a single workshop."""
    return database.get_event_by_id(event_id, db_path)


def get_student_registrations(email: str, db_path: str = database.DATABASE_FILE) -> List[Dict[str, Any]]:
    """Retrieve confirmed registrations for a student email."""
    return database.get_registrations_by_email(email, db_path)


def get_dashboard_kpis(db_path: str = database.DATABASE_FILE) -> Dict[str, int]:
    """Retrieve dynamic dashboard KPI counts."""
    return database.get_kpis(db_path)
