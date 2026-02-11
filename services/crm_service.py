
import os
import sqlite3
import requests
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ScoredLead:
    address: str
    zip_code: str
    roof_age: int
    score: float
    tags: List[str]
    confidence: float

class CRMService:
    """
    Interface for Contractor CRM (JobNimbus).
    """

    def __init__(self):
        self.api_key = os.getenv("JOBNIMBUS_API_KEY", "MOCK_KEY")
        self.base_url = "https://mock.stormops.ai/api/v1" # Simulated endpoint

    def push_lead(self, lead: ScoredLead):
        """
        Push a scored lead to JobNimbus as a 'Contact'.
        """
        if not self.api_key:
            return

        # Simple Local Deduplication Check
        db_path = "stormops_cache.db"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute(
                    "SELECT pushed FROM properties WHERE address=? AND zip=?",
                    (lead.address, lead.zip_code),
                )
                row = c.fetchone()
                conn.close()
                if row and row[0] == 1:
                    return
            except Exception:
                pass

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "recordType": "Contact",
            "status": "Lead",
            "source": "StormOps Earth-2",
            "firstName": "Resident",
            "lastName": "Occupant",
            "address1": lead.address.split(",")[0].strip(),
            " city": "Denton",
            "state": "TX",
            "zip": lead.zip_code,
            "description": f"Storm Score: {lead.score} | Roof Age: {lead.roof_age} | Tags: {','.join(lead.tags)}",
        }

        try:
            if "mock.stormops.ai" in self.base_url:
                response_status = 201
            else:
                response = requests.post(
                    f"{self.base_url}/contacts", json=payload, headers=headers, timeout=10
                )
                response_status = response.status_code

            if response_status in [200, 201]:
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    conn.cursor().execute(
                        "UPDATE properties SET pushed=1 WHERE address=? AND zip=?",
                        (lead.address, lead.zip_code),
                    )
                    conn.commit()
                    conn.close()
        except Exception:
            pass
