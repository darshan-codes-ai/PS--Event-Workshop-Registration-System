"""
UI Theme & Design System - Event Registration Concurrency Monitor
Modern SaaS-inspired dark theme styling, reusable component generators,
and Plotly visualization layout templates.
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

# =============================================================================
# 1. MODERN SAAS DARK THEME STYLESHEET
# =============================================================================
MODERN_SAAS_CSS = """
<style>
/* ---------------- Global Reset & Typography ---------------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #F8FAFC;
}

:root {
    --bg-page: #0B0F19;
    --bg-card: #151D2F;
    --bg-card-hover: #1A243B;
    --border-subtle: #232F47;
    --border-focus: #3B82F6;
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    --accent-blue: #3B82F6;
    --accent-indigo: #6366F1;
    --accent-violet: #8B5CF6;
    --accent-emerald: #10B981;
    --accent-rose: #F43F5E;
    --accent-amber: #F59E0B;
}

/* Page background override */
.stApp {
    background-color: #0B0F19;
}

/* ---------------- Top SaaS Header ---------------- */
.saas-header {
    background: linear-gradient(180deg, #162035 0%, #101827 100%);
    border: 1px solid #23314E;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
}

.saas-header-text h1 {
    font-size: 1.85rem;
    font-weight: 800;
    color: #FFFFFF;
    margin: 0;
    letter-spacing: -0.025em;
}

.saas-header-text p {
    font-size: 0.95rem;
    color: #94A3B8;
    margin: 6px 0 0 0;
    font-weight: 400;
}

.saas-header-badge {
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.35);
    color: #60A5FA;
    font-size: 0.82rem;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 9999px;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

/* ---------------- KPI Metric Cards ---------------- */
.kpi-container {
    background: #151D2F;
    border: 1px solid #232F47;
    border-radius: 12px;
    padding: 18px 20px;
    position: relative;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    height: 100%;
}

.kpi-container:hover {
    transform: translateY(-2px);
    border-color: #3B82F6;
    box-shadow: 0 8px 18px -4px rgba(59, 130, 246, 0.15);
}

.kpi-top-bar {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

.kpi-label {
    font-size: 0.76rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94A3B8;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.kpi-value {
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1.1;
    color: #FFFFFF;
    margin: 4px 0 6px 0;
    letter-spacing: -0.02em;
}

.kpi-subtext {
    font-size: 0.82rem;
    color: #64748B;
    margin: 0;
}

/* ---------------- Event Grid Cards ---------------- */
.event-card {
    background: #151D2F;
    border: 1px solid #232F47;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    transition: transform 0.15s ease, border-color 0.15s ease;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.event-card:hover {
    border-color: #384A6E;
    transform: translateY(-2px);
}

.event-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
    gap: 12px;
}

.event-card-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0;
    line-height: 1.35;
}

.event-card-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 0.84rem;
    color: #94A3B8;
    margin: 12px 0 16px 0;
}

.event-card-meta-item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.event-capacity-bar {
    background: #1E293B;
    border-radius: 9999px;
    height: 7px;
    width: 100%;
    overflow: hidden;
    margin: 8px 0;
}

.event-capacity-fill {
    height: 100%;
    border-radius: 9999px;
    transition: width 0.3s ease;
}

/* ---------------- Badges & Pills ---------------- */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}

.badge-green {
    background-color: rgba(16, 185, 129, 0.12);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-amber {
    background-color: rgba(245, 158, 11, 0.12);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-red {
    background-color: rgba(244, 63, 94, 0.12);
    color: #FB7185;
    border: 1px solid rgba(244, 63, 94, 0.3);
}

.badge-blue {
    background-color: rgba(59, 130, 246, 0.12);
    color: #60A5FA;
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-indigo {
    background-color: rgba(99, 102, 241, 0.12);
    color: #818CF8;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

.badge-purple {
    background-color: rgba(139, 92, 246, 0.12);
    color: #C084FC;
    border: 1px solid rgba(139, 92, 246, 0.3);
}

.badge-slate {
    background-color: rgba(148, 163, 184, 0.1);
    color: #94A3B8;
    border: 1px solid rgba(148, 163, 184, 0.25);
}

/* ---------------- Concurrency Banners ---------------- */
.banner-safe {
    background: linear-gradient(90deg, rgba(16, 185, 129, 0.12) 0%, rgba(15, 23, 42, 0.6) 100%);
    border-left: 4px solid #10B981;
    border-top: 1px solid rgba(16, 185, 129, 0.25);
    border-right: 1px solid rgba(16, 185, 129, 0.25);
    border-bottom: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 18px;
}

.banner-safe-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #34D399;
    margin: 0 0 4px 0;
}

.banner-safe-desc {
    font-size: 0.86rem;
    color: #CBD5E1;
    margin: 0;
}

.banner-unsafe {
    background: linear-gradient(90deg, rgba(244, 63, 94, 0.14) 0%, rgba(15, 23, 42, 0.6) 100%);
    border-left: 4px solid #F43F5E;
    border-top: 1px solid rgba(244, 63, 94, 0.25);
    border-right: 1px solid rgba(244, 63, 94, 0.25);
    border-bottom: 1px solid rgba(244, 63, 94, 0.25);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 18px;
}

.banner-unsafe-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #FB7185;
    margin: 0 0 4px 0;
}

.banner-unsafe-desc {
    font-size: 0.86rem;
    color: #CBD5E1;
    margin: 0;
}

/* ---------------- Activity Feed Item ---------------- */
.activity-row {
    background: #151D2F;
    border: 1px solid #232F47;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: background-color 0.15s ease;
}

.activity-row:hover {
    background: #1A243B;
}

.activity-actor {
    font-weight: 600;
    color: #F8FAFC;
    font-size: 0.88rem;
}

.activity-details {
    color: #94A3B8;
    font-size: 0.82rem;
    margin-top: 2px;
}

.activity-time {
    color: #64748B;
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
    white-space: nowrap;
}

/* ---------------- Section Subheaders ---------------- */
.section-heading {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin: 28px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1E293B;
}

.section-heading h2 {
    font-size: 1.3rem;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0;
    letter-spacing: -0.015em;
}

.section-heading p {
    font-size: 0.86rem;
    color: #94A3B8;
    margin: 4px 0 0 0;
}

/* ---------------- Lifecycle Step Node ---------------- */
.lifecycle-step {
    background: #151D2F;
    border: 1px solid #232F47;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    height: 100%;
}

.lifecycle-step-num {
    display: inline-block;
    width: 26px;
    height: 26px;
    line-height: 26px;
    border-radius: 50%;
    background: rgba(59, 130, 246, 0.2);
    color: #60A5FA;
    font-weight: 700;
    font-size: 0.8rem;
    margin-bottom: 8px;
}

.lifecycle-step-title {
    font-weight: 700;
    color: #F8FAFC;
    font-size: 0.92rem;
    margin-bottom: 4px;
}

.lifecycle-step-desc {
    font-size: 0.78rem;
    color: #94A3B8;
}

/* ---------------- Sidebar Enhancements ---------------- */
[data-testid="stSidebar"] {
    background-color: #0E1424;
    border-right: 1px solid #1E293B;
}

.sidebar-brand {
    padding: 12px 4px 16px 4px;
    border-bottom: 1px solid #1E293B;
    margin-bottom: 16px;
}

.sidebar-brand-title {
    font-size: 1.25rem;
    font-weight: 800;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    gap: 8px;
    letter-spacing: -0.02em;
}

.sidebar-brand-subtitle {
    font-size: 0.78rem;
    color: #60A5FA;
    font-weight: 500;
    margin-top: 3px;
}

.sidebar-user-card {
    background: #151D2F;
    border: 1px solid #232F47;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 16px;
}

.sidebar-section-title {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748B;
    margin: 18px 0 8px 4px;
}
</style>
"""


# =============================================================================
# 2. REUSABLE COMPONENT GENERATORS
# =============================================================================
def inject_custom_css() -> None:
    """Inject the SaaS dark theme stylesheet into the Streamlit session."""
    st.markdown(MODERN_SAAS_CSS, unsafe_allow_html=True)


def render_saas_header(title: str, subtitle: str, badge_text: Optional[str] = None) -> None:
    """Render a clean SaaS top-of-page header."""
    badge_html = f'<div class="saas-header-badge">{html.escape(badge_text)}</div>' if badge_text else ""
    st.markdown(
        f"""
        <div class="saas-header">
            <div class="saas-header-text">
                <h1>{html.escape(title)}</h1>
                <p>{html.escape(subtitle)}</p>
            </div>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, description: Optional[str] = None, action_html: Optional[str] = None) -> None:
    """Render a clean section divider heading with optional action button/badge."""
    desc_html = f"<p>{html.escape(description)}</p>" if description else ""
    act_html = f"<div>{action_html}</div>" if action_html else ""
    st.markdown(
        f"""
        <div class="section-heading">
            <div>
                <h2>{html.escape(title)}</h2>
                {desc_html}
            </div>
            {act_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(
    label: str,
    value: Any,
    subtext: str = "",
    top_bar_color: str = "#3B82F6",
    value_color: str = "#FFFFFF",
) -> None:
    """Render a single modern SaaS KPI metric card."""
    st.markdown(
        f"""
        <div class="kpi-container">
            <div class="kpi-top-bar" style="background: {top_bar_color};"></div>
            <div class="kpi-label">{html.escape(label)}</div>
            <div class="kpi-value" style="color: {value_color};">{html.escape(str(value))}</div>
            <div class="kpi-subtext">{html.escape(subtext)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(status: str) -> str:
    """Return HTML for a status badge based on state string."""
    clean_s = status.upper().strip()
    if clean_s in ("CONFIRMED", "AVAILABLE", "SUCCESS", "PASS", "PUBLISHED", "PRESENT"):
        return f'<span class="badge badge-green">{html.escape(status)}</span>'
    elif clean_s in ("ALMOST FULL", "WAITLISTED", "WAITING", "QUEUED", "WARNING"):
        return f'<span class="badge badge-amber">{html.escape(status)}</span>'
    elif clean_s in ("FULL", "OVERBOOKED", "FAIL", "REJECTED", "CANCELLED", "ERROR"):
        return f'<span class="badge badge-red">{html.escape(status)}</span>'
    elif clean_s in ("STUDENT", "ACTIVE"):
        return f'<span class="badge badge-blue">{html.escape(status)}</span>'
    elif clean_s in ("ORGANIZER",):
        return f'<span class="badge badge-purple">{html.escape(status)}</span>'
    elif clean_s in ("ADMINISTRATOR", "ADMIN"):
        return f'<span class="badge badge-indigo">{html.escape(status)}</span>'
    return f'<span class="badge badge-slate">{html.escape(status)}</span>'


def render_dataframe(df: pd.DataFrame, **kwargs) -> None:
    """Safe cross-version wrapper for st.dataframe with responsive container width."""
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kwargs)


def get_plotly_dark_layout(title: str = "", height: int = 340) -> Dict[str, Any]:
    """Return unified dark theme layout configuration for Plotly charts."""
    return dict(
        title=dict(
            text=title,
            font=dict(color="#F8FAFC", size=14, family="Inter"),
            x=0.01,
            y=0.96,
        ),
        paper_bgcolor="#151D2F",
        plot_bgcolor="#151D2F",
        font=dict(color="#94A3B8", family="Inter"),
        margin=dict(l=40, r=20, t=50, b=40),
        height=height,
        xaxis=dict(
            gridcolor="#232F47",
            linecolor="#232F47",
            tickfont=dict(color="#94A3B8", size=11),
        ),
        yaxis=dict(
            gridcolor="#232F47",
            linecolor="#232F47",
            tickfont=dict(color="#94A3B8", size=11),
        ),
        legend=dict(
            font=dict(color="#F8FAFC", size=11),
            bgcolor="rgba(21, 29, 47, 0.6)",
        ),
    )
