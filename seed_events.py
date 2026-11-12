"""
Seed Events Script - Expands Event & Workshop Registration System
Adds 20 realistic, demonstration-ready academic workshops across diverse computer science
and professional disciplines without deleting or corrupting existing registrations or events.

Idempotent and Transactional:
- Safe to run repeatedly without creating duplicate records.
- Preserves existing database records (users, registrations, tickets, attendance).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import database

# 20 Realistic Demonstration Events as specified in academic requirements
SAMPLE_EVENTS_SPEC: List[Dict[str, Any]] = [
    {
        "id": "EVT-01",
        "title": "Python Programming Bootcamp",
        "category": "Programming",
        "capacity": 50,
        "venue": "Turing Computing Lab 101 (Demo Venue)",
        "description": "Comprehensive hands-on training in modern Python programming, object-oriented design, functional idioms, and idiomatic Pythonic best practices.",
        "days_ahead": 7,
        "duration_hours": 3,
    },
    {
        "id": "EVT-02",
        "title": "Full-Stack Web Development",
        "category": "Web Development",
        "capacity": 40,
        "venue": "Berners-Lee Web Studio 204 (Demo Venue)",
        "description": "End-to-end full-stack development workshop covering RESTful API architecture, responsive frontend design, and asynchronous client-server communication.",
        "days_ahead": 9,
        "duration_hours": 4,
    },
    {
        "id": "EVT-03",
        "title": "AI & Machine Learning Workshop",
        "category": "Artificial Intelligence",
        "capacity": 35,
        "venue": "McCarthy AI Center 302 (Demo Venue)",
        "description": "Supervised and unsupervised learning, mathematical optimization, feature engineering, and model evaluation with scikit-learn.",
        "days_ahead": 11,
        "duration_hours": 3,
    },
    {
        "id": "EVT-04",
        "title": "Generative AI and Prompt Engineering",
        "category": "Artificial Intelligence",
        "capacity": 30,
        "venue": "Hinton Neural Suite 105 (Demo Venue)",
        "description": "Architectures of Large Language Models (LLMs), attention mechanisms, few-shot prompting strategies, retrieval-augmented generation (RAG), and ethics.",
        "days_ahead": 13,
        "duration_hours": 3,
    },
    {
        "id": "EVT-05",
        "title": "Data Structures & Algorithms",
        "category": "Programming",
        "capacity": 60,
        "venue": "Knuth Algorithmics Hall A (Demo Venue)",
        "description": "Asymptotic analysis, balanced search trees, graph traversals (BFS/DFS), dynamic programming patterns, and memory complexity tradeoffs.",
        "days_ahead": 15,
        "duration_hours": 4,
    },
    {
        "id": "EVT-06",
        "title": "Cybersecurity Essentials",
        "category": "Cybersecurity",
        "capacity": 40,
        "venue": "Diffie-Hellman Security Lab 401 (Demo Venue)",
        "description": "Core cybersecurity fundamentals: cryptographic primitives, symmetric and asymmetric ciphers, public-key infrastructure (PKI), and defense-in-depth.",
        "days_ahead": 17,
        "duration_hours": 3,
    },
    {
        "id": "EVT-07",
        "title": "Ethical Hacking Workshop",
        "category": "Cybersecurity",
        "capacity": 25,
        "venue": "Shamir Defensive Cyber Lab 405 (Demo Venue)",
        "description": "Penetration testing methodologies, vulnerability assessment, web application security (OWASP Top 10), and responsible disclosure frameworks.",
        "days_ahead": 19,
        "duration_hours": 3,
    },
    {
        "id": "EVT-08",
        "title": "Cloud Computing with AWS",
        "category": "Cloud Computing",
        "capacity": 35,
        "venue": "Lamport Cloud Auditorium 210 (Demo Venue)",
        "description": "Cloud infrastructure design on AWS: Elastic Compute Cloud (EC2), S3 storage partitioning, VPC networking, security groups, and cost optimization.",
        "days_ahead": 21,
        "duration_hours": 4,
    },
    {
        "id": "EVT-09",
        "title": "DevOps and CI/CD Fundamentals",
        "category": "DevOps",
        "capacity": 30,
        "venue": "Kernighan Build Lab 112 (Demo Venue)",
        "description": "Continuous Integration and Continuous Deployment pipelines, automated linting and testing stages, infrastructure-as-code, and release management.",
        "days_ahead": 23,
        "duration_hours": 3,
    },
    {
        "id": "EVT-10",
        "title": "Git & GitHub Masterclass",
        "category": "Developer Tools",
        "capacity": 50,
        "venue": "Torvalds Open-Source Lab 301 (Demo Venue)",
        "description": "Advanced Git internals: DAG commit trees, branch merging vs rebase, interactive staging, submodules, resolving complex merge conflicts, and GitHub flow.",
        "days_ahead": 25,
        "duration_hours": 3,
    },
    {
        "id": "EVT-11",
        "title": "Docker and Kubernetes Workshop",
        "category": "DevOps",
        "capacity": 30,
        "venue": "Containerization Suite 205 (Demo Venue)",
        "description": "Container virtualization: Dockerfile optimization, multi-stage builds, container networks, Kubernetes pods, deployments, services, and ingress control.",
        "days_ahead": 27,
        "duration_hours": 4,
    },
    {
        "id": "EVT-12",
        "title": "Database Design with SQL",
        "category": "Databases",
        "capacity": 40,
        "venue": "Codd Relational Data Lab 108 (Demo Venue)",
        "description": "Relational schema design: 1NF through BCNF normalization, primary and foreign key constraints, index selection, ACID transactions, and query plans.",
        "days_ahead": 29,
        "duration_hours": 3,
    },
    {
        "id": "EVT-13",
        "title": "MongoDB Hands-on Workshop",
        "category": "Databases",
        "capacity": 35,
        "venue": "NoSQL Systems Lab 110 (Demo Venue)",
        "description": "Document-oriented NoSQL databases: BSON schemas, aggregation pipelines, replica sets, sharding architectures, and schema design for semi-structured data.",
        "days_ahead": 31,
        "duration_hours": 3,
    },
    {
        "id": "EVT-14",
        "title": "Computer Networks Fundamentals",
        "category": "Networking",
        "capacity": 45,
        "venue": "Cerf-Kahn Networking Hall 305 (Demo Venue)",
        "description": "OSI 7-layer and TCP/IP reference models: packet switching, IP subnetting, TCP flow/congestion control, DNS resolution, and Wireshark traffic analysis.",
        "days_ahead": 33,
        "duration_hours": 3,
    },
    {
        "id": "EVT-15",
        "title": "Operating Systems and Multithreading",
        "category": "Operating Systems",
        "capacity": 35,
        "venue": "Tanenbaum Kernel Lab 310 (Demo Venue)",
        "description": "Kernel architecture, process control blocks (PCBs), CPU scheduling algorithms, virtual memory paging, multithreading, and mutex critical sections.",
        "days_ahead": 35,
        "duration_hours": 4,
    },
    {
        "id": "EVT-16",
        "title": "Competitive Programming Contest",
        "category": "Competition",
        "capacity": 100,
        "venue": "Campus Grand Arena North (Demo Venue)",
        "description": "Timed problem-solving competition: algorithmic problem sets, fast I/O techniques, dynamic programming, number theory, and mathematical insights.",
        "days_ahead": 38,
        "duration_hours": 5,
    },
    {
        "id": "EVT-17",
        "title": "Hackathon 2026",
        "category": "Hackathon",
        "capacity": 150,
        "venue": "Innovation Complex Great Hall (Demo Venue)",
        "description": "24-hour collaborative sprint: teams prototype and present software solutions addressing sustainability, healthcare, and education challenges.",
        "days_ahead": 42,
        "duration_hours": 24,
    },
    {
        "id": "EVT-18",
        "title": "Resume Building and Interview Preparation",
        "category": "Career Development",
        "capacity": 60,
        "venue": "Career Advancement Hall 102 (Demo Venue)",
        "description": "Technical career guidance: crafting impactful project resumes, whiteboarding system design challenges, behavioral STAR technique, and mock interviews.",
        "days_ahead": 45,
        "duration_hours": 3,
    },
    {
        "id": "EVT-19",
        "title": "UI/UX Design Workshop",
        "category": "Design",
        "capacity": 35,
        "venue": "HCI Design Studio 201 (Demo Venue)",
        "description": "User experience principles: wireframing, high-fidelity interactive prototyping, WCAG accessibility standards, user testing, and visual hierarchy.",
        "days_ahead": 48,
        "duration_hours": 3,
    },
    {
        "id": "EVT-20",
        "title": "Startup and Entrepreneurship Meetup",
        "category": "Entrepreneurship",
        "capacity": 80,
        "venue": "Founder Incubation Auditorium (Demo Venue)",
        "description": "Technology commercialization: product-market fit evaluation, lean canvas modeling, minimum viable products (MVPs), seed pitch decks, and angel networking.",
        "days_ahead": 52,
        "duration_hours": 4,
    },
]


def seed_events(db_path: str = database.DATABASE_FILE) -> Tuple[int, int, int]:
    """
    Seed the 20 sample events into SQLite database safely and idempotently.
    
    Returns:
    - Tuple[int, int, int]: (added_count, skipped_count, total_events_in_db)
    """
    # Ensure base schema is present without dropping data
    database.init_db(db_path, reset=False)

    conn = database.get_connection(db_path)
    cursor = conn.cursor()

    # Verify organizer prof_turner exists to satisfy foreign key constraint
    cursor.execute("SELECT id FROM users WHERE id = 'prof_turner'")
    organizer = cursor.fetchone()
    organizer_id = organizer["id"] if organizer else "admin_sys"

    now_base = datetime.now()
    added_count = 0
    skipped_count = 0

    with database.get_db_cursor(db_path) as cur:
        for spec in SAMPLE_EVENTS_SPEC:
            event_id = spec["id"]
            title = spec["title"]

            # Idempotency check: look up by ID or by exact Title
            cur.execute("SELECT id FROM events WHERE id = ? OR title = ?", (event_id, title))
            existing = cur.fetchone()

            if existing:
                skipped_count += 1
                continue

            # Compute realistic future dates
            start_dt = now_base + timedelta(days=spec["days_ahead"], hours=2)
            end_dt = start_dt + timedelta(hours=spec["duration_hours"])
            start_str = start_dt.strftime("%Y-%m-%d %H:%M:00")
            end_str = end_dt.strftime("%Y-%m-%d %H:%M:00")
            now_iso = now_base.isoformat()

            cur.execute("""
                INSERT INTO events (
                    id, title, description, category, venue, start_datetime, end_datetime,
                    capacity, status, organizer_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Published', ?, ?, ?)
            """, (
                event_id,
                title,
                spec["description"],
                spec["category"],
                spec["venue"],
                start_str,
                end_str,
                spec["capacity"],
                organizer_id,
                now_iso,
                now_iso,
            ))

            cur.execute("""
                INSERT INTO audit_logs (actor_id, event_id, action, status, details, created_at)
                VALUES (?, ?, 'SEED_EVENT', 'SUCCESS', ?, ?)
            """, (organizer_id, event_id, f"Seeded sample workshop: {title} (Capacity: {spec['capacity']})", now_iso))

            added_count += 1

    # Fetch final count
    cursor.execute("SELECT COUNT(*) AS total FROM events")
    total_events = cursor.fetchone()["total"]

    return added_count, skipped_count, total_events


def main() -> int:
    """CLI execution entry point."""
    print("=" * 70)
    print("EVENT REGISTRATION SYSTEM — SAMPLE EVENTS SEEDER")
    print("Populating 20 Realistic Demonstration Events")
    print("=" * 70)

    added, skipped, total = seed_events()

    print(f"\n[OK] Events Newly Added:          {added}")
    print(f"[OK] Duplicate Events Prevented:   {skipped}")
    print(f"[OK] Total Events in Database:     {total}")
    print("=" * 70)
    print("Seeding completed successfully without database reset.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

