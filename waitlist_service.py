"""
Waitlist & Semaphore Service - Operating Systems Synchronization Laboratory
Contrasts and demonstrates:
1. Mutex (threading.Lock): Single-thread mutual exclusion for critical sections
2. Counting Semaphore (threading.Semaphore): Counting resource permits for capacity pools
3. FIFO Queue: Deterministic, fair ordering policy for waitlist promotion
4. Database ACID Transaction: Persistent atomicity and isolation across system reboots
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


class SemaphoreResourcePool:
    """
    Educational demonstration of a Counting Semaphore managing a pool of N capacity permits.
    Shows how permits are decremented upon entry and incremented upon release.
    """

    def __init__(self, capacity: int = 2) -> None:
        self.capacity = max(1, capacity)
        self.semaphore = threading.Semaphore(value=self.capacity)
        self.active_permits_lock = threading.Lock()
        self.active_holders: List[str] = []
        self.audit_events: List[Dict[str, Any]] = []

    def acquire_permit(self, worker_id: str, timeout: float = 2.0) -> Tuple[bool, float]:
        """
        Attempt to acquire a counting semaphore permit.
        Returns (success, wait_ms).
        """
        t0 = time.perf_counter()
        acquired = self.semaphore.acquire(timeout=timeout)
        wait_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        if acquired:
            with self.active_permits_lock:
                self.active_holders.append(worker_id)
                self.audit_events.append({
                    "timestamp": time.strftime("%H:%M:%S"),
                    "worker": worker_id,
                    "action": "ACQUIRE_PERMIT",
                    "holders": list(self.active_holders),
                    "wait_ms": wait_ms,
                })
        else:
            with self.active_permits_lock:
                self.audit_events.append({
                    "timestamp": time.strftime("%H:%M:%S"),
                    "worker": worker_id,
                    "action": "TIMEOUT_REJECTED",
                    "holders": list(self.active_holders),
                    "wait_ms": wait_ms,
                })

        return acquired, wait_ms

    def release_permit(self, worker_id: str) -> None:
        """Release a counting semaphore permit back to the pool."""
        with self.active_permits_lock:
            if worker_id in self.active_holders:
                self.active_holders.remove(worker_id)
            self.audit_events.append({
                "timestamp": time.strftime("%H:%M:%S"),
                "worker": worker_id,
                "action": "RELEASE_PERMIT",
                "holders": list(self.active_holders),
            })
        self.semaphore.release()


def run_semaphore_simulation(
    capacity: int = 2,
    num_threads: int = 6,
    hold_delay: float = 0.2,
) -> Dict[str, Any]:
    """
    Run an educational multi-threaded simulation demonstrating Counting Semaphore permit allocation.
    """
    pool = SemaphoreResourcePool(capacity=capacity)
    results: List[Dict[str, Any]] = []
    res_lock = threading.Lock()

    def _worker(wid: str) -> None:
        t_req = time.perf_counter()
        acquired, wait_ms = pool.acquire_permit(wid, timeout=3.0)
        t_entry = time.perf_counter()

        if acquired:
            try:
                time.sleep(hold_delay)
            finally:
                pool.release_permit(wid)
            t_exit = time.perf_counter()
            with res_lock:
                results.append({
                    "worker": wid,
                    "status": "ACQUIRED_AND_RELEASED",
                    "wait_ms": wait_ms,
                    "held_ms": round((t_exit - t_entry) * 1000.0, 2),
                    "req_time": t_req,
                    "entry_time": t_entry,
                    "exit_time": t_exit,
                })
        else:
            with res_lock:
                results.append({
                    "worker": wid,
                    "status": "TIMED_OUT",
                    "wait_ms": wait_ms,
                    "held_ms": 0.0,
                    "req_time": t_req,
                    "entry_time": t_req,
                    "exit_time": t_req,
                })

    threads = [threading.Thread(target=_worker, args=(f"Student-{i}",), name=f"SemThread-{i}") for i in range(1, num_threads + 1)]

    t_start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    t_end = time.perf_counter()

    return {
        "capacity": capacity,
        "num_threads": num_threads,
        "results": sorted(results, key=lambda x: x.get("entry_time", 0.0)),
        "audit_events": pool.audit_events,
        "total_runtime_ms": round((t_end - t_start) * 1000.0, 2),
    }

