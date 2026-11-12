"""
app.py - EventFlow OS: Process Synchronization & Mutex Monitor
A clean, professional Streamlit application demonstrating Mutual Exclusion in Operating Systems.
"""

import pandas as pd
import streamlit as st

import database
import mutex_lab
import services

# Page Configuration
st.set_page_config(
    page_title="EventFlow OS — Mutex Synchronization Monitor",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Dark SaaS Theme CSS
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background-color: #0b1120;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Headers & Text */
    h1, h2, h3, h4, h5 {
        color: #f8fafc;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Top Banner */
    .app-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .app-header h1 {
        margin: 0;
        font-size: 1.6rem;
        color: #38bdf8;
    }
    .app-header p {
        margin: 4px 0 0 0;
        color: #94a3b8;
        font-size: 0.95rem;
    }
    
    /* Metric / KPI Cards */
    .kpi-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: left;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .kpi-label {
        font-size: 0.82rem;
        text-transform: uppercase;
        color: #94a3b8;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        color: #38bdf8;
        margin-top: 4px;
    }
    
    /* Event Cards */
    .event-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 16px;
    }
    
    /* Badges */
    .badge-open {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid #059669;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-full {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid #dc2626;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database on first startup
database.init_db()


# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🔒 EventFlow OS")
st.sidebar.markdown("**OS Capstone Monitor**  \n*Process Sync & Mutex Locks*")
st.sidebar.divider()

nav_selection = st.sidebar.radio(
    "Navigation Menu",
    [
        "🏠 Dashboard",
        "📅 Events & Workshops",
        "📝 My Registrations",
        "🔒 Mutex & Synchronization Lab",
        "ℹ️ About Project",
    ],
    index=0,
)

st.sidebar.divider()
st.sidebar.markdown("""
<div style="font-size: 0.8rem; color: #94a3b8; line-height: 1.4;">
<b>Operating System Concepts:</b><br>
• Process Synchronization<br>
• Critical Section Problem<br>
• Mutex (<code>threading.Lock</code>)<br>
• Race Condition Prevention
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# VIEW 1: DASHBOARD
# -----------------------------------------------------------------------------
if nav_selection == "🏠 Dashboard":
    st.markdown("""
    <div class="app-header">
        <div>
            <h1>🏠 EventFlow OS Dashboard</h1>
            <p>Operating Systems Demonstration: Process Synchronization & Mutex Locking</p>
        </div>
        <div style="text-align: right;">
            <span class="badge-open">System Active</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4 Dynamic KPI Cards
    kpis = services.get_dashboard_kpis()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Events</div>
            <div class="kpi-value">{kpis['total_events']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Registrations</div>
            <div class="kpi-value" style="color: #a78bfa;">{kpis['total_registrations']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Available Seats</div>
            <div class="kpi-value" style="color: #34d399;">{kpis['available_seats']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Capacity</div>
            <div class="kpi-value" style="color: #38bdf8;">{kpis['total_capacity']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 Active Workshops Capacity Overview")

    events = services.get_events()
    if events:
        for ev in events:
            booked = ev["confirmed_count"]
            cap = ev["capacity"]
            avail = ev["available_seats"]
            pct = min(1.0, booked / cap) if cap > 0 else 0.0

            badge = f'<span class="badge-open">Seats Available: {avail}</span>' if avail > 0 else '<span class="badge-full">FULL</span>'

            st.markdown(f"""
            <div class="event-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">
                        {ev['event_id']} — {ev['title']}
                    </div>
                    <div>{badge}</div>
                </div>
                <div style="color: #94a3b8; font-size: 0.9rem; margin-top: 6px;">
                    📅 {ev['date']} &nbsp;|&nbsp; 📍 {ev['venue']} &nbsp;|&nbsp; 👥 Capacity: {cap} (Booked: {booked})
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(pct)


# -----------------------------------------------------------------------------
# VIEW 2: EVENTS & WORKSHOPS
# -----------------------------------------------------------------------------
elif nav_selection == "📅 Events & Workshops":
    st.markdown("""
    <div class="app-header">
        <div>
            <h1>📅 Academic Events & Workshops Catalog</h1>
            <p>Browse events, check live seat availability, and register with mutex synchronization</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    search_query = st.text_input("🔍 Search events by title or keyword:", placeholder="e.g. Python, AI, Cloud, Git...")

    events = services.get_events()
    if search_query.strip():
        events = [e for e in events if search_query.lower() in e["title"].lower() or search_query.lower() in e["description"].lower()]

    st.markdown(f"**Showing {len(events)} Workshops**")

    for ev in events:
        eid = ev["event_id"]
        title = ev["title"]
        desc = ev["description"]
        date = ev["date"]
        venue = ev["venue"]
        cap = ev["capacity"]
        avail = ev["available_seats"]

        with st.expander(f"📌 {eid}: {title} (Available Seats: {avail}/{cap})", expanded=(avail > 0 and avail < 5)):
            st.write(desc)
            st.markdown(f"**Date:** `{date}` &nbsp;|&nbsp; **Venue:** `{venue}` &nbsp;|&nbsp; **Max Capacity:** `{cap}` &nbsp;|&nbsp; **Seats Left:** `{avail}`")

            if avail > 0:
                st.markdown("#### Register for this Workshop")
                with st.form(key=f"form_reg_{eid}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        s_name = st.text_input("Full Name", placeholder="e.g. Alice Johnson", key=f"name_{eid}")
                    with c2:
                        s_email = st.text_input("Student Email", placeholder="e.g. alice@student.edu", key=f"email_{eid}")

                    submitted = st.form_submit_button("Confirm Registration 🚀", type="primary")
                    if submitted:
                        res = services.register_student(eid, s_name, s_email)
                        if res["success"]:
                            st.success(f"✅ {res['message']} Ticket ID: `{res['registration_id']}`")
                            st.rerun()
                        elif res["status"] == "DUPLICATE":
                            st.warning(f"⚠️ {res['message']}")
                        elif res["status"] == "FULL":
                            st.error(f"🛑 {res['message']}")
                        else:
                            st.error(f"❌ {res['message']}")
            else:
                st.error("🛑 This workshop has reached maximum capacity. Registrations are closed.")


# -----------------------------------------------------------------------------
# VIEW 3: MY REGISTRATIONS
# -----------------------------------------------------------------------------
elif nav_selection == "📝 My Registrations":
    st.markdown("""
    <div class="app-header">
        <div>
            <h1>📝 My Registered Workshops</h1>
            <p>Look up your active registrations and manage bookings</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    lookup_email = st.text_input("Enter your registered student email address:", placeholder="e.g. alice@student.edu")

    if lookup_email.strip():
        user_regs = services.get_student_registrations(lookup_email.strip())
        if user_regs:
            st.success(f"Found {len(user_regs)} active registration(s) for `{lookup_email}`:")
            for reg in user_regs:
                rid = reg["registration_id"]
                with st.container():
                    st.markdown(f"""
                    <div class="event-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-size: 1.1rem; font-weight: 700; color: #38bdf8;">
                                {reg['event_title']} ({reg['event_id']})
                            </div>
                            <span class="badge-open">CONFIRMED</span>
                        </div>
                        <div style="color: #cbd5e1; font-size: 0.9rem; margin-top: 8px;">
                            👤 <b>Attendee:</b> {reg['student_name']} &nbsp;|&nbsp; 🎫 <b>ID:</b> <code>{rid}</code><br>
                            📅 <b>Event Date:</b> {reg['event_date']} &nbsp;|&nbsp; 📍 <b>Venue:</b> {reg['event_venue']}<br>
                            ⏱️ <b>Registered At:</b> {reg['registration_date']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"Cancel Registration ({rid})", key=f"cancel_{rid}", type="secondary"):
                        cancel_res = services.cancel_registration(rid)
                        if cancel_res["success"]:
                            st.success(f"✅ {cancel_res['message']}")
                            st.rerun()
                        else:
                            st.error(f"❌ {cancel_res['message']}")
        else:
            st.info(f"No active registrations found for `{lookup_email}`. Visit 'Events & Workshops' to register.")
    else:
        st.info("💡 Enter your email address above to view and manage your workshop bookings.")


# -----------------------------------------------------------------------------
# VIEW 4: MUTEX & SYNCHRONIZATION LAB (CORE OS DEMONSTRATION)
# -----------------------------------------------------------------------------
elif nav_selection == "🔒 Mutex & Synchronization Lab":
    st.markdown("""
    <div class="app-header">
        <div>
            <h1>🔒 Mutex & Process Synchronization Lab</h1>
            <p>Interactive Operating Systems Experiment: Race Conditions vs. Mutual Exclusion</p>
        </div>
        <div>
            <span class="badge-open">threading.Lock()</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    In a multi-user environment, several threads can attempt to book a workshop at the exact same moment.
    When only **1 seat remains**, without process synchronization, multiple threads read the same remaining seat value,
    both pass the availability check, and both register, resulting in **overbooking** (a data race).
    """)

    st.markdown("### ⚙️ Simulation Controls")

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    with col_ctrl1:
        num_users = st.slider("Concurrent Registration Threads (Users)", min_value=2, max_value=15, value=3, step=1)
    with col_ctrl2:
        capacity = st.slider("Workshop Seat Capacity", min_value=1, max_value=5, value=1, step=1)
    with col_ctrl3:
        delay = st.slider("Context Switch Delay (seconds)", min_value=0.01, max_value=0.10, value=0.03, step=0.01)

    c_b1, c_b2 = st.columns([1, 1])
    with c_b1:
        run_comp = st.button("⚡ Run Side-by-Side Comparison", type="primary", use_container_width=True)

    if run_comp or "last_comp" in st.session_state:
        if run_comp:
            st.session_state["last_comp"] = mutex_lab.run_side_by_side_comparison(
                num_users=num_users,
                capacity=capacity,
                delay=delay,
            )

        comp = st.session_state["last_comp"]
        unsafe_res = comp["unsafe"]
        safe_res = comp["safe"]

        st.markdown("---")
        st.markdown("### 🔬 Execution Results & Side-by-Side Analysis")

        col_left, col_right = st.columns(2)

        # SCENARIO A: WITHOUT MUTEX
        with col_left:
            st.markdown("#### 🔴 Scenario A: Without Mutex (Unsafe)")
            if unsafe_res["overbooked"]:
                st.error(f"""
                **🛑 RACE CONDITION OBSERVED! OVERBOOKING OCCURRED!**  
                Capacity was **{capacity}**, but **{unsafe_res['confirmed_count']}** users were confirmed!  
                Final Available Seats: **{unsafe_res['final_available_seats']}** (Negative / Corrupt).
                """)
            else:
                st.warning(f"Confirmed: {unsafe_res['confirmed_count']} | Final Seats: {unsafe_res['final_available_seats']}")

            st.write(f"**Attempting Threads:** `{unsafe_res['num_users']}`")
            st.write(f"**Successful Registrations:** `{unsafe_res['confirmed_count']}`")
            st.write(f"**Failed Registrations:** `{unsafe_res['rejected_count']}`")
            st.write(f"**Final Available Seats:** `{unsafe_res['final_available_seats']}`")
            st.write(f"**Execution Duration:** `{unsafe_res['duration_ms']} ms`")

            with st.expander("🔍 View Unsafe Thread Execution Log"):
                df_unsafe = pd.DataFrame(unsafe_res["logs"])
                st.dataframe(df_unsafe, use_container_width=True)

        # SCENARIO B: WITH MUTEX
        with col_right:
            st.markdown("#### 🟢 Scenario B: With Mutex (`threading.Lock()`)")
            if not safe_res["overbooked"] and safe_res["confirmed_count"] <= capacity:
                st.success(f"""
                **✅ MUTUAL EXCLUSION ENFORCED! OVERBOOKING PREVENTED!**  
                Exactly **{safe_res['confirmed_count']}** user(s) granted seats.  
                Final Available Seats: **{safe_res['final_available_seats']}** (Strictly Consistent).
                """)
            else:
                st.error("Anomaly detected.")

            st.write(f"**Attempting Threads:** `{safe_res['num_users']}`")
            st.write(f"**Successful Registrations:** `{safe_res['confirmed_count']}`")
            st.write(f"**Failed Registrations:** `{safe_res['rejected_count']}`")
            st.write(f"**Final Available Seats:** `{safe_res['final_available_seats']}`")
            st.write(f"**Execution Duration:** `{safe_res['duration_ms']} ms`")

            with st.expander("🔍 View Mutex Thread Execution Log"):
                df_safe = pd.DataFrame(safe_res["logs"])
                st.dataframe(df_safe, use_container_width=True)

        st.markdown("---")
        st.markdown("### 📊 Concurrency Comparison Table")
        df_table = pd.DataFrame(comp["table"])
        st.table(df_table)

    st.markdown("---")
    st.markdown("### 📚 Process Synchronization & Mutex Concepts Explained")

    with st.expander("1. What is Process Synchronization?", expanded=True):
        st.write("""
        **Process Synchronization** is the coordination of multiple concurrent processes or threads sharing system resources 
        to ensure orderly execution and maintain consistent data. In our workshop booking system, synchronization ensures 
        that multiple students trying to book the last available seat are processed one at a time.
        """)

    with st.expander("2. What is a Shared Resource?"):
        st.write("""
        A **Shared Resource** is any data, variable, memory structure, or device accessed by more than one thread simultaneously.  
        *In this application:* The shared resource is the **`available_seats`** count for each event, as well as the active registrations table.
        """)

    with st.expander("3. What is a Critical Section?"):
        st.write("""
        A **Critical Section** is the specific block of code that accesses and modifies shared resources.  
        *In this application:* The critical section consists of:
        1. Reading `available_seats`.
        2. Checking if `available_seats > 0`.
        3. Decrementing `available_seats -= 1`.
        4. Inserting the confirmed student registration.
        """)

    with st.expander("4. What is a Race Condition?"):
        st.write("""
        A **Race Condition** occurs when two or more threads access shared data concurrently and the final outcome depends 
        on the non-deterministic order of thread scheduling. Without synchronization, Thread 1 and Thread 2 both read 
        `available_seats = 1` before either can decrement it, leading to **overbooking** (e.g. 2 confirmed for 1 seat).
        """)

    with st.expander("5. What is a Mutex Lock?"):
        st.write("""
        A **Mutex** (*Mutual Exclusion Lock*, implemented in Python as `threading.Lock()`) is a synchronization primitive. 
        It acts like a physical key to a room: only the thread that holds the key can enter the critical section. 
        All other threads must wait until the lock is released.
        """)

    with st.expander("6. How does a Mutex Prevent Race Conditions?"):
        st.markdown("""
        The mutex forces operations inside the critical section to become **atomic** (all-or-nothing):
        ```python
        # Atomic Critical Section with Mutex
        lock.acquire()
        try:
            if available_seats > 0:
                available_seats -= 1
                register_user(user)
            else:
                reject_user(user)
        finally:
            lock.release()  # Always release, even if an error occurs
        ```
        By enforcing that only **one thread** enters this block at any given instant, stale reads and overbooking become impossible.
        """)


# -----------------------------------------------------------------------------
# VIEW 5: ABOUT PROJECT
# -----------------------------------------------------------------------------
elif nav_selection == "ℹ️ About Project":
    st.markdown("""
    <div class="app-header">
        <div>
            <h1>ℹ️ About EventFlow OS</h1>
            <p>Operating Systems Capstone Project: Process Synchronization & Mutex Locking</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ### 🎯 Project Overview
    **EventFlow OS** is an academic software system designed to demonstrate core Operating Systems synchronization principles 
    through a practical workshop seat reservation system.

    ### 📌 Evaluated OS Concepts
    1. **Process Synchronization:** Coordinated multi-thread access to shared system resources without data corruption.
    2. **Critical Section Problem:** Restricting access to seat verification and decrement operations.
    3. **Mutual Exclusion (Mutex):** Enforced using Python's `threading.Lock()` with `try...finally` guarantees.
    4. **Race Condition Prevention:** Proving that concurrent booking requests never exceed event capacity.

    ### 🛠️ Technology Stack
    - **Language:** Python 3.10+
    - **Synchronization:** `threading.Lock`, `threading.Barrier`
    - **Persistence:** SQLite with Write-Ahead Logging (WAL mode)
    - **Web Framework:** Streamlit
    - **Data Handling:** pandas

    ### 📂 Clean 5-File Architecture
    ```text
    EventFlow-OS/
    │
    ├── app.py           # Streamlit Web UI, Dashboard & Mutex Lab
    ├── database.py      # SQLite WAL persistence, schema & idempotent seeding
    ├── services.py      # Mutex-protected registration & cancellation logic
    ├── mutex_lab.py     # Multi-threaded simulation (Unsafe vs Safe Mutex)
    ├── test_cases.py    # 10-test automated verification suite
    ├── requirements.txt # Minimal production dependencies
    └── README.md        # Comprehensive documentation & viva guide
    ```
    """)
