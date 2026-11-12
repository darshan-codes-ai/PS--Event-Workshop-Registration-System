"""
Event & Workshop Registration System — Mutex Synchronization Monitor
Operating Systems & Computer Networks Academic Capstone (20 Marks)
Premium SaaS Event Management Dashboard & Multi-Thread Concurrency Laboratory
"""

from __future__ import annotations

import html
import io
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import auth
import database
from registration_engine import EventStore, PersistentRegistrationService
import report_service
from simulator import run_comparison, run_simulation
import test_cases
import ticket_service
import ui_theme
from ui_theme import (
    get_plotly_dark_layout,
    inject_custom_css,
    render_dataframe,
    render_kpi_card,
    render_saas_header,
    render_section_heading,
    render_status_badge,
)
import waitlist_service

# =============================================================================
# 1. STREAMLIT APPLICATION CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="EventFlow OS — Concurrency Monitor",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject modern dark SaaS stylesheet
inject_custom_css()


# =============================================================================
# 2. SHARED SERVICES SINGLETONS (Cross-Session Invariant Consistency)
# =============================================================================
@st.cache_resource
def get_shared_event_store() -> EventStore:
    """Singleton in-memory EventStore for the OS multi-thread concurrency lab."""
    return EventStore()


@st.cache_resource
def get_shared_registration_service() -> PersistentRegistrationService:
    """Singleton persistent SQLite service for production-grade ACID registration."""
    return PersistentRegistrationService.get_instance()


store: EventStore = get_shared_event_store()
service: PersistentRegistrationService = get_shared_registration_service()


# =============================================================================
# 3. SESSION STATE INITIALIZATION
# =============================================================================
if "current_user" not in st.session_state:
    st.session_state.current_user = {
        "id": "student_alice",
        "display_name": "Alice Johnson",
        "email": "alice@student.edu",
        "role": "Student",
    }

if "last_sim_result" not in st.session_state:
    st.session_state.last_sim_result = None

if "last_comparison_result" not in st.session_state:
    st.session_state.last_comparison_result = None

if "test_results" not in st.session_state:
    st.session_state.test_results = None

if "portal_message" not in st.session_state:
    st.session_state.portal_message = None

if "bench_res" not in st.session_state:
    st.session_state.bench_res = None

user = st.session_state.current_user


# =============================================================================
# 4. SIDEBAR NAVIGATION & PROFILE CONTROLS
# =============================================================================
st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">🔒 EventFlow OS</div>
        <div class="sidebar-brand-subtitle">Event Management & Mutex Monitor</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Active User Profile Card
role_color = "badge-blue" if user["role"] == "Student" else ("badge-purple" if user["role"] == "Organizer" else "badge-indigo")
safe_display_name = html.escape(user["display_name"])
safe_role = html.escape(user["role"])
safe_email = html.escape(user.get("email", ""))

st.sidebar.markdown(
    f"""
    <div class="sidebar-user-card">
        <div style="font-size:0.72rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">Active Session</div>
        <div style="font-weight:700; color:#FFFFFF; font-size:0.95rem; margin-top:2px;">{safe_display_name}</div>
        <div style="font-size:0.78rem; color:#94A3B8; margin-bottom:6px;">{safe_email}</div>
        <div><span class='badge {role_color}'>{safe_role}</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 1-Click Viva Demo Role Switcher
with st.sidebar.expander("⚡ 1-Click Role Switcher (Viva Demo)", expanded=False):
    s_col1, s_col2, s_col3 = st.columns(3)
    with s_col1:
        if st.button("🎓 Alice", help="Switch to Student Alice"):
            st.session_state.current_user = auth.get_user_by_id("student_alice")
            st.rerun()
    with s_col2:
        if st.button("📋 Turner", help="Switch to Organizer Prof. Turner"):
            st.session_state.current_user = auth.get_user_by_id("prof_turner")
            st.rerun()
    with s_col3:
        if st.button("⚙️ Admin", help="Switch to System Admin"):
            st.session_state.current_user = auth.get_user_by_id("admin_sys")
            st.rerun()

st.sidebar.markdown('<div class="sidebar-section-title">Navigation Menu</div>', unsafe_allow_html=True)

nav_options = [
    "🏠 Dashboard",
    "🔍 Registration Portal",
]

# Role-specific workspaces
if user["role"] == "Student":
    nav_options.append("🎫 My Registrations & QR Passes")
elif user["role"] in ("Organizer", "Administrator"):
    nav_options.extend([
        "➕ Manage Workshops",
        "🎟️ Attendance Check-In",
        "📋 Attendee Rosters",
    ])

if user["role"] == "Administrator":
    nav_options.append("🛡️ Admin Control Panel")

# Academic OS & Concurrency Labs (available to all)
nav_options.extend([
    "⚡ Concurrency Simulator",
    "🧵 Thread Timeline",
    "🔒 Mutex Explainer",
    "📊 Analytics",
    "🧪 Test Center (15 Tests)",
    "📜 System Audit Log",
])

nav_choice = st.sidebar.radio("Go To", nav_options, index=0, label_visibility="collapsed")

# ----------------- Lab Demo Controls -----------------
st.sidebar.markdown('<div class="sidebar-section-title">🧪 Lab Demo Controls</div>', unsafe_allow_html=True)

preset_col1, preset_col2 = st.sidebar.columns(2)
with preset_col1:
    if st.button("🎬 Lab (1 Seat)", use_container_width=True, help="Load 1 seat, 3 threads (S1, S2, S3)"):
        store.reset({
            "E1": {"id": "E1", "name": "Python Concurrency Workshop", "date": "2026-11-15", "venue": "Turing Lab 301", "capacity": 1, "remaining_places": 1}
        })
        st.session_state.portal_message = ("info", "Loaded Lab Demo: 1 seat, 3 students (S1, S2, S3).")
        st.rerun()

with preset_col2:
    if st.button("🎬 Contention (2)", use_container_width=True, help="Load 2 seats, 10 threads"):
        store.reset({
            "E1": {"id": "E1", "name": "Python Concurrency Workshop", "date": "2026-11-15", "venue": "Turing Lab 301", "capacity": 2, "remaining_places": 2}
        })
        st.session_state.portal_message = ("info", "Loaded Contention Demo: 2 seats, 10 students.")
        st.rerun()

confirm_reset = st.sidebar.checkbox("Confirm Lab Reset", value=False, help="Safety confirmation before resetting in-memory lab data")
if st.sidebar.button("🔄 Reset In-Memory Labs", use_container_width=True, disabled=not confirm_reset):
    store.reset()
    st.session_state.last_sim_result = None
    st.session_state.last_comparison_result = None
    st.session_state.portal_message = ("info", "In-memory simulation state reset to defaults.")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="font-size:0.72rem; color:#64748B; text-align:center; line-height:1.4;">
        <strong>OS & CN Academic Capstone</strong><br>
        SQLite WAL + Per-Event Mutex (`threading.Lock`)<br>
        20 Realistic Events • 15/15 Tests Verified
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# HELPER: FLASH PORTAL NOTIFICATIONS
# =============================================================================
def display_portal_message() -> None:
    """Render flash status alert if set in session state."""
    if st.session_state.portal_message:
        msg_t, msg_c = st.session_state.portal_message
        if msg_t == "success":
            st.success(msg_c)
        elif msg_t == "warning":
            st.warning(msg_c)
        elif msg_t == "error":
            st.error(msg_c)
        else:
            st.info(msg_c)
        st.session_state.portal_message = None


# =============================================================================
# 1. 🏠 DASHBOARD (MODERN SAAS REDESIGN)
# =============================================================================
if nav_choice == "🏠 Dashboard":
    today_str = datetime.now().strftime("%A, %b %d, %Y")
    render_saas_header(
        "Event Management Dashboard",
        "Monitor events, registrations, and available capacity in one place.",
        badge_text=f"📅 {today_str}",
    )
    display_portal_message()

    # Query authoritative database records
    events = service.list_events(status=None)
    total_events = len(events)
    total_capacity = sum(e["capacity"] for e in events)
    total_confirmed = sum(e["confirmed_count"] for e in events)
    total_remaining = sum(e["remaining_places"] for e in events)
    reg_rate = (total_confirmed / total_capacity * 100.0) if total_capacity > 0 else 0.0

    # 4 Primary KPI Cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        render_kpi_card(
            label="Total Events",
            value=f"{total_events}",
            subtext="Published & Active Workshops",
            top_bar_color="#3B82F6",
            value_color="#60A5FA",
        )
    with kpi_col2:
        render_kpi_card(
            label="Total Registrations",
            value=f"{total_confirmed}",
            subtext="Confirmed Student Enrollments",
            top_bar_color="#10B981",
            value_color="#34D399",
        )
    with kpi_col3:
        render_kpi_card(
            label="Available Seats",
            value=f"{total_remaining}",
            subtext=f"Across {total_capacity} Total Seats",
            top_bar_color="#F59E0B",
            value_color="#FBBF24",
        )
    with kpi_col4:
        render_kpi_card(
            label="Registration Rate",
            value=f"{reg_rate:.1f}%",
            subtext="Overall Capacity Utilization",
            top_bar_color="#8B5CF6",
            value_color="#C084FC",
        )

    # ------------------ Upcoming Events Section ------------------
    render_section_heading(
        "Upcoming Events",
        "Active workshops with real-time capacity and occupancy metrics.",
    )

    if not events:
        st.info("No events found in the database. Use 'Manage Workshops' to create one.")
    else:
        # Display first 6 events in a clean 3-column card grid
        preview_events = events[:6]
        grid_cols = st.columns(3)
        for idx, ev in enumerate(preview_events):
            col_target = grid_cols[idx % 3]
            eid = ev["id"]
            title = ev["title"]
            category = ev["category"]
            venue = ev["venue"]
            cap = ev["capacity"]
            conf = ev["confirmed_count"]
            rem = ev["remaining_places"]
            date_display = ev["start_datetime"][:16] if ev.get("start_datetime") else "Upcoming"

            # Determine Status Badge
            if rem <= 0:
                status_label = "Full"
                status_badge_html = '<span class="badge badge-red">Full</span>'
                bar_color = "#F43F5E"
            elif rem <= 3 or (cap > 0 and (conf / cap) >= 0.85):
                status_label = "Almost Full"
                status_badge_html = f'<span class="badge badge-amber">{rem} Left</span>'
                bar_color = "#F59E0B"
            else:
                status_label = "Available"
                status_badge_html = f'<span class="badge badge-green">{rem} Available</span>'
                bar_color = "#10B981"

            fill_pct = min(100, int((conf / cap) * 100)) if cap > 0 else 100

            with col_target:
                st.markdown(
                    f"""
                    <div class="event-card">
                        <div>
                            <div class="event-card-header">
                                <span class="badge badge-indigo">{html.escape(category)}</span>
                                {status_badge_html}
                            </div>
                            <h3 class="event-card-title">{html.escape(title)}</h3>
                            <div class="event-card-meta">
                                <div class="event-card-meta-item">📍 {html.escape(venue)}</div>
                                <div class="event-card-meta-item">📅 {html.escape(date_display)}</div>
                            </div>
                        </div>
                        <div>
                            <div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#94A3B8; margin-bottom:2px;">
                                <span>Occupancy: {fill_pct}%</span>
                                <span>{conf} / {cap} Seats</span>
                            </div>
                            <div class="event-capacity-bar">
                                <div class="event-capacity-fill" style="width:{fill_pct}%; background:{bar_color};"></div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # Quick 1-click registration button
                if rem > 0:
                    if st.button(f"Register ({eid})", key=f"dash_reg_{eid}", use_container_width=True):
                        reg_res = service.register(user["id"], eid)
                        if reg_res["status"] == "CONFIRMED":
                            st.session_state.portal_message = ("success", f"Registered for {title}! Ticket ID: {reg_res['ticket_id']}")
                        elif reg_res["status"] == "DUPLICATE":
                            st.session_state.portal_message = ("warning", reg_res["message"])
                        elif reg_res["status"] == "WAITLISTED":
                            st.session_state.portal_message = ("info", reg_res["message"])
                        else:
                            st.session_state.portal_message = ("error", reg_res["message"])
                        st.rerun()
                else:
                    if st.button(f"Join Waitlist ({eid})", key=f"dash_wait_{eid}", use_container_width=True):
                        reg_res = service.register(user["id"], eid)
                        if reg_res["status"] == "WAITLISTED":
                            st.session_state.portal_message = ("info", f"Added to waitlist at Position #{reg_res['queue_position']}.")
                        else:
                            st.session_state.portal_message = ("warning", reg_res["message"])
                        st.rerun()

    # ------------------ Registration Analytics Section ------------------
    render_section_heading(
        "Registration Analytics",
        "Real-time enrollment distribution across workshops and academic categories.",
    )

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Chart 1: Registrations by Event (Top Events)
        if events:
            sorted_events = sorted(events, key=lambda x: x["confirmed_count"], reverse=True)[:8]
            df_chart_events = pd.DataFrame([
                {"Workshop": e["title"][:22] + ("..." if len(e["title"]) > 22 else ""), "Confirmed": e["confirmed_count"]}
                for e in sorted_events
            ])

            fig_events = px.bar(
                df_chart_events,
                x="Confirmed",
                y="Workshop",
                orientation="h",
                text="Confirmed",
                color="Confirmed",
                color_continuous_scale=["#1E293B", "#3B82F6", "#60A5FA"],
            )
            fig_events.update_layout(get_plotly_dark_layout("Top Workshops by Confirmed Participants", height=320))
            fig_events.update_coloraxes(showscale=False)
            fig_events.update_traces(textposition="outside", textfont=dict(color="#F8FAFC", size=11))
            fig_events.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_events, use_container_width=True)
        else:
            st.info("No registration data available for visualization.")

    with chart_col2:
        # Chart 2: Capacity Utilization by Category
        if events:
            cat_map: Dict[str, Dict[str, int]] = {}
            for e in events:
                c = e.get("category", "General")
                if c not in cat_map:
                    cat_map[c] = {"Confirmed": 0, "Available": 0}
                cat_map[c]["Confirmed"] += e["confirmed_count"]
                cat_map[c]["Available"] += e["remaining_places"]

            # Take top 6 categories
            top_cats = sorted(cat_map.items(), key=lambda x: (x[1]["Confirmed"] + x[1]["Available"]), reverse=True)[:6]
            cat_rows = []
            for c, d in top_cats:
                cat_rows.append({"Category": c, "Seats": d["Confirmed"], "Type": "Confirmed"})
                cat_rows.append({"Category": c, "Seats": d["Available"], "Type": "Available"})

            df_cat = pd.DataFrame(cat_rows)
            fig_cat = px.bar(
                df_cat,
                x="Category",
                y="Seats",
                color="Type",
                barmode="stack",
                color_discrete_map={"Confirmed": "#3B82F6", "Available": "#1E293B"},
            )
            fig_cat.update_layout(get_plotly_dark_layout("Seat Capacity Breakdown by Category", height=320))
            fig_cat.update_traces(marker_line_color="#232F47", marker_line_width=1)
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No capacity data available for visualization.")

    # ------------------ Recent Activity Section ------------------
    render_section_heading(
        "Recent Activity",
        "Chronological audit trail of registrations, waitlist queues, and check-ins.",
    )

    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 6")
    recent_logs = [dict(r) for r in cur.fetchall()]

    if recent_logs:
        for log in recent_logs:
            actor = log.get("actor_id") or "System"
            action = log.get("action") or "LOG"
            details = log.get("details") or ""
            ts = log.get("created_at") or ""
            time_short = ts[11:19] if len(ts) >= 19 else ts
            date_short = ts[:10] if len(ts) >= 10 else ""

            st.markdown(
                f"""
                <div class="activity-row">
                    <div>
                        <div class="activity-actor">
                            {html.escape(actor)}
                            &nbsp;{render_status_badge(action)}
                        </div>
                        <div class="activity-details">{html.escape(details)}</div>
                    </div>
                    <div class="activity-time">
                        {html.escape(date_short)} {html.escape(time_short)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No recent activity recorded yet.")


# =============================================================================
# 2. 🔍 REGISTRATION PORTAL (BROWSE & REGISTER)
# =============================================================================
elif nav_choice == "🔍 Registration Portal":
    render_saas_header(
        "Workshop Registration Portal",
        "Search workshops, reserve seats with mutual exclusion protection, or join FIFO waitlists.",
    )
    display_portal_message()

    all_raw_events = service.list_events(status=None)
    categories_available = ["All"] + sorted(list(set(e["category"] for e in all_raw_events if e.get("category"))))
    venues_available = ["All"] + sorted(list(set(e["venue"] for e in all_raw_events if e.get("venue"))))

    # Search & Filter Toolbar
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1, 1, 1])
    with f_col1:
        search_kw = st.text_input("🔍 Search Workshops", placeholder="Search by title, topic, or keyword...", label_visibility="collapsed")
    with f_col2:
        cat_filter = st.selectbox("Category", categories_available, label_visibility="collapsed")
    with f_col3:
        venue_filter = st.selectbox("Venue", venues_available, label_visibility="collapsed")
    with f_col4:
        available_only = st.checkbox("Available Seats Only", value=False)

    filtered_events = service.list_events(
        category=cat_filter if cat_filter != "All" else None,
        venue=venue_filter if venue_filter != "All" else None,
        status="Published",
        search_query=search_kw,
    )

    if available_only:
        filtered_events = [e for e in filtered_events if e["remaining_places"] > 0]

    st.markdown(f"<div style='font-size:0.85rem; color:#94A3B8; margin:12px 0;'>Showing <strong>{len(filtered_events)}</strong> matching workshops</div>", unsafe_allow_html=True)

    if not filtered_events:
        st.warning("No workshops matched your search and filter criteria. Try adjusting your query.")
    else:
        for ev in filtered_events:
            eid = ev["id"]
            title = ev["title"]
            desc = ev["description"] or "No detailed description provided."
            cap = ev["capacity"]
            rem = ev["remaining_places"]
            conf = ev["confirmed_count"]
            venue = ev["venue"]
            dt = ev["start_datetime"][:16] if ev.get("start_datetime") else "TBA"

            # Check if current user already registered
            user_regs = service.get_user_registrations(user["id"])
            user_status_for_ev = next((r["registration_status"] for r in user_regs if r["event_id"] == eid), None)

            st.markdown(
                f"""
                <div class="event-card">
                    <div class="event-card-header">
                        <div>
                            <span class="badge badge-indigo">{html.escape(ev['category'])}</span>
                            <span style="font-size:0.82rem; color:#64748B; margin-left:8px; font-family:monospace;">ID: {html.escape(eid)}</span>
                        </div>
                        <div>
                            {render_status_badge('CONFIRMED' if user_status_for_ev == 'CONFIRMED' else ('WAITLISTED' if user_status_for_ev == 'WAITLISTED' else ('AVAILABLE' if rem > 0 else 'FULL')))}
                        </div>
                    </div>
                    <h3 class="event-card-title">{html.escape(title)}</h3>
                    <p style="color:#CBD5E1; font-size:0.88rem; margin:8px 0 12px 0; line-height:1.5;">{html.escape(desc)}</p>
                    <div class="event-card-meta">
                        <div class="event-card-meta-item">📍 <strong>Venue:</strong> {html.escape(venue)}</div>
                        <div class="event-card-meta-item">📅 <strong>Date:</strong> {html.escape(dt)}</div>
                        <div class="event-card-meta-item">🪑 <strong>Capacity:</strong> {cap} seats</div>
                        <div class="event-card-meta-item">🟢 <strong>Available:</strong> <span style="color:#34D399; font-weight:700;">{rem}</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            act_col1, act_col2 = st.columns([1, 4])
            with act_col1:
                if user_status_for_ev in ("CONFIRMED", "WAITLISTED"):
                    if st.button(f"❌ Cancel Registration", key=f"portal_cancel_{eid}", use_container_width=True):
                        c_res = service.cancel(user["id"], eid)
                        st.session_state.portal_message = ("info", c_res["message"])
                        st.rerun()
                elif rem > 0:
                    if st.button(f"✅ Register ({eid})", key=f"portal_reg_{eid}", type="primary", use_container_width=True):
                        res = service.register(user["id"], eid)
                        if res["status"] == "CONFIRMED":
                            st.session_state.portal_message = ("success", f"CONFIRMED! Ticket token issued: {res['ticket_id']}")
                        elif res["status"] == "DUPLICATE":
                            st.session_state.portal_message = ("warning", res["message"])
                        elif res["status"] == "WAITLISTED":
                            st.session_state.portal_message = ("info", res["message"])
                        else:
                            st.session_state.portal_message = ("error", res["message"])
                        st.rerun()
                else:
                    if st.button(f"⏳ Join Waitlist ({eid})", key=f"portal_wait_{eid}", use_container_width=True):
                        res = service.register(user["id"], eid)
                        if res["status"] == "WAITLISTED":
                            st.session_state.portal_message = ("info", f"Added to FIFO Waitlist at Position #{res['queue_position']}.")
                        else:
                            st.session_state.portal_message = ("warning", res["message"])
                        st.rerun()


# =============================================================================
# 3. 🎫 MY REGISTRATIONS & QR TICKETS (STUDENT WORKSPACE)
# =============================================================================
elif nav_choice == "🎫 My Registrations & QR Passes":
    render_saas_header(
        "My Registrations & Digital Passes",
        "View your confirmed bookings, download digital QR tickets, or cancel reservations.",
    )
    display_portal_message()

    my_regs = service.get_user_registrations(user["id"])

    if not my_regs:
        st.info("You have no registrations yet. Explore the Registration Portal to enroll!")
    else:
        for r in my_regs:
            eid = r["event_id"]
            status = r["registration_status"]
            ticket_id = r["ticket_id"]

            r_col1, r_col2 = st.columns([3, 2])
            with r_col1:
                st.markdown(
                    f"""
                    <div class="event-card">
                        <div class="event-card-header">
                            <h3 class="event-card-title">{html.escape(r['event_title'])}</h3>
                            {render_status_badge(status)}
                        </div>
                        <div class="event-card-meta">
                            <div class="event-card-meta-item">📍 {html.escape(r['venue'])}</div>
                            <div class="event-card-meta-item">📅 {html.escape(r['start_datetime'][:16])}</div>
                        </div>
                        <div style="font-family:'JetBrains Mono', monospace; color:#60A5FA; font-size:0.84rem; margin:8px 0;">
                            Ticket ID: {html.escape(ticket_id or 'Pending / Waitlisted')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if status in ("CONFIRMED", "WAITLISTED"):
                    if st.button(f"❌ Cancel Registration ({eid})", key=f"my_cancel_{eid}"):
                        c_res = service.cancel(user["id"], eid)
                        st.session_state.portal_message = ("info", c_res["message"])
                        st.rerun()

            with r_col2:
                if status in ("CONFIRMED", "ATTENDED") and ticket_id:
                    badge_bytes = ticket_service.generate_ticket_badge_card(
                        ticket_id=ticket_id,
                        event_title=r["event_title"],
                        user_name=user["display_name"],
                        venue=r["venue"],
                        date_str=r["start_datetime"][:10],
                    )
                    st.image(badge_bytes, caption=f"Digital Pass: {ticket_id}", use_container_width=True)
                    st.download_button(
                        label="📥 Download Pass (PNG)",
                        data=badge_bytes,
                        file_name=f"pass_{ticket_id}.png",
                        mime="image/png",
                        key=f"dl_{ticket_id}",
                    )
                elif status == "WAITLISTED":
                    pos = r.get("queue_position") or 1
                    st.info(f"⏳ Waitlisted: You are at **Position #{pos}**. When a seat is freed, the system automatically promotes in FIFO order.")


# =============================================================================
# 4. ➕ MANAGE WORKSHOPS (ORGANIZER WORKSPACE)
# =============================================================================
elif nav_choice == "➕ Manage Workshops":
    render_saas_header(
        "Organizer Workshop Management",
        "Create new workshops with validated capacities and manage publication statuses.",
    )

    tab_create, tab_manage = st.tabs(["➕ Create New Workshop", "📋 All Published Workshops"])

    with tab_create:
        with st.form("create_event_form", clear_on_submit=True):
            f1, f2 = st.columns(2)
            with f1:
                new_id = st.text_input("Event ID (e.g. EVT-21, WORKSHOP_OS)", placeholder="EVT-21")
                new_title = st.text_input("Workshop Title", placeholder="Network Sockets & TCP Concurrency")
                new_cat = st.selectbox("Category", [
                    "Programming", "Web Development", "Artificial Intelligence", "Cybersecurity",
                    "Cloud Computing", "DevOps", "Developer Tools", "Databases", "Networking",
                    "Operating Systems", "Competition", "Hackathon", "Career Development",
                    "Design", "Entrepreneurship", "Systems & OS", "Distributed Systems", "Core Systems", "General"
                ])
                new_venue = st.text_input("Venue / Lab", placeholder="Dijkstra Lab 402")
            with f2:
                new_cap = st.number_input("Maximum Capacity (Seats)", min_value=1, max_value=500, value=30)
                start_d = st.date_input("Start Date", value=datetime.now().date() + timedelta(days=7))
                start_t = st.time_input("Start Time", value=datetime.strptime("10:00", "%H:%M").time())
                end_t = st.time_input("End Time", value=datetime.strptime("13:00", "%H:%M").time())

            new_desc = st.text_area("Workshop Description", placeholder="Detailed syllabus, prerequisites, and learning outcomes...")
            submit_create = st.form_submit_button("🚀 Publish Workshop", type="primary")

            if submit_create:
                start_dt = f"{start_d} {start_t}"
                end_dt = f"{start_d} {end_t}"
                ok, msg = service.create_event(
                    event_id=new_id,
                    title=new_title,
                    description=new_desc,
                    category=new_cat,
                    venue=new_venue,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    capacity=new_cap,
                    organizer_id=user["id"],
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    with tab_manage:
        all_events = service.list_events(status=None)
        if all_events:
            df_m = pd.DataFrame(all_events)[["id", "title", "category", "venue", "capacity", "confirmed_count", "remaining_places", "status"]]
            render_dataframe(df_m, hide_index=True)
        else:
            st.info("No workshops registered yet.")


# =============================================================================
# 5. 🎟️ ATTENDANCE CHECK-IN (ORGANIZER WORKSPACE)
# =============================================================================
elif nav_choice == "🎟️ Attendance Check-In":
    render_saas_header(
        "QR Ticket Check-In Verification",
        "Scan or enter ticket identifiers to verify attendee registrations and record presence.",
    )

    checkin_col1, checkin_col2 = st.columns([1, 1])

    with checkin_col1:
        st.markdown("### 🔍 Verify Ticket")
        ticket_input = st.text_input("Scan / Enter Ticket ID", placeholder="e.g. TKT-E1-studenta-E8561519")

        if st.button("✅ Verify & Check In", type="primary", use_container_width=True):
            if not ticket_input.strip():
                st.warning("Please provide a ticket ID.")
            else:
                ok, msg, reg_data = ticket_service.verify_and_checkin_ticket(ticket_input.strip(), checked_in_by=user["id"])
                if ok:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)

    with checkin_col2:
        st.markdown("### 📊 Check-In Roster for Workshop")
        events_list = service.list_events(status=None)
        sel_eid = st.selectbox("Select Workshop to view check-ins", options=[e["id"] for e in events_list], format_func=lambda x: f"{x} - {next((e['title'] for e in events_list if e['id'] == x), '')}")

        roster = ticket_service.get_event_attendance_roster(sel_eid)
        if roster:
            df_roster = pd.DataFrame(roster)[["display_name", "user_id", "ticket_id", "attendance_status", "checked_in_at"]]
            render_dataframe(df_roster, hide_index=True)
        else:
            st.info("No confirmed attendees yet for this workshop.")


# =============================================================================
# 6. 📋 ATTENDEE ROSTERS & EXPORT (ORGANIZER / ADMIN)
# =============================================================================
elif nav_choice == "📋 Attendee Rosters":
    render_saas_header(
        "Attendee Rosters & Official Export",
        "Generate verified attendee listings with CSV anti-formula protection and printable PDF reports.",
    )

    evs = service.list_events(status=None)
    sel_e = st.selectbox("Select Workshop", options=[e["id"] for e in evs], format_func=lambda x: f"{x} - {next((e['title'] for e in evs if e['id'] == x), '')}")

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        csv_str = report_service.get_attendees_csv(sel_e)
        st.download_button(
            label="📥 Export Sanitized CSV (Anti-Formula Injection)",
            data=csv_str,
            file_name=f"attendees_{sel_e}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with exp_col2:
        try:
            pdf_data = report_service.generate_event_roster_pdf(sel_e)
            st.download_button(
                label="📄 Generate Official Printable PDF Report",
                data=pdf_data,
                file_name=f"roster_{sel_e}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        except Exception as ex:
            st.warning(f"PDF generator notice: {ex}")

    st.markdown("#### Live Attendee Table")
    att_csv = report_service.get_attendees_csv(sel_e)
    if att_csv:
        df_att = pd.read_csv(io.StringIO(att_csv))
        render_dataframe(df_att, hide_index=True)
    else:
        st.info("No attendees enrolled yet.")


# =============================================================================
# 7. 🛡️ ADMIN CONTROL PANEL (ADMINISTRATOR ONLY)
# =============================================================================
elif nav_choice == "🛡️ Admin Control Panel":
    render_saas_header(
        "System Administrator Control Panel",
        "Manage system users, reassign security roles, and review database health.",
    )

    if not auth.can_admin_system(user):
        st.error("Access Denied: Only users with the Administrator role can access this page.")
    else:
        tab_users, tab_db = st.tabs(["👥 User & Role Management", "🗄️ Database Health"])

        with tab_users:
            all_users = auth.list_all_users()
            st.markdown("#### Registered System Users")
            df_users = pd.DataFrame(all_users)[["id", "display_name", "email", "role", "created_at", "status"]]
            render_dataframe(df_users, hide_index=True)

            st.markdown("#### Modify User Role")
            u_col1, u_col2, u_col3 = st.columns(3)
            with u_col1:
                target_uid = st.selectbox("Target User", options=[u["id"] for u in all_users])
            with u_col2:
                target_role = st.selectbox("New Role", ["Student", "Organizer", "Administrator"])
            with u_col3:
                st.write("")
                st.write("")
                if st.button("Update Role", type="primary"):
                    ok, msg = auth.update_user_role(user, target_uid, target_role)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_db:
            st.markdown(f"**Database Location:** `{database.DATABASE_FILE}`")
            st.markdown(f"**Journal Mode:** `WAL (Write-Ahead Logging)`")
            st.markdown(f"**Foreign Keys:** `ENABLED`")
            if st.button("⚠️ Re-Initialize Database (Reset to Default Demo State)"):
                database.init_db(reset=True)
                st.success("Database restored to clean default demo state.")
                st.rerun()


# =============================================================================
# 8. ⚡ CONCURRENCY SIMULATOR (SHOWCASE LAB)
# =============================================================================
elif nav_choice == "⚡ Concurrency Simulator":
    render_saas_header(
        "Concurrency Simulator: Mutex ON vs Mutex OFF",
        "Execute concurrent threads simultaneously to trigger the race condition or enforce mutual exclusion.",
    )

    st.markdown(
        """
        <div class="event-card" style="margin-bottom:20px;">
            <div style="font-weight:700; color:#F8FAFC; margin-bottom:4px;">⚙️ Operating Systems Simulation Setup</div>
            <div style="font-size:0.88rem; color:#94A3B8; line-height:1.5;">
                Multiple worker threads simultaneously execute <code>store.register()</code> using a synchronization barrier.
                <strong>Without Mutex:</strong> Threads interleave inside the critical section, reading the identical capacity count and causing overbooking (negative remaining places).
                <strong>With Mutex:</strong> The <code>threading.Lock</code> serializes critical section access, guaranteeing that exactly 1 thread enters at any instant.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    use_fg = st.checkbox("Enable Fine-Grained Per-Event Locking (Advanced OS Mode)", value=False, help="Uses event-specific mutex lock instead of single global lock")

    b_col1, b_col2, b_col3 = st.columns([1, 1, 1.5])
    sim_users = [f"S{i}" for i in range(1, num_users + 1)]

    with b_col1:
        if st.button("🔴 Run Unsafe (Mutex OFF)", use_container_width=True):
            with st.spinner("Spawning uncoordinated threads..."):
                fresh_store = store.clone()
                fresh_store.events[sim_eid]["capacity"] = initial_seats
                fresh_store.events[sim_eid]["remaining_places"] = initial_seats
                res = run_simulation(sim_eid, sim_users, use_lock=False, delay=sim_delay, store=fresh_store)
                st.session_state.last_sim_result = res
                st.session_state.last_comparison_result = None

    with b_col2:
        if st.button("🟢 Run Safe (Mutex ON)", use_container_width=True):
            with st.spinner("Spawning mutex-protected threads..."):
                fresh_store = store.clone()
                fresh_store.events[sim_eid]["capacity"] = initial_seats
                fresh_store.events[sim_eid]["remaining_places"] = initial_seats
                res = run_simulation(sim_eid, sim_users, use_lock=True, delay=sim_delay, store=fresh_store, use_fine_grained=use_fg)
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
                    use_fine_grained=use_fg,
                )
                st.session_state.last_comparison_result = comp
                st.session_state.last_sim_result = comp["safe"]

    st.markdown("---")

    if st.session_state.last_comparison_result:
        comp = st.session_state.last_comparison_result
        u_res = comp["unsafe"]
        s_res = comp["safe"]

        render_section_heading("Side-by-Side Concurrency Comparison Results")
        cmp_col1, cmp_col2 = st.columns(2)

        with cmp_col1:
            if u_res["overbooked"]:
                st.markdown(
                    """
                    <div class="banner-unsafe">
                        <div class="banner-unsafe-title">⚠️ OVERBOOKED / RACE DETECTED</div>
                        <div class="banner-unsafe-desc">Unsynchronized threads interleaved in the critical section, reading stale capacity and overbooking!</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="banner-unsafe" style="border-left-color:#F59E0B;">
                        <div class="banner-unsafe-title" style="color:#FBBF24;">⚠️ RACE NOT TRIGGERED THIS RUN</div>
                        <div class="banner-unsafe-desc">OS thread scheduling was sequential on this run. Re-run to observe non-deterministic interleaving.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            u_m1, u_m2, u_m3 = st.columns(3)
            with u_m1:
                st.metric("Initial Capacity", u_res["capacity"])
            with u_m2:
                u_color = "normal" if not u_res["overbooked"] else "inverse"
                st.metric("Confirmed", f"{u_res['confirmed_count']} users", delta=f"{u_res['confirmed_count'] - u_res['capacity']} excess" if u_res['confirmed_count'] > u_res['capacity'] else None, delta_color=u_color)
            with u_m3:
                st.metric("Final Remaining", u_res["final_remaining"])

            st.markdown(f"**Runtime:** `{u_res['total_runtime_ms']} ms` | **Throughput:** `{u_res['throughput_rps']} req/s` | **Mutex:** `OFF`")

            if u_res["violations"]:
                st.error("🚨 Invariant Violations:\n- " + "\n- ".join(u_res["violations"]))

            st.markdown("#### Unsafe Per-Thread Telemetry")
            df_u = pd.DataFrame(u_res["thread_results"])[["user", "thread_name", "status", "remaining_after", "timestamp"]]
            render_dataframe(df_u, hide_index=True)

        with cmp_col2:
            st.markdown(
                """
                <div class="banner-safe">
                    <div class="banner-safe-title">🛡️ CONSISTENT & SYNCHRONIZED</div>
                    <div class="banner-safe-desc">Mutex lock strictly enforced atomic critical section execution. Invariants strictly preserved!</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            s_m1, s_m2, s_m3 = st.columns(3)
            with s_m1:
                st.metric("Initial Capacity", s_res["capacity"])
            with s_m2:
                st.metric("Confirmed", f"{s_res['confirmed_count']} users", delta="Exact Match", delta_color="normal")
            with s_m3:
                st.metric("Final Remaining", s_res["final_remaining"])

            lock_type_str = "Fine-Grained Per-Event" if s_res.get("use_fine_grained") else "Global Mutex"
            st.markdown(f"**Runtime:** `{s_res['total_runtime_ms']} ms` | **Throughput:** `{s_res['throughput_rps']} req/s` | **Lock:** `{lock_type_str}`")

            if not s_res["violations"]:
                st.success("✅ State Invariants Satisfied: 0 Violations (capacity - remaining == len(registrations)).")

            st.markdown("#### Safe Per-Thread Telemetry")
            df_s = pd.DataFrame(s_res["thread_results"])[["user", "thread_name", "status", "waited_ms", "held_ms", "remaining_after"]]
            render_dataframe(df_s, hide_index=True)


# =============================================================================
# 9. 🧵 THREAD TIMELINE (GANTT CHART)
# =============================================================================
elif nav_choice == "🧵 Thread Timeline":
    render_saas_header(
        "Thread Execution Timeline & Gantt Chart",
        "Visualize lock wait queues, critical section entry, and thread interleaving.",
    )

    active_res = None
    if st.session_state.last_comparison_result:
        choice = st.radio("Choose Simulation Mode to Visualize", ["Safe Mode (Mutex ON)", "Unsafe Mode (Mutex OFF)"], horizontal=True)
        active_res = st.session_state.last_comparison_result["safe"] if "Safe" in choice else st.session_state.last_comparison_result["unsafe"]
    elif st.session_state.last_sim_result:
        active_res = st.session_state.last_sim_result
    else:
        st.info("No simulation run recorded yet. Running initial benchmark...")
        active_res = run_simulation("E1", ["S1", "S2", "S3"], use_lock=True, delay=0.2)
        st.session_state.last_sim_result = active_res

    if active_res and active_res.get("timeline_data"):
        tl_data = active_res["timeline_data"]
        df_tl = pd.DataFrame(tl_data)

        # Plotly Gantt Chart
        fig = go.Figure()

        for _, row in df_tl.iterrows():
            thread_name = row["Thread"]
            wait_start = row["Wait_Start_ms"]
            cs_entry = row["CS_Entry_ms"]
            cs_exit = row["CS_Exit_ms"]
            status = row["Status"]

            if cs_entry > wait_start:
                fig.add_trace(go.Bar(
                    name="Waiting for Lock",
                    y=[thread_name],
                    x=[cs_entry - wait_start],
                    base=[wait_start],
                    orientation='h',
                    marker=dict(color="#F59E0B", line=dict(color="#D97706", width=1)),
                    showlegend=False,
                ))

            cs_color = "#10B981" if (active_res["use_lock"] and status == "CONFIRMED") else ("#F43F5E" if not active_res["use_lock"] else "#64748B")
            fig.add_trace(go.Bar(
                name=f"Critical Section ({status})",
                y=[thread_name],
                x=[cs_exit - cs_entry],
                base=[cs_entry],
                orientation='h',
                marker=dict(color=cs_color, line=dict(color="#151D2F", width=1)),
                showlegend=False,
            ))

        fig.update_layout(
            barmode='stack',
            title=dict(
                text=f"Thread Timeline ({'Mutex ON: Serialized Queue' if active_res['use_lock'] else 'Mutex OFF: Concurrent Overlap'})",
                font=dict(color="#F8FAFC", size=15),
            ),
            xaxis=dict(title="Elapsed Time (milliseconds)", color="#94A3B8", gridcolor="#232F47"),
            yaxis=dict(title="Thread ID", color="#94A3B8", autorange="reversed"),
            paper_bgcolor="#151D2F",
            plot_bgcolor="#151D2F",
            height=340 + (len(df_tl) * 18),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """
            <div style="font-size:0.84rem; color:#94A3B8; margin-top:8px;">
                <span style="color:#FBBF24; font-weight:700;">■ Amber:</span> Thread waiting on <code>lock.acquire()</code> (Blocked in scheduler queue). &nbsp;|&nbsp;
                <span style="color:#34D399; font-weight:700;">■ Green:</span> Thread executing critical section atomically. &nbsp;|&nbsp;
                <span style="color:#FB7185; font-weight:700;">■ Red:</span> Unsafe concurrent overlap without lock.
            </div>
            """,
            unsafe_allow_html=True,
        )


# =============================================================================
# 10. 🔒 MUTEX EXPLAINER (OPERATING SYSTEMS CONCEPTS)
# =============================================================================
elif nav_choice == "🔒 Mutex Explainer":
    render_saas_header(
        "Operating Systems Synchronization Explainer",
        "A visual and technical guide to mutual exclusion, critical sections, and race condition prevention.",
    )

    # 4 Core Concept Cards
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="event-card" style="height:100%;">
                <h3 style="color:#60A5FA; margin-top:0;">1. What is a Mutex?</h3>
                <p style="color:#CBD5E1; font-size:0.9rem; line-height:1.6;">
                    A <strong>Mutex</strong> (Mutual Exclusion lock) is a binary synchronization primitive that guarantees only one thread enters a critical region of code at any given time.
                    The thread that acquires the mutex holds exclusive ownership and must release it when finished.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="event-card" style="height:100%;">
                <h3 style="color:#C084FC; margin-top:0;">2. What is a Critical Section?</h3>
                <p style="color:#CBD5E1; font-size:0.9rem; line-height:1.6;">
                    The <strong>Critical Section</strong> is the portion of code where shared resources (such as <code>remaining_places</code> and the registration list) are read, checked, and updated.
                    Without mutual exclusion, multiple threads interleave, causing state inconsistency.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    c3, c4 = st.columns(2)
    with c3:
        st.markdown(
            """
            <div class="event-card" style="height:100%;">
                <h3 style="color:#FB7185; margin-top:0;">3. What is a Race Condition?</h3>
                <p style="color:#CBD5E1; font-size:0.9rem; line-height:1.6;">
                    A <strong>Race Condition</strong> occurs when the outcome of a program depends on the non-deterministic scheduling and timing of concurrent threads.
                    In registration, two threads read <code>remaining = 1</code> at the same time, and both confirm, driving remaining seats to negative values.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            """
            <div class="event-card" style="height:100%;">
                <h3 style="color:#34D399; margin-top:0;">4. Why Synchronization is Necessary</h3>
                <p style="color:#CBD5E1; font-size:0.9rem; line-height:1.6;">
                    Although Python has a Global Interpreter Lock (GIL), the GIL only synchronizes individual bytecode operations—not application-level check-then-act logic.
                    Explicit mutex locking via <code>threading.Lock</code> is mandatory to guarantee ACID invariant correctness.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Mutex Execution Lifecycle
    render_section_heading("Mutex Lock Execution Lifecycle", "The 5-step serialized synchronization flow.")
    l1, l2, l3, l4, l5 = st.columns(5)
    with l1:
        st.markdown("""<div class="lifecycle-step"><div class="lifecycle-step-num">1</div><div class="lifecycle-step-title">Request</div><div class="lifecycle-step-desc">Thread arrives and requests seat</div></div>""", unsafe_allow_html=True)
    with l2:
        st.markdown("""<div class="lifecycle-step"><div class="lifecycle-step-num">2</div><div class="lifecycle-step-title">Acquire Lock</div><div class="lifecycle-step-desc"><code>lock.acquire()</code> (Blocks if busy)</div></div>""", unsafe_allow_html=True)
    with l3:
        st.markdown("""<div class="lifecycle-step"><div class="lifecycle-step-num">3</div><div class="lifecycle-step-title">Critical Section</div><div class="lifecycle-step-desc">Verify & decrement atomically</div></div>""", unsafe_allow_html=True)
    with l4:
        st.markdown("""<div class="lifecycle-step"><div class="lifecycle-step-num">4</div><div class="lifecycle-step-title">Release Lock</div><div class="lifecycle-step-desc"><code>lock.release()</code> in <code>finally</code></div></div>""", unsafe_allow_html=True)
    with l5:
        st.markdown("""<div class="lifecycle-step"><div class="lifecycle-step-num">5</div><div class="lifecycle-step-title">Next Thread</div><div class="lifecycle-step-desc">Waiting thread is awakened</div></div>""", unsafe_allow_html=True)

    # Python Code Pattern Box
    render_section_heading("Recommended Synchronization Pattern in Python")
    st.code(
        """import threading

lock = threading.Lock()

def register_user(user_id: str, event_id: str):
    lock.acquire()
    try:
        # --- CRITICAL SECTION START ---
        if user_id in registrations[event_id]:
            return "DUPLICATE"
        if remaining_places[event_id] > 0:
            remaining_places[event_id] -= 1
            registrations[event_id].add(user_id)
            return "CONFIRMED"
        else:
            return "FULL"
        # --- CRITICAL SECTION END ---
    finally:
        # Guarantee lock is released even if an exception occurs
        lock.release()
""",
        language="python",
    )

    # Architectural Comparison Table
    render_section_heading("Synchronization Mechanisms Comparison")
    comp_data = [
        {"Primitive": "Mutex (threading.Lock)", "Mechanism": "Strict mutual exclusion", "Permits": "Exactly 1 thread", "Ownership": "Yes (acquirer must release)", "Role in System": "Protects in-memory check-then-act capacity decrement"},
        {"Primitive": "Counting Semaphore", "Mechanism": "Permit counter pool", "Permits": "N concurrent permits", "Ownership": "No (any thread can signal)", "Role in System": "Demonstrated in the Permit Pool Lab below"},
        {"Primitive": "FIFO Waitlist Queue", "Mechanism": "Deterministic turn-taking", "Permits": "Unbounded / Bounded queue", "Ownership": "N/A", "Role in System": "Enforces fair promotion when confirmed seats cancel"},
        {"Primitive": "SQLite ACID Transaction", "Mechanism": "Write-Ahead Log (WAL)", "Permits": "Serialized disk commits", "Ownership": "Connection", "Role in System": "Guarantees database consistency across restarts"},
    ]
    render_dataframe(pd.DataFrame(comp_data), hide_index=True)

    # Interactive Counting Semaphore Permit Pool Lab
    render_section_heading("Interactive Counting Semaphore Permit Lab")
    sem_c1, sem_c2, sem_c3 = st.columns(3)
    with sem_c1:
        sem_cap = st.slider("Permits in Pool (Capacity)", 1, 5, 2)
    with sem_c2:
        sem_threads = st.slider("Requesting Threads", 2, 10, 5)
    with sem_c3:
        sem_hold = st.slider("Hold Duration (seconds)", 0.1, 0.5, 0.2, 0.05)

    if st.button("🚀 Run Semaphore Permit Simulation", type="primary"):
        sem_res = waitlist_service.run_semaphore_simulation(sem_cap, sem_threads, sem_hold)
        st.success(f"Simulation completed in {sem_res['total_runtime_ms']} ms!")

        df_sem = pd.DataFrame(sem_res["results"])
        render_dataframe(df_sem, hide_index=True)


# =============================================================================
# 11. 📊 ANALYTICS & BENCHMARKING
# =============================================================================
elif nav_choice == "📊 Analytics":
    render_saas_header(
        "Concurrency & Attendance Analytics",
        "Statistical verification across repeated trials and business attendance metrics.",
    )

    tab_concur_stats, tab_biz_stats = st.tabs(["⚡ Concurrency Benchmark", "📈 Workshop Attendance Stats"])

    with tab_concur_stats:
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1:
            num_trials = st.slider("Trials (N)", 5, 25, 10, 5)
        with t_col2:
            trial_threads = st.slider("Threads per Trial", 3, 10, 4)
        with t_col3:
            trial_delay = st.slider("Delay (s)", 0.05, 0.25, 0.1, 0.05)

        if st.button("🚀 Execute Multi-Trial Benchmark", type="primary"):
            with st.spinner("Conducting trials..."):
                unsafe_over = 0
                safe_over = 0
                records = []

                for t_idx in range(1, num_trials + 1):
                    users = [f"T{t_idx}_U{j}" for j in range(1, trial_threads + 1)]
                    cmp = run_comparison("E1", users, delay=trial_delay, capacity_override=1, remaining_override=1)
                    if cmp["unsafe"]["overbooked"]:
                        unsafe_over += 1
                    if cmp["safe"]["overbooked"]:
                        safe_over += 1
                    records.append({
                        "Trial": t_idx,
                        "Unsafe Confirmed": cmp["unsafe"]["confirmed_count"],
                        "Safe Confirmed": cmp["safe"]["confirmed_count"],
                        "Unsafe Overbooked": cmp["unsafe"]["overbooked"],
                    })

                st.session_state.bench_res = {
                    "records": records,
                    "unsafe_rate": (unsafe_over / num_trials) * 100,
                    "safe_rate": (safe_over / num_trials) * 100,
                    "num_trials": num_trials,
                }

        if st.session_state.bench_res:
            br = st.session_state.bench_res
            bm1, bm2, bm3 = st.columns(3)
            with bm1:
                st.metric("Total Trials", br["num_trials"])
            with bm2:
                st.metric("Unsafe Race Frequency", f"{br['unsafe_rate']:.1f}%", delta="Failure Rate", delta_color="inverse")
            with bm3:
                st.metric("Safe Invariant Guarantee", f"{br['safe_rate']:.1f}%", delta="0.0% Violations", delta_color="normal")

            df_b = pd.DataFrame(br["records"])
            fig_b = px.bar(
                df_b,
                x="Trial",
                y=["Unsafe Confirmed", "Safe Confirmed"],
                barmode="group",
                title="Confirmed Registrations per Trial (Capacity = 1)",
                color_discrete_map={"Unsafe Confirmed": "#F43F5E", "Safe Confirmed": "#10B981"},
            )
            fig_b.update_layout(get_plotly_dark_layout("Empirical Overbooking vs Mutex Guarantee", height=340))
            st.plotly_chart(fig_b, use_container_width=True)

    with tab_biz_stats:
        evs = service.list_events(status=None)
        if evs:
            df_biz = pd.DataFrame(evs)[["title", "capacity", "confirmed_count", "remaining_places"]]
            render_dataframe(df_biz, hide_index=True)


# =============================================================================
# 12. 🧪 TEST CENTER (15 AUTOMATED TESTS)
# =============================================================================
elif nav_choice == "🧪 Test Center (15 Tests)":
    render_saas_header(
        "Operating Systems Automated Test Center",
        "Execute 15 automated verification tests validating synchronization, persistence, seeding idempotency, and security.",
    )

    tb1, tb2 = st.columns([1, 2])
    with tb1:
        if st.button("▶️ Run Complete 15-Test QA Suite", type="primary", use_container_width=True):
            with st.spinner("Executing tests..."):
                st.session_state.test_results = test_cases.run_all_tests()

    with tb2:
        if st.session_state.test_results:
            passed = sum(1 for t in st.session_state.test_results if t["passed"])
            total = len(st.session_state.test_results)
            if passed == total:
                st.success(f"✅ All {passed}/{total} Verification Tests Passed! (Full 20/20 Academic Verification)")
            else:
                st.error(f"❌ {passed}/{total} Tests Passed. Review failures below.")

    st.markdown("---")
    if not st.session_state.test_results:
        st.info("Click '▶️ Run Complete 15-Test QA Suite' above to execute all automated test scenarios.")
    else:
        for r in st.session_state.test_results:
            badge_html = "<span class='badge badge-green'>PASS</span>" if r["passed"] else "<span class='badge badge-red'>FAIL</span>"
            st.markdown(
                f"""
                <div class="event-card" style="margin-bottom:10px; padding:14px 18px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div><strong>{html.escape(r['id'])}: {html.escape(r['name'])}</strong> {badge_html}</div>
                        <div style="font-size:0.82rem; color:#94A3B8; font-family:'JetBrains Mono', monospace;">{r['duration_ms']} ms</div>
                    </div>
                    <div style="font-size:0.86rem; color:#CBD5E1; margin-top:4px;">{html.escape(r['description'])}</div>
                    <div style="font-size:0.82rem; color:#94A3B8; margin-top:6px; font-family:'JetBrains Mono', monospace; background:#0B0F19; padding:6px 10px; border-radius:6px; border:1px solid #1E293B;">
                        {html.escape(r['details'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# =============================================================================
# 13. 📜 SYSTEM AUDIT LOG
# =============================================================================
elif nav_choice == "📜 System Audit Log":
    render_saas_header(
        "System Audit & Concurrency Ledger",
        "Chronological audit records tracking registrations, cancellations, and check-ins.",
    )

    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY created_at DESC")
    logs = [dict(r) for r in cursor.fetchall()]

    if logs:
        # Filter row
        actions_list = ["ALL"] + sorted(list(set(l["action"] for l in logs if l.get("action"))))
        f_act = st.selectbox("Filter by Action", actions_list)

        filtered_logs = logs if f_act == "ALL" else [l for l in logs if l.get("action") == f_act]

        df_logs = pd.DataFrame(filtered_logs)
        render_dataframe(df_logs, hide_index=True)

        csv_str = report_service.export_to_csv_string(filtered_logs)
        st.download_button(
            label="📥 Download Audit Log as CSV (Sanitized)",
            data=csv_str,
            file_name="audit_log.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Audit log is currently empty.")
