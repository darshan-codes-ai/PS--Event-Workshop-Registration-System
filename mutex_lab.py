"""
mutex_lab.py - Mutex & Process Synchronization Laboratory
Demonstrates the classic check-then-act race condition and how threading.Lock()
guarantees mutual exclusion and prevents overbooking.
"""

import threading
import time
from typing import Any, Dict, List


class ConcurrencySimulator:
    """Simulates concurrent user registrations on a shared event capacity."""

    def __init__(self, capacity: int = 1):
        self.capacity = capacity
        self.available_seats = capacity
        self.confirmed_users: List[str] = []
        self.rejected_users: List[str] = []
        self.lock = threading.Lock()
        self.logs: List[Dict[str, Any]] = []
        self._logs_guard = threading.Lock()

    def _log(self, thread_name: str, user: str, action: str, details: str, seats: int) -> None:
        with self._logs_guard:
            self.logs.append({
                "time": round(time.time(), 4),
                "thread": thread_name,
                "user": user,
                "action": action,
                "details": details,
                "available_seats": seats,
            })

    def register_unsafe(self, user_name: str, barrier: threading.Barrier, delay: float) -> None:
        """
        Unsynchronized registration (Without Mutex).
        Demonstrates the race condition: reading capacity and writing are split,
        allowing interleaved threads to read stale seats and cause overbooking.
        """
        th_name = threading.current_thread().name
        # Synchronize all threads so they strike the critical section concurrently
        barrier.wait()

        # Step 1: READ shared resource (VULNERABLE READ WINDOW)
        seats_read = self.available_seats
        self._log(th_name, user_name, "READ_SEATS", f"Saw {seats_read} available seats", seats_read)

        # Step 2: Context Switch / Interleaving Delay
        time.sleep(delay)

        # Step 3: Check-Then-Act without synchronization
        if seats_read > 0:
            self.available_seats -= 1
            self.confirmed_users.append(user_name)
            self._log(th_name, user_name, "CONFIRMED", f"Seat granted! Remaining count: {self.available_seats}", self.available_seats)
        else:
            self.rejected_users.append(user_name)
            self._log(th_name, user_name, "REJECTED_FULL", "No seats available", self.available_seats)

    def register_safe(self, user_name: str, barrier: threading.Barrier, delay: float) -> None:
        """
        Mutex-protected registration (With Mutex).
        Enforces mutual exclusion using threading.Lock(): only one thread enters
        the critical section at a time, preventing race conditions and overbooking.
        """
        th_name = threading.current_thread().name
        barrier.wait()

        # Step 1: Acquire Mutex
        self._log(th_name, user_name, "LOCK_WAITING", "Waiting to acquire mutex...", self.available_seats)
        self.lock.acquire()
        try:
            # --- CRITICAL SECTION BEGINS ---
            self._log(th_name, user_name, "LOCK_ACQUIRED", "Entered critical section", self.available_seats)

            seats_read = self.available_seats
            self._log(th_name, user_name, "READ_SEATS", f"Checked current seats: {seats_read}", seats_read)

            # Simulated processing inside critical section
            time.sleep(delay)

            if self.available_seats > 0:
                self.available_seats -= 1
                self.confirmed_users.append(user_name)
                self._log(th_name, user_name, "CONFIRMED", f"Seat granted! Remaining count: {self.available_seats}", self.available_seats)
            else:
                self.rejected_users.append(user_name)
                self._log(th_name, user_name, "REJECTED_FULL", "Workshop is FULL. Seat rejected.", self.available_seats)
            # --- CRITICAL SECTION ENDS ---
        finally:
            # Step 6: Always release lock in finally block to prevent deadlocks
            self.lock.release()
            self._log(th_name, user_name, "LOCK_RELEASED", "Released mutex lock", self.available_seats)


def run_simulation(
    num_users: int = 3,
    capacity: int = 1,
    use_mutex: bool = False,
    delay: float = 0.03,
) -> Dict[str, Any]:
    """
    Execute a multi-threaded registration simulation with or without mutex synchronization.
    Returns quantitative results, invariants, and execution logs.
    """
    sim = ConcurrencySimulator(capacity=capacity)
    barrier = threading.Barrier(num_users)
    threads: List[threading.Thread] = []

    user_names = [f"Student_{i + 1}" for i in range(num_users)]

    for name in user_names:
        target_fn = sim.register_safe if use_mutex else sim.register_unsafe
        t = threading.Thread(target=target_fn, args=(name, barrier, delay), name=f"Thread-{name}")
        threads.append(t)

    t_start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration_ms = round((time.perf_counter() - t_start) * 1000, 2)

    confirmed_count = len(sim.confirmed_users)
    rejected_count = len(sim.rejected_users)
    overbooked = confirmed_count > capacity or sim.available_seats < 0

    return {
        "use_mutex": use_mutex,
        "mode": "With Mutex (Safe)" if use_mutex else "Without Mutex (Unsafe)",
        "capacity": capacity,
        "num_users": num_users,
        "confirmed_count": confirmed_count,
        "rejected_count": rejected_count,
        "confirmed_users": sim.confirmed_users,
        "rejected_users": sim.rejected_users,
        "final_available_seats": sim.available_seats,
        "overbooked": overbooked,
        "duration_ms": duration_ms,
        "logs": sim.logs,
    }


def run_side_by_side_comparison(
    num_users: int = 3,
    capacity: int = 1,
    delay: float = 0.03,
) -> Dict[str, Any]:
    """Execute both Unsafe and Safe simulations under identical parameters for comparative analysis."""
    unsafe_res = run_simulation(num_users=num_users, capacity=capacity, use_mutex=False, delay=delay)
    safe_res = run_simulation(num_users=num_users, capacity=capacity, use_mutex=True, delay=delay)

    comparison_table = [
        {"Parameter": "Synchronization Mechanism", "Without Mutex": "None (Unsynchronized)", "With Mutex": "threading.Lock()"},
        {"Parameter": "Critical Section Protection", "Without Mutex": "No (Unprotected Read-Write)", "With Mutex": "Yes (try...finally Locked)"},
        {"Parameter": "Race Condition", "Without Mutex": "Observed / Possible", "With Mutex": "Completely Prevented"},
        {"Parameter": "Overbooking Occurred?", "Without Mutex": "YES (Overbooked!)" if unsafe_res["overbooked"] else "Possible under contention", "With Mutex": "NO (Strictly Prevented)"},
        {"Parameter": "Confirmed Registrations", "Without Mutex": f"{unsafe_res['confirmed_count']} (Capacity: {capacity})", "With Mutex": f"{safe_res['confirmed_count']} (Capacity: {capacity})"},
        {"Parameter": "Final Available Seats", "Without Mutex": str(unsafe_res["final_available_seats"]), "With Mutex": str(safe_res["final_available_seats"])},
        {"Parameter": "Data Consistency Invariant", "Without Mutex": "VIOLATED" if unsafe_res["overbooked"] else "Uncertain", "With Mutex": "PRESERVED"},
    ]

    return {
        "unsafe": unsafe_res,
        "safe": safe_res,
        "table": comparison_table,
    }


if __name__ == "__main__":
    print("Testing Mutex Simulation Engine...")
    comp = run_side_by_side_comparison(num_users=3, capacity=1)
    print("\n--- UNSAFE (NO MUTEX) ---")
    print(f"Confirmed: {comp['unsafe']['confirmed_count']}, Final Seats: {comp['unsafe']['final_available_seats']}, Overbooked: {comp['unsafe']['overbooked']}")
    print("\n--- SAFE (WITH MUTEX) ---")
    print(f"Confirmed: {comp['safe']['confirmed_count']}, Final Seats: {comp['safe']['final_available_seats']}, Overbooked: {comp['safe']['overbooked']}")
