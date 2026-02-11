"""
Clean Database Initialization
"""

import sqlite3
import os

DB_PATH = "stormops_cache.db"


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT UNIQUE,
            org_name TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO tenants (tenant_id, org_name, status)
        VALUES ('demo-tenant', 'Demo Roofing Company', 'active')
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            storm_type TEXT,
            severity TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            affected_zips TEXT,
            tenant_id TEXT DEFAULT 'demo-tenant',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        INSERT INTO storms (id, name, status, storm_type, severity, affected_zips, tenant_id)
        VALUES ('demo-storm', 'DFW Storm-24', 'active', 'hail', 'severe', '75001,75002,75007,75010,75024,75034,75035,75093,75201,75204,75205,75225,75230,75234,75240,75248,75287', 'demo-tenant')
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS earth2_impact_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id TEXT UNIQUE,
            storm_id TEXT,
            zip_code TEXT NOT NULL,
            hail_size_inches REAL DEFAULT 0,
            wind_speed_mph REAL DEFAULT 0,
            damage_propensity_score REAL DEFAULT 0,
            estimated_roofs INTEGER DEFAULT 0,
            lead_value DECIMAL(12,2) DEFAULT 0,
            risk_level TEXT DEFAULT 'Medium',
            latitude REAL,
            longitude REAL,
            center_lat REAL DEFAULT 0,
            center_lon REAL DEFAULT 0,
            FOREIGN KEY (storm_id) REFERENCES storms(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id TEXT UNIQUE,
            storm_id TEXT,
            address TEXT,
            city TEXT,
            zip_code TEXT,
            hail_size REAL,
            roof_age INTEGER,
            property_value DECIMAL(12,2),
            lead_score REAL DEFAULT 0,
            conversion_probability REAL DEFAULT 0,
            priority_tier TEXT DEFAULT 'C',
            trigger_description TEXT,
            phone TEXT,
            email TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_contact TIMESTAMP,
            persona TEXT DEFAULT 'realist',
            voice_ready BOOLEAN DEFAULT 0,
            ai_confidence REAL DEFAULT 0,
            ai_reasoning TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id TEXT UNIQUE,
            storm_id TEXT,
            tenant_id TEXT,
            name TEXT,
            zip_code TEXT,
            property_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            assigned_crew TEXT,
            total_doors INTEGER DEFAULT 0,
            completed_doors INTEGER DEFAULT 0,
            estimated_value DECIMAL(12,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (storm_id) REFERENCES storms(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            lead_id INTEGER,
            route_id INTEGER,
            address TEXT,
            status TEXT DEFAULT 'pending',
            claim_amount DECIMAL(12,2) DEFAULT 0,
            damage_type TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id),
            FOREIGN KEY (route_id) REFERENCES routes(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markov_zip_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            storm_id TEXT NOT NULL,
            zip_code TEXT NOT NULL,
            current_state TEXT DEFAULT 'pre_event',
            prob_to_recovery REAL DEFAULT 0,
            estimated_tam_usd REAL DEFAULT 0,
            state_entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transitions_count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (storm_id) REFERENCES storms(id)
        )
    """)

    # Create properties table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id TEXT UNIQUE,
            address TEXT,
            zip_code TEXT,
            latitude REAL,
            longitude REAL,
            census_tract_geoid TEXT,
            tenant_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create property_identities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS property_identities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identity_id TEXT UNIQUE,
            tenant_id TEXT,
            property_id TEXT,
            confidence_score DECIMAL(5, 4),
            resolution_method TEXT,
            household_id TEXT,
            decision_maker_name TEXT,
            decision_maker_email TEXT,
            decision_maker_phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (property_id) REFERENCES properties(property_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_calls (
            id TEXT PRIMARY KEY,
            lead_id TEXT,
            phone_number TEXT,
            status TEXT,
            persona TEXT,
            intent_detected TEXT,
            transcript TEXT,
            sentiment_score REAL,
            disposition TEXT,
            callback_scheduled TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            duration_seconds INTEGER DEFAULT 0,
            retell_call_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sidebar_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            storm_id TEXT NOT NULL,
            action_id TEXT UNIQUE,
            action_type TEXT,
            action_status TEXT DEFAULT 'proposed',
            ai_confidence REAL DEFAULT 0,
            ai_reasoning TEXT,
            action_params TEXT,
            proposed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (storm_id) REFERENCES storms(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attribution_touchpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            storm_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            property_id TEXT NOT NULL,
            markov_credit REAL DEFAULT 0,
            shapley_credit REAL DEFAULT 0,
            hybrid_credit REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (storm_id) REFERENCES storms(id)
        )
    """)

    # Add sample data
    sample_zips = [
        ("75001", 1.75, 68, 0.82, 2847, 22776000, "High"),
        ("75002", 2.0, 72, 0.88, 3421, 34105000, "Critical"),
        ("75007", 1.5, 65, 0.75, 2156, 17248000, "Medium"),
        ("75010", 1.25, 58, 0.62, 1876, 13132000, "Medium"),
        ("75024", 2.25, 75, 0.91, 4521, 54252000, "Critical"),
        ("75034", 1.875, 70, 0.85, 3892, 46704000, "High"),
        ("75035", 1.625, 66, 0.78, 2987, 26913000, "High"),
        ("75093", 1.375, 62, 0.68, 2245, 19182500, "Medium"),
        ("75201", 2.5, 78, 0.95, 5124, 71736000, "Critical"),
        ("75204", 2.125, 73, 0.89, 4256, 55228000, "Critical"),
        ("75205", 1.75, 69, 0.83, 3156, 40968000, "High"),
        ("75225", 1.9, 71, 0.86, 3678, 47714000, "High"),
        ("75230", 2.375, 76, 0.93, 4892, 68288000, "Critical"),
        ("75234", 1.45, 64, 0.72, 2456, 19648000, "Medium"),
        ("75240", 2.0, 72, 0.88, 4125, 53625000, "Critical"),
        ("75248", 1.6, 67, 0.79, 2945, 26505000, "Medium"),
        ("75252", 1.8, 70, 0.84, 3567, 42724000, "High"),
        ("75287", 1.55, 65, 0.76, 2678, 24002000, "Medium"),
    ]

    import random

    personas = ["realist", "skeptic", "visionary", "urgent", "quality"]

    for zip_code, hail, wind, damage, roofs, value, risk in sample_zips:
        zone_id = f"zone-{zip_code}"
        lat = 32.7767 + (hash(zip_code) % 100) / 1000.0
        lon = -96.7970 + (hash(zip_code) % 100) / 1000.0

        cursor.execute(
            """
            INSERT INTO earth2_impact_zones (storm_id, zone_id, zip_code, hail_size_inches, wind_speed_mph, damage_propensity_score, estimated_roofs, lead_value, risk_level, center_lat, center_lon)
            VALUES ('demo-storm', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (zone_id, zip_code, hail, wind, damage, roofs, value, risk, lat, lon),
        )

    lead_templates = [
        (
            "123 Oak St",
            "Dallas",
            "75201",
            2.0,
            18,
            485000,
            "High",
            "Direct hail impact - immediate inspection needed",
        ),
        (
            "456 Maple Ave",
            "Dallas",
            "75204",
            2.25,
            12,
            625000,
            "High",
            "Critical damage - adjacent to major claim",
        ),
        (
            "789 Pine Rd",
            "Plano",
            "75024",
            2.0,
            22,
            520000,
            "High",
            "Older roof + large trees - high risk",
        ),
        (
            "321 Elm Dr",
            "Addison",
            "75001",
            1.75,
            15,
            385000,
            "Medium",
            "Commercial property - multi-unit",
        ),
        (
            "654 Cedar Ln",
            "Frisco",
            "75034",
            1.875,
            8,
            725000,
            "High",
            "Premium neighborhood - fast sale cycle",
        ),
        (
            "987 Birch Way",
            "Dallas",
            "75230",
            2.375,
            14,
            890000,
            "Critical",
            "High-value estate - all cash buyer",
        ),
        (
            "147 Ash Ct",
            "Richardson",
            "75082",
            1.5,
            20,
            345000,
            "Medium",
            "Rental property - investor lead",
        ),
        (
            "258 Spruce St",
            "Dallas",
            "75240",
            2.0,
            11,
            475000,
            "High",
            "Insurance claim in progress",
        ),
        (
            "369 Willow Ave",
            "Garland",
            "75044",
            1.25,
            25,
            295000,
            "Medium",
            "HOA managed - approval required",
        ),
        (
            "483 Sequoia Dr",
            "Plano",
            "75093",
            1.375,
            16,
            420000,
            "Medium",
            "Referral from completed job",
        ),
    ]

    for i, (addr, city, zip_code, hail, age, value, tier, trigger) in enumerate(
        lead_templates
    ):
        score = min(100, 50 + (hail * 15) + (value / 20000) + ((25 - age) * 0.5))
        conv_prob = (
            score
            / 100
            * (0.7 if tier == "Critical" else 0.5 if tier == "High" else 0.3)
        )
        phone = f"+1555{random.randint(1000000, 9999999)}"

        cursor.execute(
            """
            INSERT INTO leads (lead_id, storm_id, address, city, zip_code, hail_size, roof_age, property_value, lead_score, conversion_probability, priority_tier, trigger_description, phone, persona, voice_ready, ai_confidence, ai_reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                f"lead-{i + 1:03d}",
                "demo-storm",
                addr,
                city,
                zip_code,
                hail,
                age,
                value,
                round(score, 1),
                round(conv_prob, 2),
                tier,
                trigger,
                phone,
                random.choice(personas),
                1 if random.random() > 0.3 else 0,
                round(random.uniform(0.75, 0.98), 2),
                f"High damage score ({damage * 100:.0f}%), {tier} tier property, {trigger[:30]}...",
            ),
        )

    # Add sample attribution touchpoints
    cursor.execute("""
        INSERT INTO attribution_touchpoints (storm_id, channel, property_id, markov_credit, shapley_credit, hybrid_credit)
        VALUES 
            ('demo-storm', 'door', 'lead-001', 0.25, 0.20, 0.22),
            ('demo-storm', 'sms', 'lead-002', 0.15, 0.12, 0.14),
            ('demo-storm', 'email', 'lead-003', 0.10, 0.08, 0.09),
            ('demo-storm', 'social', 'lead-004', 0.20, 0.18, 0.19)
    """)

    # Add sample sidebar actions
    cursor.execute("""
        INSERT OR IGNORE INTO sidebar_actions (tenant_id, storm_id, action_id, action_type, action_status, ai_confidence, ai_reasoning, action_params, proposed_at)
        VALUES
            ('demo-tenant', 'demo-storm', 'action-001', 'load_storm', 'proposed', 0.92, 'Load DFW Storm-24 to identify hot zones', '{}', CURRENT_TIMESTAMP),
            ('demo-tenant', 'demo-storm', 'action-002', 'select_zones', 'proposed', 0.87, 'Select 3 high-impact ZIPs from zones 75201, 75204, 75224', '{}', CURRENT_TIMESTAMP),
            ('demo-tenant', 'demo-storm', 'action-003', 'build_routes', 'proposed', 0.78, 'Build 2 optimized routes for 1500 doors', '{}', CURRENT_TIMESTAMP),
            ('demo-tenant', 'demo-storm', 'action-004', 'file_claims', 'proposed', 0.65, 'Process insurance claims for 2 completed jobs', '{}', CURRENT_TIMESTAMP)
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")
    print(
        f"Storms: 1 | Impact Zones: {len(sample_zips)} | Leads: {len(lead_templates)}"
    )
    print(f"Markov States: 12 | Routes: 3 | Jobs: 4")


if __name__ == "__main__":
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
    except:
        pass
    init_database()
    else:
        init_database()
