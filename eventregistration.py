"""
Event / Workshop Registration System  (Product 8)
Concept: critical section + mutex (threading.Lock)

Shared data  : events[event_id]["seats"]  and  registrations[event_id]
Critical sec : duplicate check + seats check + seats decrement + add user
"""
import threading
import time

# ---------------- Shared data ----------------
events = {
    "E1": {"name": "Python Workshop", "capacity": 2, "seats": 2},
    "E2": {"name": "AI Seminar", "capacity": 3, "seats": 3},
}
registrations = {"E1": set(), "E2": set()}   # event_id -> set of user ids

lock = threading.Lock()
USE_LOCK = True        # set False to see the race condition (overbooking)
DELAY = 0.2            # teaching delay: widens the gap between check and update


def reset(use_lock):
    """Restore the initial state before each test run."""
    global USE_LOCK
    USE_LOCK = use_lock
    for eid, e in events.items():
        e["seats"] = e["capacity"]
        registrations[eid].clear()


# ---------------- Operations ----------------
def register(user, event_id):
    if USE_LOCK:
        lock.acquire()
    try:
        # ---------- CRITICAL SECTION START ----------
        if user in registrations[event_id]:
            print(f"{user}: already registered for {event_id} (duplicate)")
        elif events[event_id]["seats"] > 0:
            time.sleep(DELAY)                       # simulates processing work
            events[event_id]["seats"] -= 1
            registrations[event_id].add(user)
            print(f"{user}: registration CONFIRMED for {event_id}")
        else:
            print(f"{user}: {event_id} is FULL")
        # ---------- CRITICAL SECTION END ----------
    finally:
        if USE_LOCK:
            lock.release()


def cancel(user, event_id):
    if USE_LOCK:
        lock.acquire()
    try:
        if user in registrations[event_id]:
            registrations[event_id].remove(user)
            events[event_id]["seats"] += 1
            print(f"{user}: registration CANCELLED for {event_id}")
        else:
            print(f"{user}: not registered for {event_id}")
    finally:
        if USE_LOCK:
            lock.release()


def show_events():
    print("\n--- Event list ---")
    for eid, e in events.items():
        print(f"{eid} | {e['name']} | seats left: {e['seats']}/{e['capacity']}")
    print()


# ---------------- Simulation / testing ----------------
def run_test(title, use_lock, users, event_id):
    print(f"\n===== {title} =====")
    reset(use_lock)
    threads = [threading.Thread(target=register, args=(u, event_id)) for u in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    confirmed = len(registrations[event_id])
    print(f"Confirmed: {confirmed} | Capacity: {events[event_id]['capacity']} "
          f"| Seats left: {events[event_id]['seats']}")
    seats = events[event_id]["seats"]
    cap = events[event_id]["capacity"]
    if confirmed > cap or seats < 0:
        print("RESULT: OVERBOOKED (race condition!)")
    elif cap - seats != confirmed:
        print("RESULT: INCONSISTENT (seat count does not match registrations)")
    else:
        print("RESULT: correct")


if __name__ == "__main__":
    students = [f"S{i}" for i in range(1, 7)]

    # 6 students, 2 seats
    run_test("WITHOUT mutex", False, students, "E1")
    run_test("WITH mutex", True, students, "E1")

    # same student trying to register twice at the same time
    run_test("Duplicate attempt WITHOUT mutex", False, ["S1", "S1"], "E2")
    run_test("Duplicate attempt WITH mutex", True, ["S1", "S1"], "E2")

    # cancel and re-register
    print("\n===== Cancel test =====")
    reset(True)
    register("S1", "E1")
    cancel("S1", "E1")
    show_events()