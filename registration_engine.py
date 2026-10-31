"""
Registration Engine - Mutex-Protected Event Registration Logic
Operating Systems Demonstration: Shared Data & Mutual Exclusion Synchronization

This module implements the core data structures and operations for an event
workshop registration system. It demonstrates the critical difference between
unprotected concurrent access (race condition) and mutex synchronization
(threading.Lock with try/finally).

Worker threads append results to thread-safe structures and NEVER call any
Streamlit (st.*) functions directly.
"""

from __future__ import annotations

import copy
import datetime
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class EventStore:
    """
    Central thread-safe repository managing workshops, capacities,
    registrations, and the shared mutex lock.
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
        """
        Initialize the EventStore with event records and thread synchronization primitives.
        """
        # Shared business data
        self.events: Dict[str, Dict[str, Any]] = {}
        # Mapping: event_id -> set of user identifiers (strings)
        self.registrations: Dict[str, Set[str]] = {}

        # Primary Synchronization Mutex (threading.Lock)
        # Protects the check-and-update critical section
        self.lock = threading.Lock()

        # Secondary lock dedicated strictly to the audit log to ensure thread safety
        # without affecting the primary mutex demonstration
        self.log_lock = threading.Lock()
        self.audit_log: List[Dict[str, Any]] = []

        # Load initial records
        self.reset(initial_events)

    def reset(self, initial_events: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """
        Restore the initial event capacities and clear all registrations.
        """
        with self.lock:
            with self.log_lock:
                source = initial_events if initial_events is not None else self.DEFAULT_EVENTS
                self.events = copy.deepcopy(source)
                self.registrations = {eid: set() for eid in self.events}
                # Ensure all required keys exist with sensible defaults
                for eid, data in self.events.items():
                    data.setdefault("id", eid)
                    data.setdefault("name", f"Workshop {eid}")
                    data.setdefault("date", "2026-11-20")
                    data.setdefault("venue", "Lab 101")
                    data.setdefault("capacity", 5)
                    data.setdefault("remaining_places", data.get("capacity", 5))

    def clone(self) -> EventStore:
        """
        Create an independent, deep-copied instance of the EventStore for isolated simulations.
        """
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
    ) -> Dict[str, Any]:
        """
        Attempt to register a user for a workshop.

        Critical Section Order:
        1. Duplicate check (user in registrations[event_id])
        2. Capacity check (remaining_places > 0)
        3. Simulated processing delay (widens race window if unprotected)
        4. Decrement remaining_places & add user to registrations

        Parameters:
        - user: Unique identifier of the user (e.g., 'S1')
        - event_id: ID of the event (e.g., 'E1')
        - use_lock: True for safe mode (Mutex ON), False for unsafe mode (Mutex OFF)
        - delay: Artificial processing delay (seconds) to expose race conditions
        - simulate_exception: If True, raises a deliberate RuntimeError during the
                              critical section to verify try/finally release.

        Returns:
        - Result dictionary containing status, timings, and metadata.
        """
        thread_name = threading.current_thread().name
        req_time = time.perf_counter()
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

        waited_ms = 0.0
        held_ms = 0.0
        cs_entry_time = 0.0
        cs_exit_time = 0.0

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

        # --- MUTEX ACQUISITION (IF ENABLED) ---
        if use_lock:
            wait_start = time.perf_counter()
            self.lock.acquire()
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
                # 3. Teaching delay: Exposes race condition when concurrency is uncoordinated
                if delay > 0:
                    time.sleep(delay)

                # 4. State update: Decrement capacity and record registration
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
            # --- MUTEX RELEASE (ALWAYS GUARANTEED BY FINALLY) ---
            if use_lock:
                self.lock.release()

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
        }

        # Log operation safely
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

    def cancel(self, user: str, event_id: str, use_lock: bool = True) -> Dict[str, Any]:
        """
        Cancel a user's registration and restore remaining capacity.

        Parameters:
        - user: Unique identifier of the user
        - event_id: ID of the event
        - use_lock: True to protect state update with mutex

        Returns:
        - Result dictionary detailing cancellation status.
        """
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

        if use_lock:
            wait_start = time.perf_counter()
            self.lock.acquire()
            waited_ms = (time.perf_counter() - wait_start) * 1000.0

        try:
            event = self.events[event_id]
            user_clean = user.strip()

            if user_clean in self.registrations[event_id]:
                self.registrations[event_id].remove(user_clean)
                # Ensure remaining_places never exceeds max capacity
                event["remaining_places"] = min(event["capacity"], event["remaining_places"] + 1)
                status = "CANCELLED"
                message = f"Registration for '{user_clean}' cancelled. 1 place released."
            else:
                status = "NOT_REGISTERED"
                message = f"User '{user_clean}' is not registered for {event['name']}."

            remaining_after = event["remaining_places"]
        finally:
            if use_lock:
                self.lock.release()

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
        """
        Validate Operating System invariants for shared data:
        1. remaining_places >= 0 (no negative places)
        2. remaining_places <= capacity (cannot exceed maximum)
        3. capacity - remaining_places == len(registrations) (arithmetic consistency)
        4. No duplicate entries in registrations

        Returns:
        - List of error strings describing invariant violations. Empty list means consistent.
        """
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

            # Invariant 1: Non-negative remaining capacity
            if rem < 0:
                violations.append(
                    f"Invariant 1 VIOLATION [Event {eid}]: Remaining places is negative ({rem} < 0). Race condition detected!"
                )

            # Invariant 2: Remaining places cannot exceed total capacity
            if rem > cap:
                violations.append(
                    f"Invariant 2 VIOLATION [Event {eid}]: Remaining places ({rem}) exceeds capacity ({cap})."
                )

            # Invariant 3: Arithmetic consistency (capacity - remaining == confirmed count)
            if cap - rem != confirmed_count:
                violations.append(
                    f"Invariant 3 VIOLATION [Event {eid}]: State mismatch! "
                    f"Capacity ({cap}) - Remaining ({rem}) = {cap - rem}, but confirmed registrations = {confirmed_count}."
                )

            # Overbooking check directly against capacity
            if confirmed_count > cap:
                violations.append(
                    f"OVERBOOKING VIOLATION [Event {eid}]: {confirmed_count} users confirmed for a capacity of only {cap}!"
                )

        return violations

    def _record_log(self, entry: Dict[str, Any]) -> None:
        """Append an entry to the audit log in a thread-safe manner."""
        with self.log_lock:
            self.audit_log.append(entry)

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return a snapshot of the audit log."""
        with self.log_lock:
            return list(self.audit_log)

    def clear_audit_log(self) -> None:
        """Clear all audit log entries."""
        with self.log_lock:
            self.audit_log.clear()

    def get_event_summary(self, event_id: str) -> Dict[str, Any]:
        """Return a dictionary summary of an event's state."""
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
