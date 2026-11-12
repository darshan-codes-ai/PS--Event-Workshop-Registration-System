"""
Registration Engine - Mutex-Protected Event Registration Logic
Operating Systems Demonstration: Shared Data & Mutual Exclusion Synchronization

This module implements both:
1. In-Memory `EventStore`: Laboratory benchmark for concurrent thread simulation,
   fine-grained vs global locks, race condition reproduction, and invariant verification.
2. `PersistentRegistrationService`: Production-grade ACID-backed registration,
   FIFO waitlist promotion, per-event mutual exclusion, and digital ticket issuance.

Worker threads append results to thread-safe collections and NEVER call Streamlit functions.
"""

from __future__ import annotations

import copy
import datetime
import html
import secrets
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import database
import ticket_service


class EventStore:
    """
    Central repository for the in-memory concurrency laboratory.
    Supports both Global Mutex and Fine-Grained Per-Event Locking.
    """

    DEFAULT_EVENTS = {
        "E1": {
            "id": "E1",
            "name": "Python Concurrency Workshop",
            "date": "2026-11-15",
            "venue": "Turing Lab 301",
            "capacity": 2,
            "remaining_places": 2,
        },
        "E2": {
            "id": "E2",
            "name": "Distributed Systems Seminar",
            "date": "2026-11-22",
            "venue": "Lovelace Auditorium",
            "capacity": 5,
            "remaining_places": 5,
        },
        "E3": {
            "id": "E3",
            "name": "Operating Systems Masterclass",
            "date": "2026-12-05",
            "venue": "Von Neumann Hall",
            "capacity": 10,
            "remaining_places": 10,
        },
    }

    def __init__(self, initial_events: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """Initialize the in-memory store and synchronization locks."""
        self.events: Dict[str, Dict[str, Any]] = {}
        self.registrations: Dict[str, Set[str]] = {}

        # 1. Global Mutex Lock (for classical OS benchmark)
        self.lock = threading.Lock()

        # 2. Fine-Grained Per-Event Lock Registry (for advanced concurrency)
        self.locks_mutex = threading.Lock()
        self.event_locks: Dict[str, threading.Lock] = {}

        # 3. Thread-safe Audit Log Lock
        self.log_lock = threading.Lock()
        self.audit_log: List[Dict[str, Any]] = []

        self.reset(initial_events)

    def get_event_lock(self, event_id: str) -> threading.Lock:
        """Retrieve or lazily instantiate a dedicated mutex for an event in a thread-safe manner."""
        with self.locks_mutex:
            if event_id not in self.event_locks:
                self.event_locks[event_id] = threading.Lock()
            return self.event_locks[event_id]

    def reset(self, initial_events: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """Restore initial event capacities and reset registrations."""
        with self.lock:
            with self.log_lock:
                source = initial_events if initial_events is not None else self.DEFAULT_EVENTS
                self.events = copy.deepcopy(source)
                self.registrations = {eid: set() for eid in self.events}
                for eid, data in self.events.items():
                    data.setdefault("id", eid)
                    data.setdefault("name", f"Workshop {eid}")
                    data.setdefault("date", "2026-11-20")
                    data.setdefault("venue", "Lab 101")
                    data.setdefault("capacity", 5)
                    data.setdefault("remaining_places", data.get("capacity", 5))

                with self.locks_mutex:
                    self.event_locks = {eid: threading.Lock() for eid in self.events}

    def clone(self) -> EventStore:
        """Create an independent deep copy of the store for isolated simulations."""
        with self.lock:
            new_store = EventStore(self.events)
            for eid, users in self.registrations.items():
                new_store.registrations[eid] = set(users)
            return new_store

    def register(
        self,
        user: str,
        event_id: str,
        use_lock: bool = True,
        delay: float = 0.3,
        simulate_exception: bool = False,
        use_fine_grained: bool = False,
    ) -> Dict[str, Any]:
        """
        In-memory registration simulation.
        Can use Global Mutex (use_fine_grained=False) or Per-Event Mutex (use_fine_grained=True).
        """
        thread_name = threading.current_thread().name
        req_time = time.perf_counter()
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

        waited_ms = 0.0
        held_ms = 0.0

        if event_id not in self.events:
            return {
                "user": user,
                "event_id": event_id,
                "status": "ERROR",
                "message": f"Event '{event_id}' not found.",
                "timestamp": timestamp_str,
                "thread_name": thread_name,
                "waited_ms": 0.0,
                "held_ms": 0.0,
                "req_time": req_time,
                "cs_entry_time": req_time,
                "cs_exit_time": req_time,
                "remaining_after": 0,
            }

        # Select synchronization lock primitive
        target_lock = self.get_event_lock(event_id) if use_fine_grained else self.lock

        if use_lock:
            wait_start = time.perf_counter()
            target_lock.acquire()
            waited_ms = (time.perf_counter() - wait_start) * 1000.0

        cs_entry_time = time.perf_counter()

        try:
            # ==================== CRITICAL SECTION START ====================
            event = self.events[event_id]
            user_clean = user.strip()

            if simulate_exception:
                raise RuntimeError("Simulated crash inside critical section")

            # 1. Duplicate check
            if user_clean in self.registrations[event_id]:
                status = "DUPLICATE"
                message = f"User '{user_clean}' is already registered for {event['name']}."
            # 2. Capacity check
            elif event["remaining_places"] > 0:
                # 3. Simulated processing delay (exposes race condition if unprotected)
                if delay > 0:
                    time.sleep(delay)

                # 4. State update: Decrement capacity and add attendee
                event["remaining_places"] -= 1
                self.registrations[event_id].add(user_clean)
                status = "CONFIRMED"
                message = f"Registration CONFIRMED for {user_clean} ({event['name']})."
            else:
                status = "FULL"
                message = f"Workshop '{event['name']}' is FULL. No places remaining."

            remaining_after = event["remaining_places"]
            # ===================== CRITICAL SECTION END =====================

        finally:
            cs_exit_time = time.perf_counter()
            held_ms = (cs_exit_time - cs_entry_time) * 1000.0
            if use_lock:
                target_lock.release()

        result = {
            "user": user,
            "event_id": event_id,
            "status": status,
            "message": message,
            "timestamp": timestamp_str,
            "thread_name": thread_name,
            "waited_ms": round(waited_ms, 2),
            "held_ms": round(held_ms, 2),
            "req_time": req_time,
            "cs_entry_time": cs_entry_time,
            "cs_exit_time": cs_exit_time,
            "remaining_after": remaining_after,
            "use_lock": use_lock,
            "use_fine_grained": use_fine_grained,
        }

        self._record_log({
            "timestamp": timestamp_str,
            "thread": thread_name,
            "action": "REGISTER",
            "user": user,
            "event_id": event_id,
            "status": status,
            "use_lock": use_lock,
            "waited_ms": round(waited_ms, 2),
            "held_ms": round(held_ms, 2),
            "remaining_after": remaining_after,
            "message": message,
        })

        return result

    def cancel(self, user: str, event_id: str, use_lock: bool = True, use_fine_grained: bool = False) -> Dict[str, Any]:
        """Cancel a registration and restore remaining places."""
        thread_name = threading.current_thread().name
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        waited_ms = 0.0

        if event_id not in self.events:
            return {
                "user": user,
                "event_id": event_id,
                "status": "ERROR",
                "message": f"Event '{event_id}' not found.",
                "timestamp": timestamp_str,
                "remaining_after": 0,
            }

        target_lock = self.get_event_lock(event_id) if use_fine_grained else self.lock

        if use_lock:
            wait_start = time.perf_counter()
            target_lock.acquire()
            waited_ms = (time.perf_counter() - wait_start) * 1000.0

        try:
            event = self.events[event_id]
            user_clean = user.strip()

            if user_clean in self.registrations[event_id]:
                self.registrations[event_id].remove(user_clean)
                event["remaining_places"] = min(event["capacity"], event["remaining_places"] + 1)
                status = "CANCELLED"
                message = f"Registration for '{user_clean}' cancelled. 1 place released."
            else:
                status = "NOT_REGISTERED"
                message = f"User '{user_clean}' is not registered for {event['name']}."

            remaining_after = event["remaining_places"]
        finally:
            if use_lock:
                target_lock.release()

        result = {
            "user": user,
            "event_id": event_id,
            "status": status,
            "message": message,
            "timestamp": timestamp_str,
            "thread_name": thread_name,
            "waited_ms": round(waited_ms, 2),
            "remaining_after": remaining_after,
            "use_lock": use_lock,
        }

        self._record_log({
            "timestamp": timestamp_str,
            "thread": thread_name,
            "action": "CANCEL",
            "user": user,
            "event_id": event_id,
            "status": status,
            "use_lock": use_lock,
            "waited_ms": round(waited_ms, 2),
            "held_ms": 0.0,
            "remaining_after": remaining_after,
            "message": message,
        })

        return result

    def validate_state(self, event_id: Optional[str] = None) -> List[str]:
        """Validate in-memory OS invariants."""
        violations: List[str] = []
        target_ids = [event_id] if event_id is not None else list(self.events.keys())

        for eid in target_ids:
            if eid not in self.events:
                violations.append(f"Invalid event reference: {eid}")
                continue

            event = self.events[eid]
            cap = event["capacity"]
            rem = event["remaining_places"]
            regs = self.registrations.get(eid, set())
            confirmed_count = len(regs)

            if rem < 0:
                violations.append(f"Invariant 1 VIOLATION [Event {eid}]: Remaining capacity is negative ({rem} < 0).")
            if rem > cap:
                violations.append(f"Invariant 2 VIOLATION [Event {eid}]: Remaining places ({rem}) exceeds capacity ({cap}).")
            if cap - rem != confirmed_count:
                violations.append(f"Invariant 3 VIOLATION [Event {eid}]: Capacity ({cap}) - Remaining ({rem}) != Confirmed ({confirmed_count}).")
            if confirmed_count > cap:
                violations.append(f"OVERBOOKING VIOLATION [Event {eid}]: {confirmed_count} confirmed for capacity {cap}!")

        return violations

    def _record_log(self, entry: Dict[str, Any]) -> None:
        with self.log_lock:
            self.audit_log.append(entry)

    def get_audit_log(self) -> List[Dict[str, Any]]:
        with self.log_lock:
            return list(self.audit_log)

    def clear_audit_log(self) -> None:
        with self.log_lock:
            self.audit_log.clear()

    def get_event_summary(self, event_id: str) -> Dict[str, Any]:
        event = self.events[event_id]
        regs = self.registrations.get(event_id, set())
        return {
            "id": event.get("id", event_id),
            "name": event.get("name", f"Event {event_id}"),
            "date": event.get("date", "N/A"),
            "venue": event.get("venue", "N/A"),
            "capacity": event.get("capacity", 0),
            "remaining_places": event.get("remaining_places", 0),
            "confirmed_count": len(regs),
            "registered_users": sorted(list(regs)),
            "is_full": event.get("remaining_places", 0) <= 0,
        }


# =============================================================================
# PERSISTENT REGISTRATION SERVICE (SQLite ACID + Fine-Grained Locks)
# =============================================================================
class PersistentRegistrationService:
    """
    Production-grade registration service backed by SQLite and per-event mutexes.
    Guarantees:
    - Thread-safe check-and-update via fine-grained per-event locks
    - Atomic database updates via immediate transactions
    - Automatic FIFO waitlist queueing when full
    - Automatic waitlist promotion when confirmed seats are cancelled
    - Unique QR ticket token generation
    """

    _instance = None
    _service_lock = threading.Lock()

    def __init__(self, db_path: str = database.DATABASE_FILE) -> None:
        self.db_path = db_path
        self.event_locks: Dict[str, threading.Lock] = {}
        self.locks_guard = threading.Lock()

    @classmethod
    def get_instance(cls) -> PersistentRegistrationService:
        """Singleton accessor for shared cross-session application service."""
        with cls._service_lock:
            if cls._instance is None:
                cls._instance = PersistentRegistrationService()
            return cls._instance

    def get_event_lock(self, event_id: str) -> threading.Lock:
        with self.locks_guard:
            if event_id not in self.event_locks:
                self.event_locks[event_id] = threading.Lock()
            return self.event_locks[event_id]

    def register(self, user_id: str, event_id: str) -> Dict[str, Any]:
        """
        Register a student for a workshop or place on waitlist if full.
        Protected by event-specific mutex lock and SQLite atomic transaction.
        """
        user_clean = user_id.strip()
        event_clean = event_id.strip()

        if not user_clean:
            return {"status": "ERROR", "message": "User identifier cannot be empty."}

        event_lock = self.get_event_lock(event_clean)

        with event_lock:
            with database.get_db_cursor(self.db_path) as cursor:
                # 1. Fetch Event Record
                cursor.execute("SELECT id, title, capacity, status FROM events WHERE id = ?", (event_clean,))
                event = cursor.fetchone()
                if not event:
                    return {"status": "ERROR", "message": f"Workshop '{event_clean}' not found."}

                if event["status"] != "Published":
                    return {"status": "ERROR", "message": f"Registrations closed. Event status is '{event['status']}'."}

                # 2. Check for existing active registration
                cursor.execute("""
                    SELECT status, ticket_id FROM registrations 
                    WHERE event_id = ? AND user_id = ? AND status IN ('CONFIRMED', 'WAITLISTED', 'ATTENDED')
                """, (event_clean, user_clean))
                existing = cursor.fetchone()
                if existing:
                    status = existing["status"]
                    return {
                        "status": "DUPLICATE",
                        "message": f"User '{user_clean}' already has active status '{status}' for this event.",
                        "ticket_id": existing["ticket_id"],
                    }

                # 3. Check current confirmed capacity
                cursor.execute("""
                    SELECT COUNT(*) AS confirmed_count 
                    FROM registrations 
                    WHERE event_id = ? AND status IN ('CONFIRMED', 'ATTENDED')
                """, (event_clean,))
                confirmed_count = cursor.fetchone()["confirmed_count"]
                capacity = event["capacity"]

                reg_id = f"REG-{secrets.token_hex(6).upper()}"
                now_str = datetime.datetime.now().isoformat()

                # 4. Seat Allocation or Waitlist Promotion
                if confirmed_count < capacity:
                    # Allocate Seat & Generate QR Ticket
                    ticket_id = ticket_service.generate_ticket_token(event_clean, user_clean, reg_id)
                    cursor.execute("""
                        INSERT INTO registrations (id, event_id, user_id, status, ticket_id, registered_at)
                        VALUES (?, ?, ?, 'CONFIRMED', ?, ?)
                    """, (reg_id, event_clean, user_clean, ticket_id, now_str))

                    cursor.execute("""
                        INSERT INTO audit_logs (actor_id, event_id, action, status, details, created_at)
                        VALUES (?, ?, 'REGISTER', 'CONFIRMED', ?, ?)
                    """, (user_clean, event_clean, f"Confirmed seat for {user_clean}. Ticket {ticket_id}", now_str))

                    return {
                        "status": "CONFIRMED",
                        "message": f"Registration CONFIRMED for {user_clean} ({event['title']}).",
                        "ticket_id": ticket_id,
                        "registration_id": reg_id,
                        "remaining_places": max(0, capacity - confirmed_count - 1),
                    }
                else:
                    # Event is Full -> Join FIFO Waitlist
                    cursor.execute("""
                        SELECT COALESCE(MAX(queue_position), 0) + 1 AS next_pos 
                        FROM waitlist 
                        WHERE event_id = ? AND status = 'WAITING'
                    """, (event_clean,))
                    next_pos = cursor.fetchone()["next_pos"]
                    wait_id = f"WAIT-{secrets.token_hex(6).upper()}"

                    cursor.execute("""
                        INSERT INTO waitlist (id, event_id, user_id, queue_position, status, joined_at)
                        VALUES (?, ?, ?, ?, 'WAITING', ?)
                    """, (wait_id, event_clean, user_clean, next_pos, now_str))

                    cursor.execute("""
                        INSERT INTO registrations (id, event_id, user_id, status, registered_at)
                        VALUES (?, ?, ?, 'WAITLISTED', ?)
                    """, (reg_id, event_clean, user_clean, now_str))

                    cursor.execute("""
                        INSERT INTO audit_logs (actor_id, event_id, action, status, details, created_at)
                        VALUES (?, ?, 'WAITLIST', 'QUEUED', ?, ?)
                    """, (user_clean, event_clean, f"User {user_clean} placed in waitlist position #{next_pos}", now_str))

                    return {
                        "status": "WAITLISTED",
                        "message": f"Workshop is FULL. User '{user_clean}' joined the FIFO waitlist at position #{next_pos}.",
                        "queue_position": next_pos,
                        "registration_id": reg_id,
                        "remaining_places": 0,
                    }

    def cancel(self, user_id: str, event_id: str) -> Dict[str, Any]:
        """
        Cancel a registration.
        If a confirmed seat is freed and waitlisted students exist,
        automatically promotes the earliest eligible student (FIFO order).
        """
        user_clean = user_id.strip()
        event_clean = event_id.strip()
        now_str = datetime.datetime.now().isoformat()

        event_lock = self.get_event_lock(event_clean)

        with event_lock:
            with database.get_db_cursor(self.db_path) as cursor:
                # 1. Find active registration
                cursor.execute("""
                    SELECT id, status, ticket_id FROM registrations 
                    WHERE event_id = ? AND user_id = ? AND status IN ('CONFIRMED', 'WAITLISTED')
                """, (event_clean, user_clean))
                reg = cursor.fetchone()

                if not reg:
                    return {"status": "NOT_REGISTERED", "message": f"No active registration found for '{user_clean}'."}

                reg_id = reg["id"]
                prev_status = reg["status"]

                # 2. Cancel current registration
                cursor.execute("""
                    UPDATE registrations 
                    SET status = 'CANCELLED', cancelled_at = ? 
                    WHERE id = ?
                """, (now_str, reg_id))

                promoted_user = None

                # 3. If a confirmed seat was freed, check FIFO waitlist for promotion
                if prev_status == "CONFIRMED":
                    cursor.execute("""
                        SELECT id, user_id FROM waitlist 
                        WHERE event_id = ? AND status = 'WAITING' 
                        ORDER BY queue_position ASC LIMIT 1
                    """, (event_clean,))
                    next_wait = cursor.fetchone()

                    if next_wait:
                        promoted_uid = next_wait["user_id"]
                        waitlist_id = next_wait["id"]

                        # Promote waitlisted user
                        promoted_ticket = ticket_service.generate_ticket_token(event_clean, promoted_uid, waitlist_id)

                        cursor.execute("""
                            UPDATE registrations 
                            SET status = 'CONFIRMED', ticket_id = ? 
                            WHERE event_id = ? AND user_id = ? AND status = 'WAITLISTED'
                        """, (promoted_ticket, event_clean, promoted_uid))

                        cursor.execute("""
                            UPDATE waitlist 
                            SET status = 'PROMOTED' 
                            WHERE id = ?
                        """, (waitlist_id,))

                        promoted_user = promoted_uid

                        cursor.execute("""
                            INSERT INTO audit_logs (actor_id, event_id, action, status, details, created_at)
                            VALUES (?, ?, 'WAITLIST_PROMOTION', 'SUCCESS', ?, ?)
                        """, (promoted_uid, event_clean, f"Promoted waitlisted user {promoted_uid} to CONFIRMED. Ticket {promoted_ticket}", now_str))

                cursor.execute("""
                    INSERT INTO audit_logs (actor_id, event_id, action, status, details, created_at)
                    VALUES (?, ?, 'CANCEL', 'SUCCESS', ?, ?)
                """, (user_clean, event_clean, f"Cancelled registration for {user_clean}. Promoted: {promoted_user}", now_str))

                msg = f"Registration for '{user_clean}' successfully cancelled."
                if promoted_user:
                    msg += f" FIFO Waitlist: Promoted '{promoted_user}' to confirmed seat!"

                return {
                    "status": "CANCELLED",
                    "message": msg,
                    "promoted_user": promoted_user,
                }

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Fetch event metadata, confirmed count, remaining seats, and waitlist count."""
        conn = database.get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        ev = cursor.fetchone()
        if not ev:
            return None

        event_data = dict(ev)

        cursor.execute("""
            SELECT COUNT(*) AS confirmed_count 
            FROM registrations 
            WHERE event_id = ? AND status IN ('CONFIRMED', 'ATTENDED')
        """, (event_id,))
        confirmed = cursor.fetchone()["confirmed_count"]

        cursor.execute("""
            SELECT COUNT(*) AS wait_count 
            FROM waitlist 
            WHERE event_id = ? AND status = 'WAITING'
        """, (event_id,))
        wait_count = cursor.fetchone()["wait_count"]

        event_data["confirmed_count"] = confirmed
        event_data["remaining_places"] = max(0, event_data["capacity"] - confirmed)
        event_data["waitlist_count"] = wait_count
        event_data["is_full"] = event_data["remaining_places"] <= 0
        return event_data

    def list_events(
        self,
        category: Optional[str] = None,
        venue: Optional[str] = None,
        status: Optional[str] = "Published",
        search_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query and filter events with live capacity telemetry."""
        conn = database.get_connection(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM events WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        if venue and venue != "All":
            query += " AND venue = ?"
            params.append(venue)
        if search_query:
            query += " AND (title LIKE ? OR description LIKE ?)"
            term = f"%{search_query.strip()}%"
            params.extend([term, term])

        query += " ORDER BY start_datetime ASC"
        cursor.execute(query, params)
        raw_events = [dict(r) for r in cursor.fetchall()]

        # Attach real-time occupancy counts
        for ev in raw_events:
            eid = ev["id"]
            cursor.execute("""
                SELECT COUNT(*) AS confirmed_count 
                FROM registrations 
                WHERE event_id = ? AND status IN ('CONFIRMED', 'ATTENDED')
            """, (eid,))
            conf = cursor.fetchone()["confirmed_count"]
            ev["confirmed_count"] = conf
            ev["remaining_places"] = max(0, ev["capacity"] - conf)
            ev["is_full"] = ev["remaining_places"] <= 0

        return raw_events

    def get_user_registrations(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch all registrations (confirmed, waitlisted, attended) for a student."""
        conn = database.get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                r.id AS registration_id,
                r.event_id,
                r.status AS registration_status,
                r.ticket_id,
                r.registered_at,
                e.title AS event_title,
                e.venue,
                e.start_datetime,
                w.queue_position
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            LEFT JOIN waitlist w ON r.event_id = w.event_id AND r.user_id = w.user_id AND w.status = 'WAITING'
            WHERE r.user_id = ?
            ORDER BY r.registered_at DESC
        """, (user_id.strip(),))
        return [dict(r) for r in cursor.fetchall()]

    def create_event(
        self,
        event_id: str,
        title: str,
        description: str,
        category: str,
        venue: str,
        start_datetime: str,
        end_datetime: str,
        capacity: int,
        organizer_id: str,
    ) -> Tuple[bool, str]:
        """Create a new event with input validation."""
        clean_id = event_id.strip().upper()
        clean_title = title.strip()
        clean_venue = venue.strip()

        if not clean_id or not clean_title or not clean_venue:
            return False, "Event ID, Title, and Venue are required."
        if capacity < 0:
            return False, "Capacity must be non-negative."
        if end_datetime <= start_datetime:
            return False, "End date/time must be after start date/time."

        now_str = datetime.datetime.now().isoformat()
        with database.get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT id FROM events WHERE id = ?", (clean_id,))
            if cursor.fetchone():
                return False, f"Event ID '{clean_id}' already exists."

            cursor.execute("""
                INSERT INTO events (id, title, description, category, venue, start_datetime, end_datetime, capacity, status, organizer_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Published', ?, ?, ?)
            """, (clean_id, clean_title, description.strip(), category, clean_venue, start_datetime, end_datetime, capacity, organizer_id, now_str, now_str))

            cursor.execute("""
                INSERT INTO audit_logs (actor_id, event_id, action, status, details, created_at)
                VALUES (?, ?, 'CREATE_EVENT', 'SUCCESS', ?, ?)
            """, (organizer_id, clean_id, f"Created workshop '{clean_title}' with capacity {capacity}", now_str))

        return True, f"Workshop '{clean_title}' ({clean_id}) created successfully!"
