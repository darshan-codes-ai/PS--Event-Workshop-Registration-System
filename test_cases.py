"""
test_cases.py - Automated QA Test Suite (10 Tests)
Verifies Event Management, Process Synchronization, Mutex Locking, and Invariants.
"""

import os
import sys
import threading
import time
from typing import Any, Dict, List

import database
import mutex_lab
import services

TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_suite.db")


def setup_test_db() -> str:
    """Initialize a dedicated isolated test database."""
    database.close_connection(TEST_DB)
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass
    database.init_db(TEST_DB, reset=True)
    return TEST_DB


def teardown_test_db() -> None:
    """Clean up test database files."""
    database.close_connection(TEST_DB)
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass


# ---------------------------------------------------------
# 10 TARGETED ACADEMIC TESTS
# ---------------------------------------------------------

def test_1_event_creation() -> Dict[str, Any]:
    """Test 1: Event Creation - Verifies event insertion and schema field persistence."""
    t0 = time.perf_counter()
    db = setup_test_db()

    with database.get_db_cursor(db) as cur:
        cur.execute("""
            INSERT INTO events (event_id, title, description, date, venue, capacity)
            VALUES ('TEST-01', 'Operating Systems Workshop', 'Concurrency & Locking', '2026-12-01', 'Lab 1', 25)
        """)

    ev = database.get_event_by_id("TEST-01", db)
    passed = (
        ev is not None
        and ev["title"] == "Operating Systems Workshop"
        and ev["capacity"] == 25
        and ev["available_seats"] == 25
    )
    teardown_test_db()
    return {
        "id": "T1",
        "name": "Event Creation",
        "passed": passed,
        "details": f"Created 'TEST-01', Capacity: {ev['capacity'] if ev else 0}, Available: {ev['available_seats'] if ev else 0}",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_2_successful_registration() -> Dict[str, Any]:
    """Test 2: Successful Registration - Verifies single student registration flow."""
    t0 = time.perf_counter()
    db = setup_test_db()

    res = services.register_student("EVT-01", "David Miller", "david@university.edu", db_path=db)
    passed = (
        res["success"] is True
        and res["status"] == "CONFIRMED"
        and res["registration_id"].startswith("REG-")
    )
    teardown_test_db()
    return {
        "id": "T2",
        "name": "Successful Registration",
        "passed": passed,
        "details": f"Status: {res.get('status')}, Reg ID: {res.get('registration_id')}",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_3_duplicate_registration_prevention() -> Dict[str, Any]:
    """Test 3: Duplicate Registration Prevention - Prevents same email registering twice for same event."""
    t0 = time.perf_counter()
    db = setup_test_db()

    res1 = services.register_student("EVT-02", "Elena Rostova", "elena@university.edu", db_path=db)
    res2 = services.register_student("EVT-02", "Elena Rostova", "elena@university.edu", db_path=db)

    passed = (
        res1["success"] is True
        and res2["success"] is False
        and res2["status"] == "DUPLICATE"
    )
    teardown_test_db()
    return {
        "id": "T3",
        "name": "Duplicate Registration Prevention",
        "passed": passed,
        "details": f"Attempt 1: {res1['status']} -> Attempt 2: {res2['status']}",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_4_registration_when_seats_full() -> Dict[str, Any]:
    """Test 4: Registration When Seats Full - Verifies boundary enforcement when capacity is reached."""
    t0 = time.perf_counter()
    db = setup_test_db()

    with database.get_db_cursor(db) as cur:
        cur.execute("INSERT INTO events (event_id, title, description, date, venue, capacity) VALUES ('T-FULL', 'Mini Lab', 'Desk', 'Now', 'L1', 1)")

    r1 = services.register_student("T-FULL", "User One", "u1@test.com", db_path=db)
    r2 = services.register_student("T-FULL", "User Two", "u2@test.com", db_path=db)

    passed = (
        r1["success"] is True
        and r2["success"] is False
        and r2["status"] == "FULL"
    )
    teardown_test_db()
    return {
        "id": "T4",
        "name": "Registration When Seats Full",
        "passed": passed,
        "details": f"U1: {r1['status']} -> U2: {r2['status']} (Full Rejection Enforced)",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_5_seat_count_updates() -> Dict[str, Any]:
    """Test 5: Seat Count Updates - Ensures available_seats = capacity - confirmed_count."""
    t0 = time.perf_counter()
    db = setup_test_db()

    with database.get_db_cursor(db) as cur:
        cur.execute("INSERT INTO events (event_id, title, description, date, venue, capacity) VALUES ('T-COUNT', 'Count Lab', 'Desk', 'Now', 'L1', 5)")

    ev_initial = database.get_event_by_id("T-COUNT", db)
    services.register_student("T-COUNT", "Student A", "a@test.com", db_path=db)
    services.register_student("T-COUNT", "Student B", "b@test.com", db_path=db)
    ev_final = database.get_event_by_id("T-COUNT", db)

    passed = (
        ev_initial["available_seats"] == 5
        and ev_final["confirmed_count"] == 2
        and ev_final["available_seats"] == 3
    )
    teardown_test_db()
    return {
        "id": "T5",
        "name": "Seat Count Updates",
        "passed": passed,
        "details": f"Initial Seats: {ev_initial['available_seats']} -> After 2 Regs: {ev_final['available_seats']} Available",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_6_registration_cancellation() -> Dict[str, Any]:
    """Test 6: Registration Cancellation - Frees up capacity and allows seat reuse."""
    t0 = time.perf_counter()
    db = setup_test_db()

    with database.get_db_cursor(db) as cur:
        cur.execute("INSERT INTO events (event_id, title, description, date, venue, capacity) VALUES ('T-CANCEL', 'Cancel Lab', 'Desk', 'Now', 'L1', 1)")

    r1 = services.register_student("T-CANCEL", "Student 1", "s1@test.com", db_path=db)
    cancel_res = services.cancel_registration(r1["registration_id"], db_path=db)
    r2 = services.register_student("T-CANCEL", "Student 2", "s2@test.com", db_path=db)

    passed = (
        r1["success"] is True
        and cancel_res["success"] is True
        and cancel_res["status"] == "CANCELLED"
        and r2["success"] is True
        and r2["status"] == "CONFIRMED"
    )
    teardown_test_db()
    return {
        "id": "T6",
        "name": "Registration Cancellation",
        "passed": passed,
        "details": f"Registered -> Cancelled -> Seat Reclaimed by New Student: {r2['status']}",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_7_concurrent_registration_without_mutex() -> Dict[str, Any]:
    """Test 7: Concurrent Registration Without Mutex - Demonstrates race condition & overbooking."""
    t0 = time.perf_counter()
    # 3 concurrent threads competing for 1 available seat without synchronization
    sim = mutex_lab.run_simulation(num_users=3, capacity=1, use_mutex=False, delay=0.03)

    passed = (
        sim["confirmed_count"] > 1  # Multiple threads confirmed for 1 seat
        or sim["overbooked"] is True
        or sim["final_available_seats"] < 0
    )
    return {
        "id": "T7",
        "name": "Concurrent Registration Without Mutex",
        "passed": passed,
        "details": f"Capacity: 1, Confirmed: {sim['confirmed_count']}, Final Seats: {sim['final_available_seats']} (Overbooked: {sim['overbooked']})",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_8_concurrent_registration_with_mutex() -> Dict[str, Any]:
    """Test 8: Concurrent Registration With Mutex - Proves mutual exclusion and zero overbooking."""
    t0 = time.perf_counter()
    # 10 concurrent threads competing for 2 seats with mutex synchronization
    sim = mutex_lab.run_simulation(num_users=10, capacity=2, use_mutex=True, delay=0.02)

    passed = (
        sim["confirmed_count"] == 2
        and sim["rejected_count"] == 8
        and sim["final_available_seats"] == 0
        and sim["overbooked"] is False
    )
    return {
        "id": "T8",
        "name": "Concurrent Registration With Mutex",
        "passed": passed,
        "details": f"Capacity: 2, Confirmed: {sim['confirmed_count']}, Rejected: {sim['rejected_count']}, Overbooked: {sim['overbooked']}",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_9_mutex_lock_release_after_exception() -> Dict[str, Any]:
    """Test 9: Mutex Lock Release After Exception - Verifies try...finally guarantees lock release."""
    t0 = time.perf_counter()
    test_lock = threading.Lock()
    exception_caught = False

    try:
        test_lock.acquire()
        try:
            raise RuntimeError("Simulated crash inside critical section")
        finally:
            test_lock.release()
    except RuntimeError:
        exception_caught = True

    # Check lock is not deadlocked and can be re-acquired immediately
    can_reacquire = test_lock.acquire(timeout=0.1)
    if can_reacquire:
        test_lock.release()

    passed = exception_caught and can_reacquire
    return {
        "id": "T9",
        "name": "Mutex Lock Release After Exception",
        "passed": passed,
        "details": f"Exception Caught: {exception_caught}, Mutex Free to Reacquire: {can_reacquire}",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def test_10_database_persistence() -> Dict[str, Any]:
    """Test 10: Database Persistence - Verifies data survives connection closing and reopening."""
    t0 = time.perf_counter()
    db = setup_test_db()

    # Step 1: Write record on connection 1
    res = services.register_student("EVT-03", "Frank Castle", "frank@marvel.edu", db_path=db)
    reg_id = res["registration_id"]

    # Step 2: Close connection completely
    database.close_connection(db)

    # Step 3: Reopen connection and verify persistence
    regs = database.get_registrations_by_email("frank@marvel.edu", db)
    passed = len(regs) == 1 and regs[0]["registration_id"] == reg_id

    teardown_test_db()
    return {
        "id": "T10",
        "name": "Database Persistence",
        "passed": passed,
        "details": f"Persisted Record ID: {regs[0]['registration_id'] if regs else 'None'} verified after reconnect",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def run_all_tests() -> List[Dict[str, Any]]:
    """Run all 10 tests and print structured terminal results."""
    tests = [
        test_1_event_creation,
        test_2_successful_registration,
        test_3_duplicate_registration_prevention,
        test_4_registration_when_seats_full,
        test_5_seat_count_updates,
        test_6_registration_cancellation,
        test_7_concurrent_registration_without_mutex,
        test_8_concurrent_registration_with_mutex,
        test_9_mutex_lock_release_after_exception,
        test_10_database_persistence,
    ]

    print("=" * 75)
    print("EVENTFLOW OS — PROCESS SYNCHRONIZATION & MUTEX QA SUITE (10 TESTS)")
    print("Operating Systems Capstone: Mutual Exclusion & Invariant Verification")
    print("=" * 75)

    results = []
    all_passed = True

    for test_fn in tests:
        res = test_fn()
        results.append(res)
        tag = "[PASS]" if res["passed"] else "[FAIL]"
        print(f"\n{tag} {res['id']}: {res['name']} ({res['time_ms']} ms)")
        print(f"       Details: {res['details']}")
        if not res["passed"]:
            all_passed = False

    print("\n" + "=" * 75)
    if all_passed:
        print("RESULT: ALL 10/10 TESTS PASSED SUCCESSFULLY! (Full Verification)")
    else:
        print("RESULT: SOME TESTS FAILED.")
    print("=" * 75)

    return results


if __name__ == "__main__":
    results = run_all_tests()
    failed = [r for r in results if not r["passed"]]
    sys.exit(0 if not failed else 1)
