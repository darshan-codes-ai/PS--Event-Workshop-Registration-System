"""
Simulator Module - Multi-Thread Concurrency Simulation (Safe vs Unsafe)
Operating Systems Demonstration: Race Conditions vs Mutual Exclusion

This module coordinates concurrent threads attempting to register for workshops.
Worker threads run concurrently, record their outcomes in thread-safe collections,
and NEVER interact with Streamlit (st.*) functions. All results are aggregated
and returned after thread.join() completes.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from registration_engine import EventStore


def _worker_task(
    user: str,
    event_id: str,
    use_lock: bool,
    delay: float,
    store: EventStore,
    results_list: List[Dict[str, Any]],
    results_lock: threading.Lock,
    start_barrier: Optional[threading.Barrier] = None,
    stagger_delay: float = 0.0,
) -> None:
    """
    Individual thread worker routine.
    Synchronizes at the start barrier to ensure simultaneous arrival,
    calls store.register(), and safely collects results.
    """
    if start_barrier is not None:
        try:
            start_barrier.wait(timeout=5.0)
        except threading.BrokenBarrierError:
            pass

    if stagger_delay > 0:
        time.sleep(stagger_delay)

    # Perform registration attempt
    result = store.register(user=user, event_id=event_id, use_lock=use_lock, delay=delay)

    # Thread-safe result collection
    with results_lock:
        results_list.append(result)


def run_simulation(
    event_id: str,
    users: List[str],
    use_lock: bool,
    delay: float = 0.3,
    stagger_ms: float = 0.0,
    store: Optional[EventStore] = None,
) -> Dict[str, Any]:
    """
    Execute a concurrent registration simulation with one thread per user.

    Parameters:
    - event_id: Target workshop ID (e.g., 'E1')
    - users: List of user IDs attempting concurrent registration
    - use_lock: True for Mutex ON (Safe), False for Mutex OFF (Unsafe)
    - delay: Processing delay inside critical section (seconds)
    - stagger_ms: Milliseconds delay between thread launches (0 for burst)
    - store: Optional EventStore instance to run against; if None, a fresh one is created.

    Returns:
    - Comprehensive simulation metrics and per-thread telemetry.
    """
    if store is None:
        store = EventStore()

    if event_id not in store.events:
        raise ValueError(f"Event ID '{event_id}' not found in store.")

    initial_event_state = store.get_event_summary(event_id)
    initial_remaining = initial_event_state["remaining_places"]
    capacity = initial_event_state["capacity"]

    num_threads = len(users)
    results_list: List[Dict[str, Any]] = []
    results_lock = threading.Lock()

    # Barrier synchronizes all threads at the starting line for a simultaneous burst
    start_barrier = threading.Barrier(num_threads) if num_threads > 1 else None

    threads: List[threading.Thread] = []
    for idx, user in enumerate(users):
        stagger = (idx * stagger_ms / 1000.0) if stagger_ms > 0 else 0.0
        t = threading.Thread(
            target=_worker_task,
            name=f"Thread-{user}",
            args=(
                user,
                event_id,
                use_lock,
                delay,
                store,
                results_list,
                results_lock,
                start_barrier,
                stagger,
            ),
        )
        threads.append(t)

    # Begin timing
    sim_start_time = time.perf_counter()

    # Spawn all threads
    for t in threads:
        t.start()

    # Await completion of all threads
    for t in threads:
        t.join()

    sim_end_time = time.perf_counter()
    total_runtime_ms = round((sim_end_time - sim_start_time) * 1000.0, 2)

    # Evaluate final system state and invariants
    final_event_state = store.get_event_summary(event_id)
    final_remaining = final_event_state["remaining_places"]
    confirmed_users = final_event_state["registered_users"]
    violations = store.validate_state(event_id)

    confirmed_count = sum(1 for r in results_list if r["status"] == "CONFIRMED")
    full_count = sum(1 for r in results_list if r["status"] == "FULL")
    duplicate_count = sum(1 for r in results_list if r["status"] == "DUPLICATE")

    # Overbooking occurs if confirmed count exceeds event capacity or remaining places drops below 0
    overbooked = (confirmed_count > capacity) or (final_remaining < 0) or (len(violations) > 0)

    # Sort results by completion timestamp for clear display
    sorted_results = sorted(results_list, key=lambda x: x.get("cs_exit_time", 0.0))

    # Format timeline telemetry for Gantt chart rendering
    timeline_data: List[Dict[str, Any]] = []
    base_time = sim_start_time

    for r in sorted_results:
        req_rel = max(0.0, (r.get("req_time", base_time) - base_time) * 1000.0)
        cs_entry_rel = max(req_rel, (r.get("cs_entry_time", base_time) - base_time) * 1000.0)
        cs_exit_rel = max(cs_entry_rel, (r.get("cs_exit_time", base_time) - base_time) * 1000.0)

        timeline_data.append({
            "Thread": r["thread_name"],
            "User": r["user"],
            "Status": r["status"],
            "Wait_Start_ms": round(req_rel, 2),
            "CS_Entry_ms": round(cs_entry_rel, 2),
            "CS_Exit_ms": round(cs_exit_rel, 2),
            "Wait_Duration_ms": round(cs_entry_rel - req_rel, 2),
            "CS_Duration_ms": round(cs_exit_rel - cs_entry_rel, 2),
            "Total_Duration_ms": round(cs_exit_rel - req_rel, 2),
        })

    return {
        "event_id": event_id,
        "event_name": initial_event_state["name"],
        "capacity": capacity,
        "initial_remaining": initial_remaining,
        "final_remaining": final_remaining,
        "use_lock": use_lock,
        "delay": delay,
        "users": users,
        "thread_results": sorted_results,
        "confirmed_count": confirmed_count,
        "full_count": full_count,
        "duplicate_count": duplicate_count,
        "overbooked": overbooked,
        "violations": violations,
        "total_runtime_ms": total_runtime_ms,
        "timeline_data": timeline_data,
        "registered_users": confirmed_users,
        "sim_start_time": sim_start_time,
        "sim_end_time": sim_end_time,
    }


def run_comparison(
    event_id: str,
    users: List[str],
    delay: float = 0.3,
    stagger_ms: float = 0.0,
    capacity_override: Optional[int] = None,
    remaining_override: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute a side-by-side comparative simulation:
    Runs the IDENTICAL workload first in UNSAFE mode (Mutex OFF) and then
    in SAFE mode (Mutex ON), each on a clean cloned state.

    Returns:
    - Dictionary with 'unsafe' and 'safe' outcome objects and comparison metrics.
    """
    # Create baseline store for the test
    base_store = EventStore()
    if capacity_override is not None:
        base_store.events[event_id]["capacity"] = capacity_override
    if remaining_override is not None:
        base_store.events[event_id]["remaining_places"] = remaining_override
    elif capacity_override is not None:
        base_store.events[event_id]["remaining_places"] = capacity_override

    # 1. Run Unsafe Simulation on fresh copy
    unsafe_store = base_store.clone()
    unsafe_result = run_simulation(
        event_id=event_id,
        users=list(users),
        use_lock=False,
        delay=delay,
        stagger_ms=stagger_ms,
        store=unsafe_store,
    )

    # 2. Run Safe Simulation on another fresh copy
    safe_store = base_store.clone()
    safe_result = run_simulation(
        event_id=event_id,
        users=list(users),
        use_lock=True,
        delay=delay,
        stagger_ms=stagger_ms,
        store=safe_store,
    )

    return {
        "event_id": event_id,
        "users": users,
        "delay": delay,
        "capacity": base_store.events[event_id]["capacity"],
        "unsafe": unsafe_result,
        "safe": safe_result,
        "race_demonstrated": unsafe_result["overbooked"],
        "safe_guaranteed": not safe_result["overbooked"] and len(safe_result["violations"]) == 0,
    }

