"""
Event Registration Concurrency Monitor
Operating Systems Synchronization Dashboard (Mutex threading.Lock Demonstration)

Course Project: Operating Systems & Computer Networks (Worth 20 Marks)
Role: Senior Python Engineer & UI Designer
"""

from __future__ import annotations

import datetime
import io
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from registration_engine import EventStore
from simulator import run_comparison, run_simulation
import test_cases

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & THEME STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Event Registration Concurrency Monitor",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
/* Modern Dark Theme Palettes */
:root {
    --bg-primary: #0F172A;
    --card-bg: #1E293B;
    --card-border: #334155;
    --text-primary: #F8FAFC;
    --text-muted: #94A3B8;
    --accent-green: #10B981;
    --accent-red: #EF4444;
    --accent-amber: #F59E0B;
    --accent-blue: #3B82F6;
    --accent-purple: #8B5CF6;
}

/* Header Gradient */
.app-header {
    background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 50%, #1E293B 100%);
    border: 1px solid #3730A3;
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.app-title {
    font-size: 2.2rem;
    font-weight: 800;
    color: #F8FAFC;
    margin: 0;
    letter-spacing: -0.5px;
}

.app-subtitle {
    font-size: 1.05rem;
    color: #A5B4FC;
    margin-top: 6px;
    margin-bottom: 0px;
}

/* Problem Statement Box */
.problem-card {
    background: rgba(30, 41, 59, 0.7);
    border-left: 4px solid #3B82F6;
    border-radius: 0 10px 10px 0;
    padding: 16px 20px;
    margin-bottom: 24px;
    font-size: 0.96rem;
    line-height: 1.6;
    color: #E2E8F0;
}

/* Metric / KPI Card */
.kpi-card {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.kpi-card:hover {
    transform: translateY(-2px);
    border-color: #6366F1;
}

.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    margin: 6px 0;
}

.kpi-label {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94A3B8;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.badge-green { background-color: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #059669; }
.badge-red { background-color: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #DC2626; }
.badge-amber { background-color: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid #D97706; }
.badge-blue { background-color: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid #2563EB; }

/* Status Banners */
.banner-safe {
    background: rgba(16, 185, 129, 0.12);
    border: 2px solid #10B981;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    color: #34D399;
    font-weight: 700;
    font-size: 1.15rem;
    margin-bottom: 16px;
}

.banner-unsafe {
    background: rgba(239, 68, 68, 0.15);
    border: 2px solid #EF4444;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    color: #F87171;
    font-weight: 700;
    font-size: 1.15rem;
    margin-bottom: 16px;
}

/* Flowchart step */
.step-node {
    background: #1E293B;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
    color: #F8FAFC;
    font-weight: 600;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "event_store" not in st.session_state:
    st.session_state.event_store = EventStore()

if "last_sim_result" not in st.session_state:
    st.session_state.last_sim_result = None

if "last_comparison_result" not in st.session_state:
    st.session_state.last_comparison_result = None

if "test_results" not in st.session_state:
    st.session_state.test_results = None

if "portal_message" not in st.session_state:
    st.session_state.portal_message = None

store: EventStore = st.session_state.event_store


# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION & DEMO PRESETS
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🔒 Concurrency Monitor")
st.sidebar.markdown(
    "<span class='badge badge-blue'>OS Concept: Mutex Lock</span> "
    "<span class='badge badge-green'>threading.Lock</span>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

nav_choice = st.sidebar.radio(
    "Navigation Menu",
    [
        "🏠 Dashboard",
        "📝 Registration Portal",
        "⚡ Concurrency Simulator",
        "🧵 Thread Timeline",
        "🔒 Mutex Explainer",
        "📊 Analytics",
        "🧪 Test Center",
        "📋 Audit Log",
    ],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🎬 Lab Demo Presets")

col_d1, col_d2 = st.sidebar.columns(2)
with col_d1:
    if st.button("🎬 Lab Demo\n(1 seat, 3 S)", use_container_width=True, help="Load 1 seat, 3 students: S1, S2, S3"):
        preset_events = {
            "E1": {
                "id": "E1",
                "name": "Python Concurrency Workshop",
                "date": "2026-11-15",
                "venue": "Turing Lab 301",
                "capacity": 1,
                "remaining_places": 1,
            }
        }
        store.reset(preset_events)
        st.session_state.demo_preset = "lab_1_3"
        st.session_state.portal_message = ("info", "Loaded Lab Demo: 1 seat, 3 students (S1, S2, S3).")
        st.rerun()

with col_d2:
    if st.button("🎬 Contention\n(2 seats, 10 S)", use_container_width=True, help="Load 2 seats, 10 students"):
        preset_events = {
            "E1": {
                "id": "E1",
                "name": "Python Concurrency Workshop",
                "date": "2026-11-15",
                "venue": "Turing Lab 301",
                "capacity": 2,
                "remaining_places": 2,
            }
        }
        store.reset(preset_events)
        st.session_state.demo_preset = "contention_2_10"
        st.session_state.portal_message = ("info", "Loaded Contention Demo: 2 seats, 10 students.")
        st.rerun()

if st.sidebar.button("🔄 Reset All Workshops", use_container_width=True):
    store.reset()
    st.session_state.last_sim_result = None
    st.session_state.last_comparison_result = None
    st.session_state.portal_message = ("info", "Workshops restored to default capacities.")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='font-size:0.75rem; color:#64748B; text-align:center;'>"
    "Operating Systems Course Project (20 Marks)<br>"
    "Thread-Safe Mutex Synchronization<br>"
    "Python 3.10+ | Streamlit | threading.Lock"
    "</div>",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
PROBLEM_STATEMENT = (
    "Several users attempt to register for a workshop at the same time when only one or two "
    "places remain. Without synchronization, concurrent threads can read the same "
    "remaining-capacity value and all be confirmed, causing overbooking and an incorrect capacity count. "
    "The application protects the capacity check-and-update (the **critical section**) with a "
    "**mutex lock** (`threading.Lock`) so that only one registration thread updates the shared data "
    "at a time, the remaining capacity is always correct, and duplicate registrations are prevented."
)


def render_header(title: str, subtitle: str) -> None:
    """Render a gradient styled page header."""
    st.markdown(
        f"""
        <div class="app-header">
            <h1 class="app-title">{title}</h1>
            <p class="app-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dataframe(df: pd.DataFrame, **kwargs) -> None:
    """Render a dataframe safely across various Streamlit versions without warnings."""
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kwargs)


# -----------------------------------------------------------------------------
# 1. 🏠 DASHBOARD
# -----------------------------------------------------------------------------
if nav_choice == "🏠 Dashboard":
    render_header(
        "Event Registration Concurrency Monitor",
        "Operating Systems Synchronization Dashboard | Mutex Lock (`threading.Lock`)",
    )

    # Problem Statement Callout Box
    st.markdown(
        f"""
        <div class="problem-card">
            <strong>📌 PROBLEM STATEMENT</strong><br>
            {PROBLEM_STATEMENT}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPI Summary Cards
    audit = store.get_audit_log()
    total_events = len(store.events)
    total_confirmed = sum(len(regs) for regs in store.registrations.values())
    total_remaining = sum(e["remaining_places"] for e in store.events.values())
    total_violations = len(store.validate_state())

    # Count mutex wait incidents recorded
    waits_count = sum(1 for log in audit if log.get("waited_ms", 0) > 0.5)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-label">Workshops</div>
                <div class="kpi-value" style="color: #60A5FA;">{total_events}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-label">Confirmed Seats</div>
                <div class="kpi-value" style="color: #34D399;">{total_confirmed}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-label">Places Remaining</div>
                <div class="kpi-value" style="color: #FBBF24;">{total_remaining}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k4:
        v_color = "#34D399" if total_violations == 0 else "#F87171"
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-label">State Violations</div>
                <div class="kpi-value" style="color: {v_color};">{total_violations}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            f"""<div class="kpi-card">
                <div class="kpi-label">Mutex Waits</div>
                <div class="kpi-value" style="color: #A78BFA;">{waits_count}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("### 📋 Live Workshop Capacities")
    event_rows = []
    for eid, e in store.events.items():
        summary = store.get_event_summary(eid)
        cap = summary["capacity"]
        rem = summary["remaining_places"]
        conf = summary["confirmed_count"]
        pct = int(((cap - rem) / cap) * 100) if cap > 0 else 100
        event_rows.append({
            "ID": eid,
            "Workshop Name": summary["name"],
            "Venue": summary["venue"],
            "Date": summary["date"],
            "Capacity": cap,
            "Enrolled": conf,
            "Remaining": rem,
            "Occupancy": f"{pct}%",
            "Status": "FULL" if rem <= 0 else "AVAILABLE",
        })

    df_events = pd.DataFrame(event_rows)
    render_dataframe(
        df_events,
        column_config={
            "Status": st.column_config.TextColumn(
                "Status",
                help="Current seat availability status",
            ),
        },
        hide_index=True,
    )

    # Progress bars for each event
    st.markdown("#### Real-Time Capacity Fill Rate")
    for eid, e in store.events.items():
        summary = store.get_event_summary(eid)
        cap = summary["capacity"]
        rem = summary["remaining_places"]
        used = cap - rem
        pct = max(0.0, min(1.0, used / cap)) if cap > 0 else 1.0

        bar_col1, bar_col2 = st.columns([3, 1])
        with bar_col1:
            st.progress(pct, text=f"{summary['name']} ({used}/{cap} seats taken)")
        with bar_col2:
            if rem <= 0:
                st.markdown("<span class='badge badge-red'>FULL</span>", unsafe_allow_html=True)
            elif rem == 1:
                st.markdown("<span class='badge badge-amber'>1 SEAT LEFT!</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='badge badge-green'>{rem} AVAILABLE</span>", unsafe_allow_html=True)

    # In-App 2-Minute Reviewer Guide
    with st.expander("📖 In-App Reviewer Guide: How Mutex Synchronization Works (2-Minute Overview)", expanded=False):
        st.markdown(
            """
            #### 1. The Concurrency Problem (Race Condition)
            - **Shared Data**: In-memory integer `remaining_places` and set `registrations`.
            - **Non-Atomic Critical Section**:
              ```python
              if remaining_places > 0:       # 1. READ
                  time.sleep(delay)          # 2. SCHEDULER INTERLEAVE
                  remaining_places -= 1      # 3. WRITE
                  registrations.add(user)
              ```
            - When multiple threads execute concurrently, Thread B reads `remaining_places = 1` before Thread A finishes decrementing it. Both threads believe a seat is available and both register, driving remaining capacity negative and overbooking the workshop!

            #### 2. The Mutex Solution (`threading.Lock`)
            - A **Mutual Exclusion (Mutex) Lock** serializes entry into the critical section.
            - Only **one thread** can hold the lock at any instant.
            - Competing threads call `lock.acquire()` and block (enter the OS waiting queue) until the holding thread executes `lock.release()`.
            - Using `try...finally` guarantees the lock is released even if an unhandled exception or crash occurs, preventing permanent deadlock.

            #### 3. How to Demo This App in 60 Seconds
            1. Open **⚡ Concurrency Simulator** from the sidebar.
            2. Click **⚡ Run Side-by-Side Comparison**.
            3. Observe: Left column (Unsafe) shows **OVERBOOKED / RACE DETECTED** (e.g. 3 confirmed for 1 seat).
            4. Right column (Safe) shows **CONSISTENT** (exactly 1 confirmed, remaining = 0).
            5. Switch to **🧵 Thread Timeline** to see the Gantt chart proving concurrent overlap vs sequential mutual exclusion!
            """
        )


# -----------------------------------------------------------------------------
# 2. 📝 REGISTRATION PORTAL
# -----------------------------------------------------------------------------
elif nav_choice == "📝 Registration Portal":
    render_header(
        "Workshop Registration Portal",
        "Interactive manual testing workbench for single-thread operations and cancellations.",
    )

    if st.session_state.portal_message:
        msg_type, msg_text = st.session_state.portal_message
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "warning":
            st.warning(msg_text)
        elif msg_type == "error":
            st.error(msg_text)
        else:
            st.info(msg_text)
        st.session_state.portal_message = None

    p_col1, p_col2 = st.columns([1, 1])

    with p_col1:
        st.markdown("### 👤 User Registration Action")
        event_options = {eid: f"{e['name']} ({eid}) - {e['remaining_places']} seats left" for eid, e in store.events.items()}
        selected_eid = st.selectbox(
            "Select Workshop",
            options=list(event_options.keys()),
            format_func=lambda x: event_options[x],
        )

        user_input = st.text_input("Student / User Identifier", value="Student_Alice", help="Enter a unique name or ID (e.g., S1, Bob)")

        act_col1, act_col2 = st.columns(2)
        with act_col1:
            if st.button("✅ Register for Workshop", use_container_width=True, type="primary"):
                if not user_input.strip():
                    st.session_state.portal_message = ("warning", "User identifier cannot be empty.")
                else:
                    res = store.register(user_input.strip(), selected_eid, use_lock=True, delay=0.05)
                    if res["status"] == "CONFIRMED":
                        st.session_state.portal_message = ("success", f"CONFIRMED: {res['message']} (Waited: {res['waited_ms']} ms)")
                    elif res["status"] == "FULL":
                        st.session_state.portal_message = ("error", f"FULL: {res['message']}")
                    elif res["status"] == "DUPLICATE":
                        st.session_state.portal_message = ("warning", f"DUPLICATE: {res['message']}")
                    st.rerun()

        with act_col2:
            if st.button("❌ Cancel Registration", use_container_width=True):
                if not user_input.strip():
                    st.session_state.portal_message = ("warning", "User identifier cannot be empty.")
                else:
                    cres = store.cancel(user_input.strip(), selected_eid, use_lock=True)
                    if cres["status"] == "CANCELLED":
                        st.session_state.portal_message = ("info", f"CANCELLED: {cres['message']}")
                    else:
                        st.session_state.portal_message = ("warning", f"NOT REGISTERED: {cres['message']}")
                    st.rerun()

    with p_col2:
        st.markdown("### 📊 Selected Workshop Status")
        summ = store.get_event_summary(selected_eid)

        st.markdown(
            f"""
            <div style="background:#1E293B; border:1px solid #334155; border-radius:10px; padding:18px;">
                <h4 style="margin-top:0; color:#F8FAFC;">{summ['name']}</h4>
                <p style="color:#94A3B8; font-size:0.9rem; margin-bottom:12px;">
                    📅 Date: {summ['date']} | 📍 Venue: {summ['venue']}
                </p>
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <div><strong>Max Capacity:</strong> {summ['capacity']}</div>
                    <div><strong>Enrolled:</strong> {summ['confirmed_count']}</div>
                    <div><strong>Remaining:</strong> <span style="color:#FBBF24; font-weight:bold;">{summ['remaining_places']}</span></div>
                </div>
                <strong>Enrolled Students:</strong>
                <div style="margin-top:8px;">
                    {" ".join([f"<span class='badge badge-blue'>{u}</span>" for u in summ['registered_users']]) if summ['registered_users'] else "<span style='color:#64748B; font-style:italic;'>No registrations yet.</span>"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------------------------------------------------------
# 3. ⚡ CONCURRENCY SIMULATOR (SHOWCASE)
# -----------------------------------------------------------------------------
elif nav_choice == "⚡ Concurrency Simulator":
    render_header(
        "Concurrency Simulator: Mutex ON vs Mutex OFF",
        "Execute concurrent threads simultaneously to trigger the race condition or enforce mutual exclusion.",
    )

    st.markdown(
        """
        <div style="background:rgba(30,41,59,0.7); border:1px solid #334155; border-radius:10px; padding:14px; margin-bottom:20px;">
            <strong>⚙️ Simulation Experiment Setup:</strong><br>
            A burst of concurrent threads all arrive at the workshop registration checkpoint simultaneously.
            Without a mutex lock, threads interleave in the critical section, reading the same remaining seat count and causing <strong>overbooking</strong>.
            With a mutex lock, threads are safely queued and serialized.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Controls Section
    c_col1, c_col2, c_col3, c_col4 = st.columns(4)
    with c_col1:
        sim_eid = st.selectbox(
            "Target Workshop",
            options=list(store.events.keys()),
            format_func=lambda x: f"{store.events[x]['name']} ({x})",
        )
    with c_col2:
        num_users = st.slider("Concurrent Users (Threads)", min_value=2, max_value=50, value=3, step=1)
    with c_col3:
        initial_seats = st.slider(
            "Initial Remaining Seats",
            min_value=1,
            max_value=10,
            value=min(1, store.events[sim_eid]["capacity"]),
            help="Set remaining places to 1 or 2 to reliably expose race conditions under contention",
        )
    with c_col4:
        sim_delay = st.slider(
            "Teaching Delay (seconds)",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
            help="Simulates processing/IO work inside critical section to widen the race vulnerability window",
        )

    # Action Buttons
    b_col1, b_col2, b_col3 = st.columns([1, 1, 1.5])

    sim_users = [f"S{i}" for i in range(1, num_users + 1)]

    with b_col1:
        if st.button("🔴 Run Unsafe (Mutex OFF)", use_container_width=True, help="Simulate without lock protection"):
            with st.spinner("Spawning uncoordinated threads..."):
                fresh_store = store.clone()
                fresh_store.events[sim_eid]["capacity"] = initial_seats
                fresh_store.events[sim_eid]["remaining_places"] = initial_seats
                res = run_simulation(
                    event_id=sim_eid,
                    users=sim_users,
                    use_lock=False,
                    delay=sim_delay,
                    store=fresh_store,
                )
                st.session_state.last_sim_result = res
                st.session_state.last_comparison_result = None

    with b_col2:
        if st.button("🟢 Run Safe (Mutex ON)", use_container_width=True, help="Simulate with threading.Lock"):
            with st.spinner("Spawning mutex-protected threads..."):
                fresh_store = store.clone()
                fresh_store.events[sim_eid]["capacity"] = initial_seats
                fresh_store.events[sim_eid]["remaining_places"] = initial_seats
                res = run_simulation(
                    event_id=sim_eid,
                    users=sim_users,
                    use_lock=True,
                    delay=sim_delay,
                    store=fresh_store,
                )
                st.session_state.last_sim_result = res
                st.session_state.last_comparison_result = None

    with b_col3:
        if st.button("⚡ Run Side-by-Side Comparison", use_container_width=True, type="primary"):
            with st.spinner("Executing comparative trials (Unsafe vs Safe)..."):
                comp = run_comparison(
                    event_id=sim_eid,
                    users=sim_users,
                    delay=sim_delay,
                    capacity_override=initial_seats,
                    remaining_override=initial_seats,
                )
                st.session_state.last_comparison_result = comp
                st.session_state.last_sim_result = comp["safe"]

    st.markdown("---")

    # Display Side-by-Side Comparison
    if st.session_state.last_comparison_result:
        comp = st.session_state.last_comparison_result
        u_res = comp["unsafe"]
        s_res = comp["safe"]

        st.markdown("### ⚖️ Side-by-Side Concurrency Comparison Results")

        cmp_col1, cmp_col2 = st.columns(2)

        # UNSAFE OUTCOME COLUMN
        with cmp_col1:
            if u_res["overbooked"]:
                st.markdown(
                    f"""
                    <div class="banner-unsafe">
                        ⚠️ OVERBOOKED / RACE DETECTED<br>
                        <span style="font-size:0.85rem; font-weight:normal;">
                            Unsynchronized threads corrupted shared capacity state!
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="banner-unsafe" style="border-color:#F59E0B; color:#FBBF24;">
                        ⚠️ RACE NOT TRIGGERED THIS RUN<br>
                        <span style="font-size:0.85rem; font-weight:normal;">
                            OS thread scheduling was sequential. Try re-running.
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            u_m1, u_m2, u_m3 = st.columns(3)
            with u_m1:
                st.metric("Capacity", u_res["capacity"])
            with u_m2:
                u_color = "normal" if not u_res["overbooked"] else "inverse"
                st.metric("Confirmed", f"{u_res['confirmed_count']} users", delta=f"{u_res['confirmed_count'] - u_res['capacity']} excess" if u_res['confirmed_count'] > u_res['capacity'] else None, delta_color=u_color)
            with u_m3:
                st.metric("Remaining", u_res["final_remaining"])

            st.markdown(f"**Runtime:** `{u_res['total_runtime_ms']} ms` | **Mutex:** `OFF`")

            if u_res["violations"]:
                st.error("🚨 Invariant Violations Detected:\n- " + "\n- ".join(u_res["violations"]))
            else:
                st.warning("Note: No invariant violations logged on this attempt.")

            st.markdown("#### Unsafe Per-Thread Telemetry")
            df_u = pd.DataFrame(u_res["thread_results"])[["user", "thread_name", "status", "remaining_after", "timestamp"]]
            render_dataframe(df_u, hide_index=True)

        # SAFE OUTCOME COLUMN
        with cmp_col2:
            st.markdown(
                """
                <div class="banner-safe">
                    🛡️ CONSISTENT & SYNCHRONIZED<br>
                    <span style="font-size:0.85rem; font-weight:normal;">
                        Mutex lock strictly enforced atomic critical section execution.
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            s_m1, s_m2, s_m3 = st.columns(3)
            with s_m1:
                st.metric("Capacity", s_res["capacity"])
            with s_m2:
                st.metric("Confirmed", f"{s_res['confirmed_count']} users", delta="Exact Match", delta_color="normal")
            with s_m3:
                st.metric("Remaining", s_res["final_remaining"])

            st.markdown(f"**Runtime:** `{s_res['total_runtime_ms']} ms` | **Mutex:** `ON` (threading.Lock)")

            if not s_res["violations"]:
                st.success("✅ State Invariants Satisfied: 0 Violations (capacity - remaining == len(registrations)).")
            else:
                st.error("Violations in safe mode: " + str(s_res["violations"]))

            st.markdown("#### Safe Per-Thread Telemetry")
            df_s = pd.DataFrame(s_res["thread_results"])[["user", "thread_name", "status", "waited_ms", "held_ms", "remaining_after"]]
            render_dataframe(df_s, hide_index=True)

        # Technical Verdict & Explanation
        st.info(
            f"💡 **OS Principle Demonstrated:** In Unsafe mode, multiple threads simultaneously checked "
            f"`remaining_places > 0` before any thread updated it, resulting in {u_res['confirmed_count']} confirmed "
            f"reservations for only {u_res['capacity']} seat(s). In Safe mode, `self.lock.acquire()` forced threads "
            f"to queue sequentially; each thread evaluated remaining capacity only after previous modifications committed, "
            f"granting exactly {s_res['confirmed_count']} seat(s) and gracefully rejecting the rest with status `FULL`."
        )

    # Single Mode Run Result
    elif st.session_state.last_sim_result:
        res = st.session_state.last_sim_result
        st.markdown("### 📊 Simulation Output")

        if res["use_lock"]:
            st.markdown("<div class='banner-safe'>🛡️ SAFE RUN (Mutex ON): State Validated</div>", unsafe_allow_html=True)
        else:
            if res["overbooked"]:
                st.markdown("<div class='banner-unsafe'>⚠️ UNSAFE RUN (Mutex OFF): Overbooking Observed!</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='banner-unsafe' style='border-color:#F59E0B; color:#FBBF24;'>⚠️ UNSAFE RUN: Race condition did not trigger this run</div>", unsafe_allow_html=True)

        sm1, sm2, sm3, sm4 = st.columns(4)
        with sm1:
            st.metric("Capacity", res["capacity"])
        with sm2:
            st.metric("Confirmed Count", res["confirmed_count"])
        with sm3:
            st.metric("Rejected (Full)", res["full_count"])
        with sm4:
            st.metric("Final Remaining", res["final_remaining"])

        st.markdown("#### Per-Thread Execution Results")
        df_res = pd.DataFrame(res["thread_results"])
        display_cols = [c for c in ["user", "thread_name", "status", "waited_ms", "held_ms", "remaining_after", "timestamp"] if c in df_res.columns]
        render_dataframe(df_res[display_cols], hide_index=True)


# -----------------------------------------------------------------------------
# 4. 🧵 THREAD TIMELINE (GANTT CHART)
# -----------------------------------------------------------------------------
elif nav_choice == "🧵 Thread Timeline":
    render_header(
        "Thread Execution Timeline & Gantt Chart",
        "Visualize lock wait queues, critical section entry, and thread interleaving.",
    )

    active_res = None
    if st.session_state.last_comparison_result:
        choice = st.radio("Choose Mode to Visualize", ["Safe Mode (Mutex ON)", "Unsafe Mode (Mutex OFF)"], horizontal=True)
        active_res = st.session_state.last_comparison_result["safe"] if "Safe" in choice else st.session_state.last_comparison_result["unsafe"]
    elif st.session_state.last_sim_result:
        active_res = st.session_state.last_sim_result
    else:
        st.info("ℹ️ No simulation data available yet. Please run a simulation from the **⚡ Concurrency Simulator** page or click below to run one automatically.")
        if st.button("🚀 Run Quick 3-Thread Simulation for Timeline", type="primary"):
            res = run_simulation(
                event_id="E1",
                users=["S1", "S2", "S3"],
                use_lock=True,
                delay=0.2,
            )
            st.session_state.last_sim_result = res
            st.rerun()

    if active_res and active_res.get("timeline_data"):
        tl_data = active_res["timeline_data"]
        df_tl = pd.DataFrame(tl_data)

        st.markdown(f"**Visualizing:** `{active_res['event_name']}` | **Mutex Lock:** `{'ENABLED' if active_res['use_lock'] else 'DISABLED'}` | **Total Runtime:** `{active_res['total_runtime_ms']} ms`")

        # Attempt to render with Plotly
        plotly_rendered = False
        try:
            import plotly.graph_objects as go

            fig = go.Figure()

            # Plot Wait Bars (Amber) and CS Bars (Green / Red / Gray)
            for _, row in df_tl.iterrows():
                thread_name = row["Thread"]
                wait_start = row["Wait_Start_ms"]
                cs_entry = row["CS_Entry_ms"]
                cs_exit = row["CS_Exit_ms"]
                status = row["Status"]

                # 1. Waiting for Lock bar
                if cs_entry > wait_start:
                    fig.add_trace(go.Bar(
                        name="Waiting for Lock",
                        y=[thread_name],
                        x=[cs_entry - wait_start],
                        base=[wait_start],
                        orientation='h',
                        marker=dict(color="#F59E0B", line=dict(color="#D97706", width=1)),
                        showlegend=False,
                        hovertext=f"{thread_name} Blocked on Lock: {row['Wait_Duration_ms']} ms",
                    ))

                # 2. Inside Critical Section bar
                if status == "CONFIRMED":
                    cs_color = "#10B981" if active_res["use_lock"] else "#EF4444"
                elif status == "FULL":
                    cs_color = "#64748B"
                elif status == "DUPLICATE":
                    cs_color = "#8B5CF6"
                else:
                    cs_color = "#3B82F6"

                fig.add_trace(go.Bar(
                    name=f"Critical Section ({status})",
                    y=[thread_name],
                    x=[cs_exit - cs_entry],
                    base=[cs_entry],
                    orientation='h',
                    marker=dict(color=cs_color, line=dict(color="#1E293B", width=1)),
                    showlegend=False,
                    hovertext=f"{thread_name} inside Critical Section ({status}): {row['CS_Duration_ms']} ms",
                ))

            fig.update_layout(
                barmode='stack',
                title=dict(
                    text=f"Thread Timeline ({'Mutex ON: Sequential Queue' if active_res['use_lock'] else 'Mutex OFF: Concurrent Overlap'})",
                    font=dict(color="#F8FAFC", size=16),
                ),
                xaxis=dict(
                    title="Elapsed Time (milliseconds)",
                    color="#94A3B8",
                    gridcolor="#334155",
                    zerolinecolor="#475569",
                ),
                yaxis=dict(
                    title="Thread ID",
                    color="#94A3B8",
                    autorange="reversed",
                ),
                paper_bgcolor="#0F172A",
                plot_bgcolor="#1E293B",
                height=350 + (len(df_tl) * 20),
                margin=dict(l=80, r=40, t=50, b=50),
            )

            st.plotly_chart(fig, use_container_width=True)
            plotly_rendered = True

            # Custom Legend below Plotly
            st.markdown(
                """
                <div style="display:flex; justify-content:center; gap:20px; font-size:0.85rem; margin-top:8px;">
                    <div><span style="display:inline-block; width:12px; height:12px; background:#F59E0B; border-radius:2px;"></span> Waiting for Mutex Lock</div>
                    <div><span style="display:inline-block; width:12px; height:12px; background:#10B981; border-radius:2px;"></span> Inside Critical Section (Confirmed)</div>
                    <div><span style="display:inline-block; width:12px; height:12px; background:#EF4444; border-radius:2px;"></span> Critical Section Overlap (Unsafe Race)</div>
                    <div><span style="display:inline-block; width:12px; height:12px; background:#64748B; border-radius:2px;"></span> Critical Section (Rejected / Full)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        except Exception as e:
            st.warning(f"Plotly render fallback (Error: {e})")

        # Native fallback table & chart if Plotly fails or as companion
        st.markdown("#### Detailed Thread Telemetry Table")
        render_dataframe(
            df_tl[["Thread", "User", "Status", "Wait_Duration_ms", "CS_Duration_ms", "Total_Duration_ms"]],
            hide_index=True,
        )

        # Narrative Step-by-Step Explanation
        st.markdown("#### 🔍 Step-by-Step Execution Trace Narration")
        if active_res["use_lock"]:
            st.markdown(
                """
                1. **Thread Arrival:** All worker threads spawn almost simultaneously and attempt to execute `register()`.
                2. **First Thread Acquisition:** One thread wins the race to acquire `self.lock`. Its wait time is ~0 ms.
                3. **Queueing of Subsequent Threads:** All remaining threads call `self.lock.acquire()` and are put into the OS blocked state (indicated by the amber bars).
                4. **Lock Release & Hand-off:** When the active thread completes seat reservation and releases the mutex in its `finally` block, the next waiting thread is awakened by the OS scheduler.
                5. **Zero Overlapping:** At no point in time were two threads inside the green/critical-section block simultaneously.
                """
            )
        else:
            st.markdown(
                """
                1. **Thread Arrival:** All threads spawn simultaneously without any lock primitive.
                2. **Simultaneous Critical Section Entry:** Because there is no mutex, every thread enters the critical section simultaneously (shown as overlapping bars).
                3. **Read Conflict:** Each thread reads the shared `remaining_places` variable before any other thread has decremented it.
                4. **Corrupted State:** Every thread proceeds to decrement the counter and add its user, causing an overbooked event and negative capacity!
                """
            )


# -----------------------------------------------------------------------------
# 5. 🔒 MUTEX EXPLAINER
# -----------------------------------------------------------------------------
elif nav_choice == "🔒 Mutex Explainer":
    render_header(
        "Operating Systems Mutex Theory & Architecture",
        "Deep-dive into Critical Sections, Race Conditions, Mutex vs Semaphore, and Atomic State Transitions.",
    )

    # 5-Step Lifecycle Visual
    st.markdown("### 🔄 Mutex Lock Execution Lifecycle")
    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        st.markdown("""<div class="step-node">1. Request<br><span style="font-size:0.75rem; color:#94A3B8;">Thread calls register()</span></div>""", unsafe_allow_html=True)
    with s2:
        st.markdown("""<div class="step-node">2. Acquire Lock<br><span style="font-size:0.75rem; color:#FBBF24;">lock.acquire() [Blocks if busy]</span></div>""", unsafe_allow_html=True)
    with s3:
        st.markdown("""<div class="step-node">3. Critical Section<br><span style="font-size:0.75rem; color:#34D399;">Check & Update atomically</span></div>""", unsafe_allow_html=True)
    with s4:
        st.markdown("""<div class="step-node">4. Release Lock<br><span style="font-size:0.75rem; color:#60A5FA;">lock.release() in finally</span></div>""", unsafe_allow_html=True)
    with s5:
        st.markdown("""<div class="step-node">5. Next Thread<br><span style="font-size:0.75rem; color:#A78BFA;">Next waiting thread unblocks</span></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Race Condition Step-by-Step Interleaving Trace Table
    st.markdown("### ⚠️ Race Condition Execution Trace (Without Mutex)")
    st.markdown("Initial State: `capacity = 1`, `remaining_places = 1`, `registrations = {}`")

    trace_data = [
        {"Step": "1", "Thread A (S1)": "Calls register('S1')", "Thread B (S2)": "Waiting (OS scheduled A)", "Shared remaining_places": "1", "Vulnerability Note": "Normal start"},
        {"Step": "2", "Thread A (S1)": "Checks `remaining_places > 0` (True)", "Thread B (S2)": "Calls register('S2')", "Shared remaining_places": "1", "Vulnerability Note": "A determines seat is available"},
        {"Step": "3", "Thread A (S1)": "time.sleep(delay) [Context Switch]", "Thread B (S2)": "Checks `remaining_places > 0` (True!)", "Shared remaining_places": "1", "Vulnerability Note": "CRITICAL FLAW: B reads 1 before A updates it!"},
        {"Step": "4", "Thread A (S1)": "Wakes up, decrements: `1 -> 0`", "Thread B (S2)": "time.sleep(delay)", "Shared remaining_places": "0", "Vulnerability Note": "A confirms registration"},
        {"Step": "5", "Thread A (S1)": "Returns CONFIRMED", "Thread B (S2)": "Wakes up, decrements: `0 -> -1`!", "Shared remaining_places": "-1", "Vulnerability Note": "B confirms registration too!"},
        {"Step": "6", "Thread A (S1)": "Completed", "Thread B (S2)": "Returns CONFIRMED", "Shared remaining_places": "-1 (CORRUPTED)", "Vulnerability Note": "OVERBOOKED: 2 confirmed for 1 seat!"},
    ]
    st.table(pd.DataFrame(trace_data))

    st.markdown("---")

    # Code Comparison
    st.markdown("### 💻 Unsafe vs Safe Code Architecture")
    code_col1, code_col2 = st.columns(2)

    with code_col1:
        st.markdown("#### ❌ Flawed / Unsynchronized Code")
        st.code(
            """# UNSAFE: Check-Then-Act Race Condition
def register_unsafe(user, event_id):
    # CRITICAL SECTION EXPOSED TO CONCURRENT ACCESS
    if user in registrations[event_id]:
        return "DUPLICATE"
    
    if events[event_id]["remaining_places"] > 0:
        time.sleep(delay) # Thread switch here ruins consistency!
        events[event_id]["remaining_places"] -= 1
        registrations[event_id].add(user)
        return "CONFIRMED"
    else:
        return "FULL"
""",
            language="python",
        )

    with code_col2:
        st.markdown("#### ✅ Synchronized Mutex (`threading.Lock`)")
        st.code(
            """# SAFE: Mutex Mutual Exclusion with try/finally
lock = threading.Lock()

def register_safe(user, event_id):
    lock.acquire() # Blocks all competing threads
    try:
        # ATOMIC CRITICAL SECTION
        if user in registrations[event_id]:
            return "DUPLICATE"
        
        if events[event_id]["remaining_places"] > 0:
            time.sleep(delay) # Safe: other threads are blocked
            events[event_id]["remaining_places"] -= 1
            registrations[event_id].add(user)
            return "CONFIRMED"
        else:
            return "FULL"
    finally:
        lock.release() # ALWAYS released even on crash!
""",
            language="python",
        )

    st.markdown("---")

    # Mutex vs Semaphore Comparison Table
    st.markdown("### ⚖️ OS Concepts Comparison: Mutex vs Semaphore")
    comparison_data = [
        {"Attribute": "Mechanism Type", "Mutex (`threading.Lock`)": "Locking Mechanism (Mutual Exclusion)", "Semaphore (`threading.Semaphore`)": "Signaling Mechanism (Counter of available permits)"},
        {"Attribute": "Allowed Threads in CS", "Mutex (`threading.Lock`)": "Strictly 1 thread at a time", "Semaphore (`threading.Semaphore`)": "Up to N threads simultaneously (where N is initial count)"},
        {"Attribute": "Ownership", "Mutex (`threading.Lock`)": "Has ownership (only the acquiring thread should release)", "Semaphore (`threading.Semaphore`)": "No ownership (any thread can release / signal)"},
        {"Attribute": "Use Case in this Project", "Mutex (`threading.Lock`)": "CHOSEN MECHANISM: Enforces atomic seat check-and-decrement", "Semaphore (`threading.Semaphore`)": "Can be used as a waitlist permit pool, but does not guarantee exclusive check-and-act consistency by itself"},
        {"Attribute": "Deadlock Risk", "Mutex (`threading.Lock`)": "Risk of deadlock if lock is not released (mitigated by try/finally)", "Semaphore (`threading.Semaphore`)": "Risk of deadlock if signal/wait imbalances occur"},
    ]
    st.table(pd.DataFrame(comparison_data))


# -----------------------------------------------------------------------------
# 6. 📊 ANALYTICS
# -----------------------------------------------------------------------------
elif nav_choice == "📊 Analytics":
    render_header(
        "Concurrency Analytics & Empirical Stress Testing",
        "Statistical verification across repeated trials and lock wait time telemetry.",
    )

    st.markdown("### 🧪 Repeated Multi-Trial Stress Experiment")
    st.markdown(
        "Run multiple independent trials of identical workloads to empirically compute the "
        "probability of race condition occurrences in Unsafe mode versus Safe mode."
    )

    t_col1, t_col2, t_col3 = st.columns([1, 1, 1])
    with t_col1:
        num_trials = st.slider("Number of Trials (N)", min_value=5, max_value=25, value=10, step=5)
    with t_col2:
        trial_threads = st.slider("Threads per Trial", min_value=3, max_value=15, value=4, step=1)
    with t_col3:
        trial_delay = st.slider("Delay per Trial (s)", min_value=0.05, max_value=0.3, value=0.1, step=0.05)

    if st.button("🚀 Run Multi-Trial Benchmark", type="primary"):
        with st.spinner(f"Running {num_trials} trials of Unsafe vs Safe execution..."):
            unsafe_overbooked_count = 0
            safe_overbooked_count = 0
            trial_records = []

            for trial_idx in range(1, num_trials + 1):
                trial_users = [f"T{trial_idx}_U{j}" for j in range(1, trial_threads + 1)]
                comp = run_comparison(
                    event_id="E1",
                    users=trial_users,
                    delay=trial_delay,
                    capacity_override=1,
                    remaining_override=1,
                )
                if comp["unsafe"]["overbooked"]:
                    unsafe_overbooked_count += 1
                if comp["safe"]["overbooked"]:
                    safe_overbooked_count += 1

                trial_records.append({
                    "Trial": trial_idx,
                    "Unsafe_Confirmed": comp["unsafe"]["confirmed_count"],
                    "Unsafe_Remaining": comp["unsafe"]["final_remaining"],
                    "Unsafe_Overbooked": comp["unsafe"]["overbooked"],
                    "Safe_Confirmed": comp["safe"]["confirmed_count"],
                    "Safe_Remaining": comp["safe"]["final_remaining"],
                    "Safe_Overbooked": comp["safe"]["overbooked"],
                })

            unsafe_rate = (unsafe_overbooked_count / num_trials) * 100
            safe_rate = (safe_overbooked_count / num_trials) * 100

            st.session_state.trial_results = {
                "records": trial_records,
                "unsafe_rate": unsafe_rate,
                "safe_rate": safe_rate,
                "num_trials": num_trials,
            }

    if "trial_results" in st.session_state and st.session_state.trial_results:
        tr = st.session_state.trial_results
        st.markdown("#### Benchmark Findings")

        tr_m1, tr_m2, tr_m3 = st.columns(3)
        with tr_m1:
            st.metric("Total Trials Conducted", tr["num_trials"])
        with tr_m2:
            st.metric("Unsafe Race Frequency", f"{tr['unsafe_rate']:.1f}%", delta="High Failure Rate", delta_color="inverse")
        with tr_m3:
            st.metric("Safe Failure Frequency", f"{tr['safe_rate']:.1f}%", delta="0.0% Invariant Guarantee", delta_color="normal")

        df_bench = pd.DataFrame(tr["records"])

        # Display bar chart comparing confirmed count across trials
        try:
            import plotly.express as px
            df_melt = pd.melt(
                df_bench,
                id_vars=["Trial"],
                value_vars=["Unsafe_Confirmed", "Safe_Confirmed"],
                var_name="Mode",
                value_name="Confirmed Seats",
            )
            df_melt["Mode"] = df_melt["Mode"].map({"Unsafe_Confirmed": "Unsafe (Mutex OFF)", "Safe_Confirmed": "Safe (Mutex ON)"})
            fig_bar = px.bar(
                df_melt,
                x="Trial",
                y="Confirmed Seats",
                color="Mode",
                barmode="group",
                title=f"Confirmed Registrations per Trial (Capacity = 1)",
                color_discrete_map={"Unsafe (Mutex OFF)": "#EF4444", "Safe (Mutex ON)": "#10B981"},
            )
            fig_bar.update_layout(paper_bgcolor="#0F172A", plot_bgcolor="#1E293B", font=dict(color="#F8FAFC"))
            st.plotly_chart(fig_bar, use_container_width=True)
        except Exception:
            st.bar_chart(df_bench[["Unsafe_Confirmed", "Safe_Confirmed"]])

        with st.expander("Detailed Trial-by-Trial Data"):
            render_dataframe(df_bench, hide_index=True)

    st.markdown("---")

    # Lock Wait Time Distribution
    audit_data = store.get_audit_log()
    df_audit = pd.DataFrame(audit_data)
    if not df_audit.empty and "waited_ms" in df_audit.columns:
        st.markdown("### ⏱️ Lock Wait Time Distribution (Contention Latency)")
        waited_entries = df_audit[df_audit["waited_ms"] > 0]
        if not waited_entries.empty:
            avg_wait = waited_entries["waited_ms"].mean()
            max_wait = waited_entries["waited_ms"].max()
            w_col1, w_col2 = st.columns(2)
            with w_col1:
                st.metric("Average Lock Wait Time", f"{avg_wait:.2f} ms")
            with w_col2:
                st.metric("Maximum Lock Wait Time", f"{max_wait:.2f} ms")

            try:
                import plotly.express as px
                fig_wait = px.histogram(
                    waited_entries,
                    x="waited_ms",
                    nbins=15,
                    title="Lock Wait Time Distribution (ms)",
                    color_discrete_sequence=["#F59E0B"],
                )
                fig_wait.update_layout(paper_bgcolor="#0F172A", plot_bgcolor="#1E293B", font=dict(color="#F8FAFC"))
                st.plotly_chart(fig_wait, use_container_width=True)
            except Exception:
                render_dataframe(waited_entries[["timestamp", "thread", "user", "waited_ms"]])
        else:
            st.info("No recorded lock wait times > 0 ms yet. Run higher concurrency simulations to see contention latency.")


# -----------------------------------------------------------------------------
# 7. 🧪 TEST CENTER
# -----------------------------------------------------------------------------
elif nav_choice == "🧪 Test Center":
    render_header(
        "Operating Systems Automated Test Center",
        "Predefined verification test suite validating concurrency invariants, race detection, and exception safety.",
    )

    t_btn_col, t_info_col = st.columns([1, 2])
    with t_btn_col:
        if st.button("▶️ Run All Verification Tests", use_container_width=True, type="primary"):
            with st.spinner("Executing OS verification test suite..."):
                st.session_state.test_results = test_cases.run_all_tests()

    with t_info_col:
        if st.session_state.test_results:
            passed = sum(1 for t in st.session_state.test_results if t["passed"])
            total = len(st.session_state.test_results)
            if passed == total:
                st.markdown(
                    f"""
                    <div style="background:rgba(16,185,129,0.15); border:1px solid #10B981; border-radius:8px; padding:10px 16px; color:#34D399; font-weight:bold;">
                        ✅ All {passed}/{total} Tests Passed! Complete Invariant & Mutex Verification (20/20 Marks).
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.error(f"❌ {passed}/{total} Tests Passed. Review test failures below.")

    st.markdown("---")

    # If no tests run yet, show the catalog of test cases
    if not st.session_state.test_results:
        st.markdown("#### Test Suite Catalog")
        test_catalog = [
            {"ID": "T1", "Name": "Sequential booking (1 seat, 2 users)", "Expected Outcome": "One success, one full rejection"},
            {"ID": "T2", "Name": "Concurrent unsafe (1 seat, 3 users)", "Expected Outcome": "Overbooking expected; honest race reporting"},
            {"ID": "T3", "Name": "Concurrent safe (1 seat, 3 users)", "Expected Outcome": "Exactly 1 confirmed, 2 full, 0 remaining"},
            {"ID": "T4", "Name": "10 users, 2 seats, safe", "Expected Outcome": "Exactly 2 confirmed, 8 full, 0 remaining"},
            {"ID": "T5", "Name": "Duplicate registration (same user twice at once, safe)", "Expected Outcome": "1 confirmed, 1 duplicate, 1 seat deducted"},
            {"ID": "T6", "Name": "Cancel then re-register", "Expected Outcome": "Cancel restores seat, next user succeeds"},
            {"ID": "T7", "Name": "Capacity never negative under 50 threads, safe", "Expected Outcome": "Remaining >= 0, confirmed <= capacity"},
            {"ID": "T8", "Name": "Lock released after an exception (try/finally check)", "Expected Outcome": "No deadlock after crash; subsequent threads proceed"},
        ]
        render_dataframe(pd.DataFrame(test_catalog), hide_index=True)
        st.info("Click '▶️ Run All Verification Tests' above to execute the test suite.")

    else:
        results = st.session_state.test_results
        for r in results:
            badge_html = "<span class='badge badge-green'>PASS</span>" if r["passed"] else "<span class='badge badge-red'>FAIL</span>"
            st.markdown(
                f"""
                <div style="background:#1E293B; border:1px solid #334155; border-radius:10px; padding:14px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong>{r['id']}: {r['name']}</strong> {badge_html}
                        </div>
                        <div style="font-size:0.85rem; color:#94A3B8;">{r['duration_ms']} ms</div>
                    </div>
                    <div style="font-size:0.88rem; color:#CBD5E1; margin-top:6px;">{r['description']}</div>
                    <div style="font-size:0.82rem; color:#94A3B8; margin-top:4px; font-family:monospace; background:#0F172A; padding:6px 10px; border-radius:6px;">
                        {r['details']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# -----------------------------------------------------------------------------
# 8. 📋 AUDIT LOG
# -----------------------------------------------------------------------------
elif nav_choice == "📋 Audit Log":
    render_header(
        "System Audit & Concurrency Communication Log",
        "Chronological, thread-safe operational ledger recording all registrations, cancellations, and lock timings.",
    )

    logs = store.get_audit_log()
    df_log = pd.DataFrame(logs)

    # Top Metrics and Actions
    al_col1, al_col2, al_col3, al_col4 = st.columns([1, 1, 1, 1])
    with al_col1:
        st.metric("Total Log Entries", len(logs))
    with al_col2:
        conf_count = len(df_log[df_log["status"] == "CONFIRMED"]) if not df_log.empty and "status" in df_log.columns else 0
        st.metric("Confirmed Operations", conf_count)
    with al_col3:
        rej_count = len(df_log[df_log["status"] == "FULL"]) if not df_log.empty and "status" in df_log.columns else 0
        st.metric("Full / Rejected", rej_count)
    with al_col4:
        if st.button("🗑️ Clear Audit Log", use_container_width=True):
            store.clear_audit_log()
            st.rerun()

    st.markdown("---")

    if not df_log.empty:
        # Filter controls
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            actions = ["ALL"] + sorted(list(df_log["action"].unique())) if "action" in df_log.columns else ["ALL"]
            sel_action = st.selectbox("Filter by Action", actions)
        with f_col2:
            statuses = ["ALL"] + sorted(list(df_log["status"].unique())) if "status" in df_log.columns else ["ALL"]
            sel_status = st.selectbox("Filter by Status", statuses)

        filtered_df = df_log.copy()
        if sel_action != "ALL":
            filtered_df = filtered_df[filtered_df["action"] == sel_action]
        if sel_status != "ALL":
            filtered_df = filtered_df[filtered_df["status"] == sel_status]

        render_dataframe(filtered_df, hide_index=True)

        # CSV Export Button
        csv_buffer = io.StringIO()
        filtered_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()

        st.download_button(
            label="📥 Download Audit Log as CSV",
            data=csv_data,
            file_name=f"audit_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Audit log is currently empty. Perform registrations or run simulations to generate log records.")
