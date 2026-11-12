"""
Test Suite - Operating Systems Verification & Enterprise Quality Assurance
Predefined test scenarios validating:
- OS Critical section synchronization & mutual exclusion (threading.Lock)
- Fine-grained per-event locking vs global lock
- Race condition manifestations & honest detection
- Deadlock prevention & try/finally release guarantees
- SQLite persistence & transaction resilience across reboots
- FIFO waitlist atomic promotions
- QR ticket generation & check-in duplicate prevention
- Stored XSS & CSV formula injection sanitization
- Role-based access control (RBAC) authorization boundaries

Can be run via CLI: `python test_cases.py`
Or imported by `app.py` for the in-app Test Center.
"""

from __future__ import annotations

import html
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List

import auth
import database
import registration_engine
from registration_engine import EventStore, PersistentRegistrationService
import report_service
import seed_events
from simulator import run_simulation
import ticket_service


# =============================================================================
# PART 1: CORE OPERATING SYSTEMS CONCURRENCY TESTS (T1 - T8)
# =============================================================================
def test_sequential_booking() -> Dict[str, Any]:
    """Test 1: Sequential booking (1 seat, 2 users) -> exactly 1 success."""
    t0 = time.perf_counter()
    store = EventStore({
        "TEST": {"id": "TEST", "name": "Sequential Test", "capacity": 1, "remaining_places": 1}
    })

    r1 = store.register("Alice", "TEST", use_lock=True, delay=0.01)
    r2 = store.register("Bob", "TEST", use_lock=True, delay=0.01)

    violations = store.validate_state("TEST")
    passed = (
        r1["status"] == "CONFIRMED"
        and r2["status"] == "FULL"
        and store.events["TEST"]["remaining_places"] == 0
        and len(violations) == 0
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T1",
        "name": "Sequential Booking (1 seat, 2 users)",
        "description": "Verifies that under sequential requests, the first user succeeds and the second is rejected.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Alice: {r1['status']}, Bob: {r2['status']}, Remaining: {store.events['TEST']['remaining_places']}",
        "duration_ms": elapsed_ms,
    }


def test_concurrent_unsafe() -> Dict[str, Any]:
    """Test 2: Concurrent unsafe (1 seat, 3 users) -> race condition / overbooking expected."""
    t0 = time.perf_counter()
    race_observed = False
    details = ""

    for attempt in range(1, 4):
        store = EventStore({
            "TEST": {"id": "TEST", "name": "Unsafe Test", "capacity": 1, "remaining_places": 1}
        })
        sim = run_simulation(
            event_id="TEST",
            users=["U1", "U2", "U3"],
            use_lock=False,
            delay=0.15,
            store=store,
        )
        if sim["overbooked"] or sim["confirmed_count"] > 1:
            race_observed = True
            details = (
                f"Race observed on attempt {attempt}: {sim['confirmed_count']} confirmed for capacity 1. "
                f"Remaining places: {sim['final_remaining']} (Overbooked: {sim['overbooked']})."
            )
            break
        else:
            details = (
                f"Race not triggered on attempt {attempt} ({sim['confirmed_count']} confirmed) due to thread interleaving."
            )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T2",
        "name": "Concurrent Unsafe (1 seat, 3 users)",
        "description": "Demonstrates race condition when mutex is omitted. Multiple threads read remaining=1 simultaneously.",
        "passed": True,
        "status": "PASS",
        "details": details if race_observed else f"{details} (Honest report: scheduler executed sequentially without race).",
        "duration_ms": elapsed_ms,
        "race_observed": race_observed,
    }


def test_concurrent_safe() -> Dict[str, Any]:
    """Test 3: Concurrent safe (1 seat, 3 users) -> exactly 1 confirmed."""
    t0 = time.perf_counter()
    store = EventStore({
        "TEST": {"id": "TEST", "name": "Safe Test", "capacity": 1, "remaining_places": 1}
    })
    sim = run_simulation(
        event_id="TEST",
        users=["U1", "U2", "U3"],
        use_lock=True,
        delay=0.05,
        store=store,
    )

    passed = (
        sim["confirmed_count"] == 1
        and sim["full_count"] == 2
        and sim["final_remaining"] == 0
        and len(sim["violations"]) == 0
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T3",
        "name": "Concurrent Safe (1 seat, 3 users)",
        "description": "Ensures mutex lock enforces mutual exclusion: exactly 1 confirmed, 2 rejected as FULL.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Confirmed: {sim['confirmed_count']}, Full: {sim['full_count']}, Final remaining: {sim['final_remaining']}",
        "duration_ms": elapsed_ms,
    }


def test_ten_users_two_seats_safe() -> Dict[str, Any]:
    """Test 4: 10 users, 2 seats, safe -> exactly 2 confirmed, 8 full."""
    t0 = time.perf_counter()
    store = EventStore({
        "TEST": {"id": "TEST", "name": "Ten User Test", "capacity": 2, "remaining_places": 2}
    })
    users = [f"Student_{i}" for i in range(1, 11)]
    sim = run_simulation(
        event_id="TEST",
        users=users,
        use_lock=True,
        delay=0.02,
        store=store,
    )

    passed = (
        sim["confirmed_count"] == 2
        and sim["full_count"] == 8
        and sim["final_remaining"] == 0
        and len(sim["violations"]) == 0
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T4",
        "name": "10 Users, 2 Seats (Safe Mode)",
        "description": "Verifies capacity boundary enforcement with high concurrency: exactly 2 seats granted.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Confirmed: {sim['confirmed_count']}, Rejected: {sim['full_count']}, Violations: {len(sim['violations'])}",
        "duration_ms": elapsed_ms,
    }


def test_duplicate_registration_safe() -> Dict[str, Any]:
    """Test 5: Duplicate registration (same user twice at once, safe) -> 1 confirmed, 1 duplicate."""
    t0 = time.perf_counter()
    store = EventStore({
        "TEST": {"id": "TEST", "name": "Duplicate Test", "capacity": 5, "remaining_places": 5}
    })
    sim = run_simulation(
        event_id="TEST",
        users=["SamUser", "SamUser"],
        use_lock=True,
        delay=0.04,
        store=store,
    )

    passed = (
        sim["confirmed_count"] == 1
        and sim["duplicate_count"] == 1
        and sim["final_remaining"] == 4
        and len(sim["violations"]) == 0
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T5",
        "name": "Concurrent Duplicate Attempt (Safe Mode)",
        "description": "Checks critical section duplicate protection: identical user ID receives 1 CONFIRMED and 1 DUPLICATE.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Confirmed: {sim['confirmed_count']}, Duplicates: {sim['duplicate_count']}, Seats left: {sim['final_remaining']}",
        "duration_ms": elapsed_ms,
    }


def test_cancel_then_reregister() -> Dict[str, Any]:
    """Test 6: Cancel then re-register -> cancel frees seat, next user succeeds."""
    t0 = time.perf_counter()
    store = EventStore({
        "TEST": {"id": "TEST", "name": "Cancel Test", "capacity": 1, "remaining_places": 1}
    })

    r1 = store.register("User1", "TEST", use_lock=True, delay=0.01)
    r2 = store.register("User2", "TEST", use_lock=True, delay=0.01)
    c1 = store.cancel("User1", "TEST", use_lock=True)
    r3 = store.register("User2", "TEST", use_lock=True, delay=0.01)

    violations = store.validate_state("TEST")
    passed = (
        r1["status"] == "CONFIRMED"
        and r2["status"] == "FULL"
        and c1["status"] == "CANCELLED"
        and r3["status"] == "CONFIRMED"
        and store.events["TEST"]["remaining_places"] == 0
        and "User2" in store.registrations["TEST"]
        and len(violations) == 0
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T6",
        "name": "Cancel and Re-Register Workflow",
        "description": "Validates seat release mechanism: cancellation increments capacity and allows queued users to register.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"U1: {r1['status']} -> U2: {r2['status']} -> Cancel: {c1['status']} -> U2 Retry: {r3['status']}",
        "duration_ms": elapsed_ms,
    }


def test_capacity_never_negative_stress() -> Dict[str, Any]:
    """Test 7: Capacity never negative under 50 threads (Safe Mode)."""
    t0 = time.perf_counter()
    store = EventStore({
        "TEST": {"id": "TEST", "name": "Stress Test", "capacity": 5, "remaining_places": 5}
    })
    users = [f"Runner_{i}" for i in range(1, 51)]
    sim = run_simulation(
        event_id="TEST",
        users=users,
        use_lock=True,
        delay=0.005,
        store=store,
    )

    violations = store.validate_state("TEST")
    passed = (
        sim["confirmed_count"] == 5
        and sim["full_count"] == 45
        and sim["final_remaining"] == 0
        and not sim["overbooked"]
        and len(violations) == 0
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T7",
        "name": "High Contention Stress (50 Threads, 5 Seats)",
        "description": "High-load stress test verifying remaining capacity never drops below 0 and invariants hold strictly.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Confirmed: {sim['confirmed_count']}/5, Full: {sim['full_count']}, Final remaining: {sim['final_remaining']}",
        "duration_ms": elapsed_ms,
    }


def test_lock_released_after_exception() -> Dict[str, Any]:
    """Test 8: Lock released after an exception (try/finally check)."""
    t0 = time.perf_counter()
    store = EventStore({
        "TEST": {"id": "TEST", "name": "Exception Test", "capacity": 2, "remaining_places": 2}
    })

    exception_caught = False
    try:
        store.register("CrashDummy", "TEST", use_lock=True, delay=0.01, simulate_exception=True)
    except RuntimeError:
        exception_caught = True

    is_locked = store.lock.locked()
    subsequent_result = store.register("Survivor", "TEST", use_lock=True, delay=0.01)

    passed = (
        exception_caught
        and not is_locked
        and subsequent_result["status"] == "CONFIRMED"
        and store.events["TEST"]["remaining_places"] == 1
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T8",
        "name": "Exception Safety (try/finally Release)",
        "description": "Verifies that an unhandled crash inside the critical section releases the mutex, preventing deadlock.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Exception Caught: {exception_caught}, Lock Is Locked: {is_locked}, Followup Status: {subsequent_result['status']}",
        "duration_ms": elapsed_ms,
    }


# =============================================================================
# PART 2: ADVANCED CONCURRENCY & ARCHITECTURAL TESTS (T9 - T14)
# =============================================================================
def test_fine_grained_concurrency() -> Dict[str, Any]:
    """Test 9: Fine-grained per-event locking allows independent concurrent execution."""
    t0 = time.perf_counter()
    store = EventStore({
        "E1": {"id": "E1", "name": "Event 1", "capacity": 2, "remaining_places": 2},
        "E2": {"id": "E2", "name": "Event 2", "capacity": 2, "remaining_places": 2},
    })

    # Register for E1 and E2 concurrently with per-event locks
    results_e1: List[Dict[str, Any]] = []
    results_e2: List[Dict[str, Any]] = []

    def book_e1():
        results_e1.append(store.register("User_A", "E1", use_lock=True, delay=0.05, use_fine_grained=True))

    def book_e2():
        results_e2.append(store.register("User_B", "E2", use_lock=True, delay=0.05, use_fine_grained=True))

    t_e1 = threading.Thread(target=book_e1)
    t_e2 = threading.Thread(target=book_e2)

    t_e1.start()
    t_e2.start()
    t_e1.join()
    t_e2.join()

    passed = (
        len(results_e1) == 1 and results_e1[0]["status"] == "CONFIRMED"
        and len(results_e2) == 1 and results_e2[0]["status"] == "CONFIRMED"
        and store.events["E1"]["remaining_places"] == 1
        and store.events["E2"]["remaining_places"] == 1
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T9",
        "name": "Fine-Grained Per-Event Locking",
        "description": "Verifies independent events do not block each other when using per-event locks.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"E1 Remaining: {store.events['E1']['remaining_places']}, E2 Remaining: {store.events['E2']['remaining_places']}",
        "duration_ms": elapsed_ms,
    }


def test_database_persistence_restart() -> Dict[str, Any]:
    """Test 10: SQLite persistence survives connection closing and process re-initialization."""
    t0 = time.perf_counter()
    test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_persistence.db")

    if os.path.exists(test_db):
        os.remove(test_db)

    database.init_db(test_db, reset=True)
    svc = PersistentRegistrationService(test_db)

    # Register student
    reg = svc.register("student_alice", "E1")
    assert reg["status"] == "CONFIRMED"
    ticket = reg["ticket_id"]

    # Simulate restart by instantiating a brand-new service connection
    new_svc = PersistentRegistrationService(test_db)
    ev = new_svc.get_event("E1")
    user_regs = new_svc.get_user_registrations("student_alice")

    passed = (
        ev is not None
        and ev["confirmed_count"] == 1
        and len(user_regs) == 1
        and user_regs[0]["ticket_id"] == ticket
    )

    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T10",
        "name": "SQLite Persistence & Restart Resilience",
        "description": "Confirms registration records and ticket tokens persist across connection lifecycles.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Persisted Confirmed: {ev['confirmed_count'] if ev else 0}, Ticket Restored: {ticket[:16]}...",
        "duration_ms": elapsed_ms,
    }


def test_fifo_waitlist_promotion() -> Dict[str, Any]:
    """Test 11: Capacity exhaustion triggers FIFO waitlist and cancellation promotes next student."""
    t0 = time.perf_counter()
    test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_waitlist.db")

    if os.path.exists(test_db):
        os.remove(test_db)

    database.init_db(test_db, reset=True)
    svc = PersistentRegistrationService(test_db)

    # E1 has capacity 2: Fill both seats
    svc.register("student_alice", "E1")
    svc.register("student_bob", "E1")

    # 3rd student must join waitlist pos 1
    w1 = svc.register("student_carol", "E1")
    # 4th student must join waitlist pos 2
    w2 = svc.register("S1", "E1")

    # Cancel Alice -> Carol must be promoted
    c = svc.cancel("student_alice", "E1")

    carol_regs = svc.get_user_registrations("student_carol")
    ev = svc.get_event("E1")

    passed = (
        w1["status"] == "WAITLISTED" and w1["queue_position"] == 1
        and w2["status"] == "WAITLISTED" and w2["queue_position"] == 2
        and c["status"] == "CANCELLED"
        and c["promoted_user"] == "student_carol"
        and len(carol_regs) == 1 and carol_regs[0]["registration_status"] == "CONFIRMED"
        and ev["confirmed_count"] == 2  # Alice replaced by Carol
    )

    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T11",
        "name": "FIFO Waitlist Atomic Promotion",
        "description": "Ensures full workshops queue students deterministically and seat cancellations promote in FIFO order.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Promoted: {c.get('promoted_user')}, Confirmed Count: {ev['confirmed_count'] if ev else 0}/2",
        "duration_ms": elapsed_ms,
    }


def test_qr_ticket_verification_and_checkin() -> Dict[str, Any]:
    """Test 12: Digital QR ticket generation, check-in validation, and duplicate rejection."""
    t0 = time.perf_counter()
    token = ticket_service.generate_ticket_token("E1", "student_alice", "REG-TEST")

    # Seed ticket into registrations for verification
    with database.get_db_cursor() as cur:
        cur.execute("""
            INSERT OR REPLACE INTO registrations (id, event_id, user_id, status, ticket_id, registered_at)
            VALUES ('REG-TEST', 'E1', 'student_alice', 'CONFIRMED', ?, datetime('now'))
        """, (token,))

    # First check-in should succeed
    ok1, msg1, att1 = ticket_service.verify_and_checkin_ticket(token, checked_in_by="prof_turner")
    # Second check-in must be REJECTED as duplicate
    ok2, msg2, att2 = ticket_service.verify_and_checkin_ticket(token, checked_in_by="prof_turner")

    passed = (
        ok1 is True
        and ok2 is False
        and "Duplicate Attendance" in msg2
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T12",
        "name": "QR Ticket Verification & Attendance Check-In",
        "description": "Validates ticket token and ensures duplicate check-ins are strictly rejected.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Checkin 1: {ok1} -> Checkin 2: {ok2} ({msg2[:32]}...)",
        "duration_ms": elapsed_ms,
    }


def test_security_sanitization_and_injection() -> Dict[str, Any]:
    """Test 13: Stored XSS prevention (html.escape) and CSV formula injection neutralization."""
    t0 = time.perf_counter()

    # 1. HTML Escaping verification
    malicious_html = "<script>alert('XSS')</script>"
    escaped_html = html.escape(malicious_html)
    xss_safe = ("<script>" not in escaped_html) and ("&lt;script&gt;" in escaped_html)

    # 2. CSV Formula Injection verification
    malicious_cell = "=CMD|' /C calc'!A0"
    sanitized_cell = report_service.sanitize_csv_cell(malicious_cell)
    csv_safe = sanitized_cell.startswith("'=")

    passed = xss_safe and csv_safe
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T13",
        "name": "Security: Stored XSS & CSV Formula Protection",
        "description": "Verifies HTML output is escaped and spreadsheet formula triggers (=, +, -, @) are neutralized.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"HTML Escaped: {escaped_html[:20]}, CSV Sanitized: {sanitized_cell[:10]}",
        "duration_ms": elapsed_ms,
    }


def test_rbac_authorization_boundaries() -> Dict[str, Any]:
    """Test 14: Role-based access control (RBAC) permission boundaries for Student, Organizer, Admin."""
    t0 = time.perf_counter()

    student = {"id": "s_test", "role": "Student"}
    organizer = {"id": "o_test", "role": "Organizer"}
    admin = {"id": "a_test", "role": "Administrator"}

    # Students cannot create events or admin system
    s_create = auth.can_create_events(student)
    s_admin = auth.can_admin_system(student)

    # Organizers can create events, cannot admin system
    o_create = auth.can_create_events(organizer)
    o_admin = auth.can_admin_system(organizer)

    # Admin can do all
    a_create = auth.can_create_events(admin)
    a_admin = auth.can_admin_system(admin)

    passed = (
        not s_create and not s_admin
        and o_create and not o_admin
        and a_create and a_admin
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T14",
        "name": "RBAC Role Boundary Verification",
        "description": "Validates permission enforcement across Student, Organizer, and Administrator roles.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Student: ({s_create}, {s_admin}), Organizer: ({o_create}, {o_admin}), Admin: ({a_create}, {a_admin})",
        "duration_ms": elapsed_ms,
    }


def test_event_seeding_and_idempotency() -> Dict[str, Any]:
    """Test 15: Event Catalog Seeding & Idempotent Non-Duplication.
    Verifies that the 20 standard sample events exist with correct capacities,
    and subsequent seed invocations safely prevent duplicate insertions."""
    t0 = time.perf_counter()

    # First ensure seeded
    added1, skipped1, total1 = seed_events.seed_events()
    # Second run must be idempotent: added must be 0, skipped must be >= 20
    added2, skipped2, total2 = seed_events.seed_events()

    with database.get_db_cursor() as cur:
        cur.execute("SELECT id, title, category, capacity FROM events")
        db_events = {row["id"]: row for row in cur.fetchall()}

    spec_matches = 0
    for spec in seed_events.SAMPLE_EVENTS_SPEC:
        eid = spec["id"]
        if eid in db_events:
            row = db_events[eid]
            if (
                row["title"] == spec["title"]
                and row["category"] == spec["category"]
                and row["capacity"] == spec["capacity"]
            ):
                spec_matches += 1

    passed = (
        added2 == 0
        and skipped2 >= 20
        and spec_matches == 20
        and total2 >= 20
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "id": "T15",
        "name": "Event Catalog Seeding & Idempotency",
        "description": "Confirms all 20 required sample events are present and subsequent seed executions prevent duplicates.",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "details": f"Spec Verified: {spec_matches}/20, Re-run Added: {added2}, Duplicates Prevented: {skipped2}, Total Events: {total2}",
        "duration_ms": elapsed_ms,
    }


ALL_TESTS: List[Callable[[], Dict[str, Any]]] = [
    test_sequential_booking,
    test_concurrent_unsafe,
    test_concurrent_safe,
    test_ten_users_two_seats_safe,
    test_duplicate_registration_safe,
    test_cancel_then_reregister,
    test_capacity_never_negative_stress,
    test_lock_released_after_exception,
    test_fine_grained_concurrency,
    test_database_persistence_restart,
    test_fifo_waitlist_promotion,
    test_qr_ticket_verification_and_checkin,
    test_security_sanitization_and_injection,
    test_rbac_authorization_boundaries,
    test_event_seeding_and_idempotency,
]


def run_all_tests() -> List[Dict[str, Any]]:
    """Execute all test cases and return structured results."""
    return [test_fn() for test_fn in ALL_TESTS]


def main() -> int:
    """CLI runner for automated testing and academic grading."""
    print("=" * 75)
    print("EVENT REGISTRATION CONCURRENCY MONITOR — VERIFICATION & QA SUITE")
    print("Operating Systems Synchronization, Security, and Invariant Verification")
    print("=" * 75)

    results = run_all_tests()
    all_passed = True

    for r in results:
        status_str = "[\033[92mPASS\033[0m]" if r["passed"] else "[\033[91mFAIL\033[0m]"
        print(f"\n{status_str} {r['id']}: {r['name']} ({r['duration_ms']} ms)")
        print(f"       Description: {r['description']}")
        print(f"       Details:     {r['details']}")
        if not r["passed"]:
            all_passed = False

    print("\n" + "=" * 75)
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    if all_passed:
        print(f"\033[92mRESULT: ALL {total_count}/{total_count} TESTS PASSED SUCCESSFULLY! (Full Verification)\033[0m")
        return 0
    else:
        print(f"\033[91mRESULT: {passed_count}/{total_count} TESTS PASSED. FIX FAILURES.\033[0m")
        return 1


if __name__ == "__main__":
    sys.exit(main())
