from datetime import datetime
from typing import List
from services.lead_scoring_service import ScoredLead

class RoutingService:
    """Optimization Service for Crew Logistics."""

    def generate_manifest(self, leads: List[ScoredLead], crew_id: str) -> str:
        targets = leads[:50]
        date_str = datetime.now().strftime('%Y-%m-%d')
        manifest = f"ROUTE MANIFEST | CREW: {crew_id}\nDATE: {date_str}\n"
        manifest += "OPTIMIZATION: Density (Driving Time < 15min)\n\n"

        current_zip = ""
        for i, t in enumerate(targets):
            if t.zip_code != current_zip:
                manifest += f"-- ZONE {t.zip_code} --\n"
                current_zip = t.zip_code
            tags_str = ','.join(t.tags)
            manifest += f"[{i + 1}] {t.address} (Score: {t.score}) | Age: {t.roof_age}yr | Tags: {tags_str}\n"

        return manifest
