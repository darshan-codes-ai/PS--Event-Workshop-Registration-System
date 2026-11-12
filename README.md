# 🔒 EventFlow OS — Process Synchronization & Mutex Monitor
### Operating Systems & Computer Networks Academic Capstone

**Core OS Focus:** Process Synchronization, Critical Section Problem, and Mutual Exclusion (`threading.Lock`)  
**Implementation:** Python 3.10+ • Streamlit • SQLite (WAL Mode) • `threading`

---

## 📌 1. Project Overview
**EventFlow OS** is an academic software demonstration focused exclusively on two foundational Operating Systems concepts:
1. **Process Synchronization:** How concurrent threads safely coordinate access to a shared resource.
2. **Mutex Locks (Mutual Exclusion):** How atomic lock acquisition and release (`threading.Lock`) eliminate race conditions and prevent overbooking.

In this application, the **shared resource** is the available seat capacity of academic workshops. When multiple users submit concurrent registration requests for a workshop with only 1 or 2 seats remaining, an unsynchronized system suffers a **race condition**: threads interleave during the check-then-act window, read stale seat availability, and all confirm registrations, causing **overbooking** (capacity drops to negative values). 

By wrapping the critical section in a **Mutex Lock** using Python's `threading.Lock()` inside a `try...finally` block, only one registration thread executes the seat check and decrement at a time, ensuring strict data consistency and zero overbooking.

---

## 🎯 2. Operating Systems Concepts Explained

### 1. Process Synchronization
Process synchronization is the mechanism of coordinating the execution of concurrent threads or processes that share system resources (memory, files, variables) to maintain data consistency and prevent race hazards.

### 2. Shared Resource
A shared resource is any data structure or variable accessed by more than one concurrent thread. In this system, the primary shared resource is **`available_seats`** for each workshop.

### 3. Critical Section
The critical section is the code block where shared resources are checked and updated:
```python
# The Critical Section:
if available_seats > 0:            # 1. Read & evaluate
    available_seats -= 1           # 2. Modify shared state
    confirmed_users.append(user)   # 3. Add to confirmed list
```

### 4. Race Condition
A race condition occurs when concurrent threads execute check-then-act operations simultaneously without synchronization. Because the thread scheduler may switch execution contexts between the read and the decrement, multiple threads read `available_seats = 1` and all proceed to claim the seat, corrupting the shared state.

### 5. Mutex Lock (Mutual Exclusion)
A **Mutex** (`threading.Lock`) is a mutual exclusion binary semaphore. Only the thread that acquires the lock can enter the critical section. Any other thread attempting to acquire the lock is blocked by the operating system until the lock is released:
```python
lock.acquire()
try:
    # --- CRITICAL SECTION ---
    if available_seats > 0:
        available_seats -= 1
        confirm_registration(user)
    else:
        reject_registration(user)
finally:
    lock.release()  # Guaranteed release to prevent deadlocks
```

---

## 📁 3. Simplified 5-File Architecture

```text
EventFlow-OS/
│
├── app.py           # Streamlit application UI, Dashboard, and Mutex Lab
├── database.py      # SQLite WAL persistence, schema, and idempotent seeding
├── services.py      # Mutex-protected registration and cancellation logic
├── mutex_lab.py     # Multi-threaded simulation (Unsafe vs. Safe Mutex comparison)
├── test_cases.py    # 10 automated unit & concurrency tests
├── requirements.txt # Minimal production dependencies (Streamlit, pandas)
└── README.md        # Comprehensive documentation and viva guide
```

---

## 🛠️ 4. Core Application Features

1. **Dashboard:** 4 dynamic KPI metrics:
   - Total Events (10 Active Workshops)
   - Total Registrations
   - Available Seats
   - Total Capacity
2. **Events & Workshops Catalog:** 10 curated academic workshops with real-time seat tracking and registration modal.
3. **Registration System:** Name and email registration, duplicate detection, and full-capacity rejection.
4. **My Registrations:** Lookup bookings by student email and cancel registrations with instant seat recovery.
5. **Mutex & Synchronization Lab:**
   - **Scenario A (Without Mutex):** Controlled race condition demonstration using `threading.Barrier` and simulated context-switch delay to reliably expose overbooking.
   - **Scenario B (With Mutex):** Atomic `threading.Lock()` execution proving mutual exclusion and zero overbooking.
   - **Comparison Table:** Side-by-side analysis of synchronization, critical section protection, and seat consistency.
   - **Interactive Q&A:** Beginner-friendly explanations of all 6 OS concepts.

---

## 🚀 5. Installation & Execution (Windows PowerShell)

### Prerequisites
* Python 3.10 or higher
* Windows PowerShell / Terminal

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Run the Streamlit Dashboard
```powershell
streamlit run app.py
```
*The web dashboard opens automatically in your browser at `http://localhost:8501`.*

### Step 3: Run the 10-Test Automated QA Suite
```powershell
python test_cases.py
```
*Expected Output: `RESULT: ALL 10/10 TESTS PASSED SUCCESSFULLY! (Full Verification)`*

---

## 📊 6. Automated Test Suite Summary (`python test_cases.py`)

| Test ID | Test Scenario | Verified OS / System Behavior | Status |
| :---: | :--- | :--- | :---: |
| **T1** | Event Creation | SQLite schema persistence and capacity initialization | **PASS** |
| **T2** | Successful Registration | Single-thread registration flow and ID generation | **PASS** |
| **T3** | Duplicate Registration Prevention | Rejects repeated registration for the same student and event | **PASS** |
| **T4** | Registration When Seats Full | Strict boundary enforcement when capacity reaches zero | **PASS** |
| **T5** | Seat Count Updates | Verifies `available_seats = capacity - confirmed_count` | **PASS** |
| **T6** | Registration Cancellation | Frees capacity and allows queued or new students to claim seats | **PASS** |
| **T7** | Concurrent Registration Without Mutex | Demonstrates race condition and negative/oversold seat count | **PASS** |
| **T8** | Concurrent Registration With Mutex | Proves `threading.Lock()` prevents overbooking (10 threads, 2 seats) | **PASS** |
| **T9** | Mutex Release After Exception | Confirms `try...finally` releases lock on error, preventing deadlocks | **PASS** |
| **T10** | Database Persistence | Confirms records survive database closing and reconnection | **PASS** |
| **TOTAL** | **10 Automated Tests** | **All Invariants Verified** | **10 / 10 PASS** |

---

## 💬 7. Viva Voce Q&A Quick Reference

### Q1: What problem does Mutex Locking solve in this project?
> **Answer:** *"When multiple registration requests arrive at the same millisecond for an event with only one seat remaining, concurrent threads can read the same remaining-capacity value and both approve bookings. A Mutex (`threading.Lock`) ensures mutual exclusion: only one thread enters the check-and-decrement critical section at any instant, guaranteeing that remaining seats are never oversold."*

### Q2: Why is the `try...finally` block critical when using Mutexes?
> **Answer:** *"If an unexpected exception (e.g., database timeout or validation error) occurs inside the critical section before `lock.release()` is called, the lock would remain permanently held. This causes a deadlock where all subsequent threads hang indefinitely. The `try...finally` construct guarantees that `lock.release()` is always executed, even if the critical section crashes."*

### Q3: What is the difference between a Mutex and a Semaphore?
> **Answer:** *"A Mutex is a mutual exclusion lock with a capacity of 1, owned strictly by the thread that acquired it. A counting semaphore maintains an integer counter allowing up to $N$ permit holders concurrently. For composite check-then-act operations where records must be validated and inserted atomically, a Mutex is required to prevent race conditions."*

### Q4: Why did we need `threading.Barrier` in our simulation lab?
> **Answer:** *"In modern operating systems, CPU threads execute so rapidly that threads spawned in a loop may finish sequentially before the next one starts. `threading.Barrier(num_threads)` halts all threads at a starting gate until every thread is ready, releasing them simultaneously to create true concurrent contention on the shared resource."*
