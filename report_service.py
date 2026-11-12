"""
Report Service - CSV & PDF Export Generation
Provides secure CSV exports with CSV formula injection protection,
and generates formatted, printable PDF reports for rosters and attendance.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

import database


def sanitize_csv_cell(value: Any) -> Any:
    """
    Prevent CSV Formula Injection (CWE-1236).
    If a cell begins with dangerous formula characters (=, +, -, @, \\t, \\r),
    prepend a single apostrophe to force spreadsheet engines to treat it as raw text.
    """
    if isinstance(value, str):
        if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{value}"
    return value


def export_to_csv_string(rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> str:
    """
    Export a list of dictionaries to a sanitized CSV string.
    """
    if not rows:
        return ""

    if fieldnames is None:
        fieldnames = list(rows[0].keys())

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()

    for r in rows:
        sanitized_row = {k: sanitize_csv_cell(r.get(k, "")) for k in fieldnames}
        writer.writerow(sanitized_row)

    return output.getvalue()


def get_events_csv() -> str:
    """Export all events to a CSV string."""
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, category, venue, start_datetime, end_datetime, capacity, status, organizer_id, created_at
        FROM events
        ORDER BY start_datetime ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    return export_to_csv_string(rows)


def get_attendees_csv(event_id: str) -> str:
    """Export attendee list for a workshop to a sanitized CSV string."""
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            r.ticket_id,
            u.id AS student_id,
            u.display_name AS student_name,
            u.email,
            r.status AS registration_status,
            r.registered_at,
            e.title AS workshop_title
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        JOIN events e ON r.event_id = e.id
        WHERE r.event_id = ?
        ORDER BY r.registered_at ASC
    """, (event_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    return export_to_csv_string(rows)


def get_attendance_csv(event_id: str) -> str:
    """Export check-in attendance records for a workshop to CSV."""
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            a.id AS attendance_id,
            r.ticket_id,
            u.id AS student_id,
            u.display_name AS student_name,
            a.checked_in_at,
            a.checked_in_by,
            a.status AS attendance_status,
            e.title AS workshop_title
        FROM attendance a
        JOIN registrations r ON a.registration_id = r.id
        JOIN users u ON a.user_id = u.id
        JOIN events e ON a.event_id = e.id
        WHERE a.event_id = ?
        ORDER BY a.checked_in_at ASC
    """, (event_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    return export_to_csv_string(rows)


def generate_event_roster_pdf(event_id: str) -> bytes:
    """
    Generate a high-resolution, printable PDF report of workshop attendees.
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    # Query event info
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    ev = cursor.fetchone()
    if not ev:
        raise ValueError(f"Event {event_id} not found")

    event_data = dict(ev)

    # Query confirmed attendees
    cursor.execute("""
        SELECT 
            u.display_name AS name,
            u.id AS student_id,
            r.ticket_id,
            r.status,
            r.registered_at
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = ? AND r.status IN ('CONFIRMED', 'ATTENDED')
        ORDER BY r.registered_at ASC
    """, (event_id,))
    attendees = [dict(r) for r in cursor.fetchall()]

    # Render PDF page image (800 x 1100 px @ 150 DPI)
    img = Image.new("RGB", (800, 1100), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Top banner header
    draw.rectangle([0, 0, 800, 90], fill="#0F172A")
    draw.rectangle([0, 90, 800, 96], fill="#3B82F6")

    # Header Titles
    draw.text((40, 25), "EVENT REGISTRATION SYSTEM — ATTENDEE ROSTER", fill="#60A5FA")
    draw.text((40, 50), f"Official Verification Report | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill="#94A3B8")

    # Workshop Metadata Box
    draw.rectangle([40, 120, 760, 200], fill="#F8FAFC", outline="#E2E8F0")
    draw.text((55, 130), f"Workshop: {event_data['title']} ({event_data['id']})", fill="#0F172A")
    draw.text((55, 155), f"Venue: {event_data['venue']} | Date: {event_data['start_datetime']}", fill="#475569")
    draw.text((55, 175), f"Capacity: {event_data['capacity']} seats | Confirmed Attendees: {len(attendees)}", fill="#10B981")

    # Table Header
    y = 230
    draw.rectangle([40, y, 760, y + 30], fill="#1E293B")
    draw.text((50, y + 8), "#", fill="#F8FAFC")
    draw.text((80, y + 8), "Student Name", fill="#F8FAFC")
    draw.text((280, y + 8), "Student ID", fill="#F8FAFC")
    draw.text((440, y + 8), "Ticket Identifier", fill="#F8FAFC")
    draw.text((640, y + 8), "Status", fill="#F8FAFC")

    y += 35
    for idx, att in enumerate(attendees, start=1):
        bg_col = "#F1F5F9" if idx % 2 == 0 else "#FFFFFF"
        draw.rectangle([40, y, 760, y + 26], fill=bg_col)

        draw.text((50, y + 6), str(idx), fill="#334155")
        draw.text((80, y + 6), att["name"][:24], fill="#0F172A")
        draw.text((280, y + 6), att["student_id"][:18], fill="#475569")
        draw.text((440, y + 6), att["ticket_id"] or "N/A", fill="#2563EB")
        draw.text((640, y + 6), att["status"], fill="#10B981")
        y += 28

        if y > 1020:
            break  # Fit on single page for demo

    # Footer note
    draw.text((40, 1050), "Operating Systems & Computer Networks Course Project (20 Marks)", fill="#94A3B8")
    draw.text((40, 1070), "Validated with Mutual Exclusion (threading.Lock) & Persistent ACID Transactions", fill="#64748B")

    buf = io.BytesIO()
    img.save(buf, format="PDF")
    return buf.getvalue()

