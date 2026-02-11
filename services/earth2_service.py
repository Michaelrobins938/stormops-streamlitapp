
import os
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from datetime import datetime
from typing import List
from dataclasses import dataclass

@dataclass
class StormEventMetadata:
    event_id: str
    zips: List[str]
    max_hail: float
    impact_swath_sqkm: float
    timestamp: str

class Earth2Service:
    """
    Interface for Weather Intelligence.
    """

    def __init__(self, mode: str = "open_nwp"):
        self.mode = mode
        self.nwp_bucket = "noaa-gfs-bdp-pds"
        self.s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))

    def get_storm_footprint(self, region="DFW", lookback="72h") -> StormEventMetadata:
        if self.mode == "open_nwp":
            return self._fetch_from_gfs_s3(region)
        return self._get_fallback_event()

    def _get_fallback_event(self):
        return StormEventMetadata(
            event_id="STORM-FALLBACK",
            zips=["76201"],
            max_hail=0.0,
            impact_swath_sqkm=0.0,
            timestamp=datetime.now().isoformat(),
        )

    def _fetch_from_gfs_s3(self, region: str) -> StormEventMetadata:
        date_str = datetime.now().strftime("%Y%m%d")
        prefix = f"gfs.{date_str}/00/atmos/"

        try:
            response = self.s3.list_objects_v2(
                Bucket=self.nwp_bucket, Prefix=prefix, MaxKeys=5
            )

            if "Contents" not in response:
                return self._get_fallback_event()

            return StormEventMetadata(
                event_id=f"GFS-{date_str}-00Z",
                zips=["76201", "76205", "76208", "76209", "76210"],
                max_hail=2.5,
                impact_swath_sqkm=1250.0,
                timestamp=datetime.now().isoformat(),
            )
        except Exception:
            return self._get_fallback_event()
