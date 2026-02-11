"""
Markov State Engine
Predicts ZIP-code opportunity windows using discrete-time Markov chains
"""

import numpy as np
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import uuid


class MarkovEngine:
    """
    4-State Markov Chain for roofing opportunity prediction
    States: baseline -> pre_impact -> impact -> recovery
    """

    # Transition matrix (empirical probabilities)
    # Rows: current state, Cols: next state
    # Order: [baseline, pre_impact, impact, recovery]
    TRANSITION_MATRIX = np.array(
        [
            [0.95, 0.05, 0.00, 0.00],  # baseline
            [0.10, 0.30, 0.60, 0.00],  # pre_impact
            [0.00, 0.00, 0.20, 0.80],  # impact
            [0.70, 0.00, 0.00, 0.30],  # recovery
        ]
    )

    STATE_MAP = {"baseline": 0, "pre_impact": 1, "impact": 2, "recovery": 3}

    STATE_REVERSE = {v: k for k, v in STATE_MAP.items()}

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def initialize_zip_states(
        self, tenant_id: uuid.UUID, storm_id: uuid.UUID, zip_codes: List[str]
    ) -> int:
        """Initialize all ZIPs in baseline state"""
        with self.engine.connect() as conn:
            for zip_code in zip_codes:
                conn.execute(
                    text("""
                    INSERT INTO markov_zip_states (
                        tenant_id, storm_id, zip_code, current_state,
                        prob_to_baseline, prob_to_pre_impact, prob_to_impact, prob_to_recovery
                    ) VALUES (
                        :tenant_id, :storm_id, :zip_code, 'baseline',
                        0.95, 0.05, 0.00, 0.00
                    )
                    ON CONFLICT DO NOTHING
                """),
                    {
                        "tenant_id": str(tenant_id),
                        "storm_id": str(storm_id),
                        "zip_code": zip_code,
                    },
                )
            conn.commit()

        return len(zip_codes)

    def predict_next_state(self, current_state: str) -> Tuple[str, float]:
        """
        Predict most likely next state
        Returns (state_name, probability)
        """
        state_idx = self.STATE_MAP[current_state]
        probs = self.TRANSITION_MATRIX[state_idx]

        next_idx = np.argmax(probs)
        next_state = self.STATE_REVERSE[next_idx]

        return next_state, probs[next_idx]

    def transition_zip(
        self,
        tenant_id: uuid.UUID,
        storm_id: uuid.UUID,
        zip_code: str,
        trigger_event: str,
    ) -> str:
        """
        Execute state transition for a ZIP code
        Returns new state
        """
        with self.engine.connect() as conn:
            # Get current state
            result = conn.execute(
                text("""
                SELECT state_id, current_state
                FROM markov_zip_states
                WHERE tenant_id = :tenant_id
                  AND storm_id = :storm_id
                  AND zip_code = :zip_code
            """),
                {
                    "tenant_id": str(tenant_id),
                    "storm_id": str(storm_id),
                    "zip_code": zip_code,
                },
            )

            row = result.fetchone()
            if not row:
                raise ValueError(f"ZIP {zip_code} not initialized")

            state_id = row[0]
            current_state = row[1]

            # Predict next state
            next_state, prob = self.predict_next_state(current_state)

            # Execute transition
            conn.execute(
                text("""
                SELECT transition_markov_state(:state_id, :new_state, :trigger)
            """),
                {
                    "state_id": str(state_id),
                    "new_state": next_state,
                    "trigger": trigger_event,
                },
            )

            # Update probabilities for new state
            new_probs = self.TRANSITION_MATRIX[self.STATE_MAP[next_state]]
            conn.execute(
                text("""
                UPDATE markov_zip_states
                SET prob_to_baseline = :p0,
                    prob_to_pre_impact = :p1,
                    prob_to_impact = :p2,
                    prob_to_recovery = :p3,
                    last_updated_at = NOW()
                WHERE state_id = :state_id
            """),
                {
                    "state_id": str(state_id),
                    "p0": float(new_probs[0]),
                    "p1": float(new_probs[1]),
                    "p2": float(new_probs[2]),
                    "p3": float(new_probs[3]),
                },
            )

            conn.commit()

        return next_state

    def trigger_earth2_transitions(
        self, tenant_id: uuid.UUID, storm_id: uuid.UUID
    ) -> Dict:
        """
        Automatically transition ZIPs based on Earth-2 impact zones
        baseline -> pre_impact -> impact
        """
        transitions = {"baseline_to_pre": 0, "pre_to_impact": 0}

        with self.engine.connect() as conn:
            # Find ZIPs with Earth-2 detected impact
            result = conn.execute(
                text("""
                SELECT DISTINCT p.zip_code
                FROM properties p
                JOIN earth2_impact_zones ez ON 
                    p.zip_code IS NOT NULL AND p.zip_code != ''
                WHERE p.tenant_id = :tenant_id
                  AND ez.storm_id = :storm_id
                  AND ez.damage_propensity_score > 0.5
            """),
                {"tenant_id": str(tenant_id), "storm_id": str(storm_id)},
            )

            impacted_zips = [row[0] for row in result.fetchall()]

        # Transition each ZIP
        for zip_code in impacted_zips:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                    SELECT current_state FROM markov_zip_states
                    WHERE tenant_id = :tenant_id
                      AND storm_id = :storm_id
                      AND zip_code = :zip_code
                """),
                    {
                        "tenant_id": str(tenant_id),
                        "storm_id": str(storm_id),
                        "zip_code": zip_code,
                    },
                )

                row = result.fetchone()
                if not row:
                    continue

                current = row[0]

                if current == "baseline":
                    self.transition_zip(
                        tenant_id, storm_id, zip_code, "earth2_hail_detected"
                    )
                    transitions["baseline_to_pre"] += 1
                elif current == "pre_impact":
                    self.transition_zip(
                        tenant_id, storm_id, zip_code, "earth2_impact_confirmed"
                    )
                    transitions["pre_to_impact"] += 1

        return transitions

    def trigger_recovery_window(
        self, tenant_id: uuid.UUID, storm_id: uuid.UUID, hours_since_impact: int = 24
    ) -> int:
        """
        Transition ZIPs from impact -> recovery after time threshold
        This is the "Peak Opportunity Window"
        """
        count = 0

        with self.engine.connect() as conn:
            # Find ZIPs in impact state for > N hours
            result = conn.execute(
                text("""
                SELECT zip_code
                FROM markov_zip_states
                WHERE tenant_id = :tenant_id
                  AND storm_id = :storm_id
                  AND current_state = 'impact'
                  AND state_entered_at < datetime('now', '-' || :hours || ' hours')
            """),
                {
                    "tenant_id": str(tenant_id),
                    "storm_id": str(storm_id),
                    "hours": hours_since_impact,
                },
            )

            recovery_zips = [row[0] for row in result.fetchall()]

        for zip_code in recovery_zips:
            self.transition_zip(tenant_id, storm_id, zip_code, "recovery_window_opened")
            count += 1

        return count

    def calculate_tam(
        self,
        tenant_id: uuid.UUID,
        storm_id: uuid.UUID,
        zip_code: str,
        avg_job_value: float = 8500,
    ) -> float:
        """
        Calculate Total Addressable Market for a ZIP
        TAM = (Properties in Recovery State) * (Avg Job Value) * (Close Rate)
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT COUNT(*)
                FROM properties p
                JOIN markov_zip_states mz ON p.zip_code = mz.zip_code
                WHERE p.tenant_id = :tenant_id
                  AND mz.storm_id = :storm_id
                  AND mz.zip_code = :zip_code
                  AND mz.current_state = 'recovery'
            """),
                {
                    "tenant_id": str(tenant_id),
                    "storm_id": str(storm_id),
                    "zip_code": zip_code,
                },
            )

            property_count = result.scalar() or 0

        # Assume 15% close rate in recovery window
        tam = property_count * avg_job_value * 0.15

        # Update in DB
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                UPDATE markov_zip_states
                SET estimated_tam_usd = :tam
                WHERE tenant_id = :tenant_id
                  AND storm_id = :storm_id
                  AND zip_code = :zip_code
            """),
                {
                    "tenant_id": str(tenant_id),
                    "storm_id": str(storm_id),
                    "zip_code": zip_code,
                    "tam": tam,
                },
            )
            conn.commit()

        return tam

    def get_top_opportunity_zips(
        self, tenant_id: uuid.UUID, storm_id: uuid.UUID, limit: int = 10
    ) -> List[Dict]:
        """
        Return top ZIPs by TAM in recovery state
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT 
                    zip_code,
                    current_state,
                    estimated_tam_usd,
                    prob_to_recovery,
                    state_entered_at
                FROM markov_zip_states
                WHERE tenant_id = :tenant_id
                  AND storm_id = :storm_id
                  AND current_state IN ('recovery', 'impact')
                ORDER BY estimated_tam_usd DESC NULLS LAST
                LIMIT :limit
            """),
                {
                    "tenant_id": str(tenant_id),
                    "storm_id": str(storm_id),
                    "limit": limit,
                },
            )

            return [dict(row._mapping) for row in result.fetchall()]


if __name__ == "__main__":
    # Demo
    engine = MarkovEngine("postgresql://stormops:password@localhost:5432/stormops")

    tenant_id = uuid.uuid4()
    storm_id = uuid.uuid4()

    # Initialize DFW ZIPs
    dfw_zips = ["75024", "75025", "75034", "75035", "76051"]
    engine.initialize_zip_states(tenant_id, storm_id, dfw_zips)
    print(f"✅ Initialized {len(dfw_zips)} ZIPs")

    # Simulate Earth-2 detection
    transitions = engine.trigger_earth2_transitions(tenant_id, storm_id)
    print(f"✅ Transitions: {transitions}")

    # Calculate TAM
    for zip_code in dfw_zips:
        tam = engine.calculate_tam(tenant_id, storm_id, zip_code)
        print(f"ZIP {zip_code}: ${tam:,.0f} TAM")
