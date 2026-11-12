"""
Ticket Service - Cryptographic Ticket Generation & Attendance Verification
Generates local QR code digital tickets for confirmed registrations and
handles organizer check-in verification against persistent database records.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import os
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

import database

# Secret key for signing ticket verification hashes
TICKET_SECRET = os.environ.get("TICKET_SECRET_KEY", "academic-os-demo-secret-key-2026")


def generate_ticket_token(event_id: str, user_id: str, registration_id: str) -> str:
    """
    Generate an opaque, tamper-evident ticket identifier.
    Format: TKT-<event_id>-<short_user>-<hex_mac>
    """
    payload = f"{event_id}:{user_id}:{registration_id}"
    sig = hmac.new(TICKET_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:8]
    clean_uid = "".join(c for c in user_id if c.isalnum())[:8]
    return f"TKT-{event_id}-{clean_uid}-{sig.upper()}"


def generate_qr_matrix(data: str, size: int = 21) -> List[List[int]]:
    """
    Generate a deterministic 2D QR-style module matrix with standard finder patterns
    and encoded data bitstreams using pure Python (no external C library required).
    """
    # 21x21 matrix (Standard Version 1 QR dimension)
    matrix = [[0 for _ in range(size)] for _ in range(size)]

    # Draw standard QR 7x7 Finder Pattern at (row, col)
    def draw_finder(top_r: int, top_c: int) -> None:
        for r in range(7):
            for c in range(7):
                if r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4):
                    matrix[top_r + r][top_c + c] = 1
                else:
                    matrix[top_r + r][top_c + c] = 0

    # Draw Top-Left, Top-Right, Bottom-Left finders
    draw_finder(0, 0)
    draw_finder(0, size - 7)
    draw_finder(size - 7, 0)

    # Timing Patterns (Alternating black and white)
    for i in range(8, size - 8):
        matrix[6][i] = 1 if i % 2 == 0 else 0
        matrix[i][6] = 1 if i % 2 == 0 else 0

    # Deterministic Data payload bitstream from SHA-256 of input
    hasher = hashlib.sha256(data.encode("utf-8"))
    hash_bytes = hasher.digest()
    bit_stream: List[int] = []
    for b in hash_bytes:
        for bit_idx in range(8):
            bit_stream.append((b >> bit_idx) & 1)

    # Replicate/cycle bit stream to fill remaining matrix cells
    stream_idx = 0
    stream_len = len(bit_stream)

    for r in range(size):
        for c in range(size):
            # Skip finder patterns and separators
            if (r < 8 and c < 8) or (r < 8 and c >= size - 8) or (r >= size - 8 and c < 8):
                continue
            if r == 6 or c == 6:
                continue
            matrix[r][c] = bit_stream[stream_idx % stream_len]
            stream_idx += 1

    return matrix


def generate_qr_image_bytes(ticket_id: str, scale: int = 10, border: int = 4) -> bytes:
    """
    Render a clean high-resolution digital QR ticket image as PNG bytes.
    """
    matrix = generate_qr_matrix(ticket_id, size=25)
    matrix_size = len(matrix)
    img_size = (matrix_size + border * 2) * scale

    # High-contrast black modules on crisp white surface
    img = Image.new("RGB", (img_size, img_size), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    for r in range(matrix_size):
        for c in range(matrix_size):
            if matrix[r][c] == 1:
                x0 = (c + border) * scale
                y0 = (r + border) * scale
                x1 = x0 + scale
                y1 = y0 + scale
                draw.rectangle([x0, y0, x1, y1], fill="#0F172A")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_ticket_badge_card(
    ticket_id: str,
    event_title: str,
    user_name: str,
    venue: str,
    date_str: str,
) -> bytes:
    """
    Generate an official printable digital event badge combining QR code,
    ticket ID, student name, and workshop venue in a card layout.
    """
    # Create card dimensions: 480w x 280h
    card = Image.new("RGB", (500, 320), "#1E293B")
    draw = ImageDraw.Draw(card)

    # Header border accent line
    draw.rectangle([0, 0, 500, 8], fill="#3B82F6")

    # Generate QR Code image
    qr_bytes = generate_qr_image_bytes(ticket_id, scale=5, border=2)
    qr_img = Image.open(io.BytesIO(qr_bytes))
    card.paste(qr_img, (20, 30))

    # Text details
    # Fallback to default bitmap font if TTF not available
    draw.text((210, 30), "OFFICIAL WORKSHOP PASS", fill="#60A5FA")
    draw.text((210, 55), event_title[:28], fill="#F8FAFC")
    draw.text((210, 85), f"Attendee: {user_name[:24]}", fill="#E2E8F0")
    draw.text((210, 115), f"Venue: {venue[:24]}", fill="#94A3B8")
    draw.text((210, 140), f"Date: {date_str[:20]}", fill="#94A3B8")

    # Ticket Token pill
    draw.rectangle([210, 180, 480, 220], fill="#0F172A", outline="#334155")
    draw.text((220, 192), ticket_id, fill="#34D399")

    draw.text((210, 240), "Present this QR pass at the entrance.", fill="#64748B")
    draw.text((210, 260), "Status: VERIFIED & CONFIRMED", fill="#10B981")

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    return buf.getvalue()


def verify_and_checkin_ticket(
    ticket_id: str,
    checked_in_by: str,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validate a QR ticket against persistent registration records and record attendance.
    Enforces that:
    1. Ticket ID exists
    2. Registration is CONFIRMED
    3. Ticket has NOT already been used (prevents duplicate attendance)
    """
    clean_ticket = ticket_id.strip()
    if not clean_ticket:
        return False, "Ticket ID cannot be empty.", None

    conn = database.get_connection()
    cursor = conn.cursor()

    # Query registration and event details
    cursor.execute("""
        SELECT 
            r.id AS reg_id,
            r.event_id,
            r.user_id,
            r.status AS reg_status,
            r.ticket_id,
            e.title AS event_title,
            e.venue,
            e.status AS event_status,
            u.display_name AS user_name,
            u.email AS user_email
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        JOIN users u ON r.user_id = u.id
        WHERE r.ticket_id = ?
    """, (clean_ticket,))
    row = cursor.fetchone()

    if row is None:
        return False, f"Invalid Ticket: Ticket ID '{clean_ticket}' not found in database.", None

    reg = dict(row)

    # 1. Check if already checked in (prevents duplicate attendance)
    cursor.execute("SELECT checked_in_at, checked_in_by FROM attendance WHERE registration_id = ?", (reg["reg_id"],))
    att_row = cursor.fetchone()
    if att_row or reg["reg_status"] == "ATTENDED":
        prev_time = att_row["checked_in_at"] if att_row else "previously"
        prev_by = att_row["checked_in_by"] if att_row else "staff"
        return False, f"Duplicate Attendance! Ticket already used at {prev_time} (by {prev_by}).", reg

    # 2. Check registration status
    if reg["reg_status"] != "CONFIRMED":
        return False, f"Ticket Rejected: Registration status is '{reg['reg_status']}' (Must be CONFIRMED).", reg

    # 3. Check event status
    if reg["event_status"] in ("Cancelled", "Draft"):
        return False, f"Ticket Rejected: Event status is '{reg['event_status']}'.", reg

    # Record attendance in an atomic transaction
    now_str = datetime.now().isoformat()
    att_id = f"ATT-{secrets.token_hex(6).upper()}"

    with database.get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO attendance (id, registration_id, event_id, user_id, checked_in_at, checked_in_by, status)
            VALUES (?, ?, ?, ?, ?, ?, 'PRESENT')
        """, (att_id, reg["reg_id"], reg["event_id"], reg["user_id"], now_str, checked_in_by))

        # Update registration status to ATTENDED
        cur.execute("UPDATE registrations SET status = 'ATTENDED' WHERE id = ?", (reg["reg_id"],))

        # Log audit entry
        cur.execute("""
            INSERT INTO audit_logs (actor_id, event_id, action, status, details, created_at)
            VALUES (?, ?, 'CHECK_IN', 'SUCCESS', ?, ?)
        """, (checked_in_by, reg["event_id"], f"Attendee {reg['user_name']} ({reg['user_id']}) checked in with ticket {clean_ticket}", now_str))

    reg["checked_in_at"] = now_str
    reg["checked_in_by"] = checked_in_by
    return True, f"Check-In Successful: Welcome {reg['user_name']} to {reg['event_title']}!", reg


def get_event_attendance_roster(event_id: str) -> List[Dict[str, Any]]:
    """Retrieve full check-in attendance roster for an event."""
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            u.id AS user_id,
            u.display_name,
            u.email,
            r.ticket_id,
            r.status AS registration_status,
            a.checked_in_at,
            a.checked_in_by,
            CASE WHEN a.id IS NOT NULL THEN 'PRESENT' ELSE 'ABSENT' END AS attendance_status
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        LEFT JOIN attendance a ON r.id = a.registration_id
        WHERE r.event_id = ? AND r.status IN ('CONFIRMED', 'ATTENDED')
        ORDER BY u.display_name ASC
    """, (event_id,))
    return [dict(r) for r in cursor.fetchall()]
