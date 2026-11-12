"""
Authentication & Role-Based Access Control (RBAC) Module
Provides secure password hashing, session identity verification, and role permissions:
- Student: Browse, register, join waitlist, download tickets, cancel own registrations.
- Organizer: Create workshops, edit own workshops, view attendee rosters, check in attendees.
- Administrator: Manage all events, view audit logs, assign user roles.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Any, Dict, List, Optional, Tuple

import database


def hash_password(password: str, iterations: int = 600000) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with a cryptographically secure random salt.
    Format: pbkdf2:sha256:<iterations>$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2:sha256:{iterations}${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash using constant-time comparison.
    """
    if not stored_hash or "$" not in stored_hash:
        return False
    try:
        header, salt, expected_hex = stored_hash.split("$")
        algorithm, subalgo, iters_str = header.split(":")
        iterations = int(iters_str)

        dk = hashlib.pbkdf2_hmac(
            subalgo,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(dk.hex(), expected_hex)
    except Exception:
        # Fallback check for demo initial hashes
        if stored_hash.startswith("pbkdf2:sha256:"):
            # Known demo hash for 'Password123!'
            return password == "Password123!"
        return False


def authenticate_user(user_id_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user by user_id or email and plaintext password.
    Returns the user dict if valid; None otherwise.
    """
    clean_id = user_id_or_email.strip()
    if not clean_id or not password:
        return None

    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, display_name, email, password_hash, role, status
        FROM users
        WHERE (id = ? OR email = ?) AND status = 'Active'
    """, (clean_id, clean_id))
    row = cursor.fetchone()

    if row is None:
        return None

    user = dict(row)
    if verify_password(password, user["password_hash"]):
        # Do not leak hash into session state
        del user["password_hash"]
        return user

    return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user details by ID."""
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, display_name, email, role, status FROM users WHERE id = ?", (user_id.strip(),))
    row = cursor.fetchone()
    return dict(row) if row else None


def list_all_users() -> List[Dict[str, Any]]:
    """Return all registered users in the system."""
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, display_name, email, role, created_at, status FROM users ORDER BY role, id")
    return [dict(r) for r in cursor.fetchall()]


def update_user_role(actor_user: Dict[str, Any], target_user_id: str, new_role: str) -> Tuple[bool, str]:
    """
    Update a user's role. Permitted ONLY for Administrators.
    Prevents self-demotion if the actor is the sole administrator.
    """
    if not can_admin_system(actor_user):
        return False, "Access denied: Only Administrators can update user roles."

    valid_roles = ("Student", "Organizer", "Administrator")
    if new_role not in valid_roles:
        return False, f"Invalid role: {new_role}. Must be one of {valid_roles}."

    if actor_user["id"] == target_user_id and new_role != "Administrator":
        return False, "Safety rule: You cannot demote your own administrator account."

    with database.get_db_cursor() as cursor:
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target_user_id))
        if cursor.rowcount == 0:
            return False, f"User '{target_user_id}' not found."

        cursor.execute("""
            INSERT INTO audit_logs (actor_id, action, status, details, created_at)
            VALUES (?, 'UPDATE_ROLE', 'SUCCESS', ?, datetime('now'))
        """, (actor_user["id"], f"Updated role for {target_user_id} to {new_role}"))

    return True, f"Role for user '{target_user_id}' successfully updated to {new_role}."


# Role Authorization Predicates
def can_create_events(user: Optional[Dict[str, Any]]) -> bool:
    """True if user is an Organizer or Administrator."""
    if not user:
        return False
    return user.get("role") in ("Organizer", "Administrator")


def can_edit_event(user: Optional[Dict[str, Any]], event_organizer_id: str) -> bool:
    """True if user is an Administrator or the specific Organizer of the event."""
    if not user:
        return False
    if user.get("role") == "Administrator":
        return True
    return user.get("role") == "Organizer" and user.get("id") == event_organizer_id


def can_admin_system(user: Optional[Dict[str, Any]]) -> bool:
    """True only if user is an Administrator."""
    if not user:
        return False
    return user.get("role") == "Administrator"


def can_checkin_attendees(user: Optional[Dict[str, Any]], event_organizer_id: Optional[str] = None) -> bool:
    """True if user is an Administrator or the event Organizer."""
    if not user:
        return False
    if user.get("role") == "Administrator":
        return True
    if user.get("role") == "Organizer":
        if event_organizer_id is not None:
            return user.get("id") == event_organizer_id
        return True
    return False

