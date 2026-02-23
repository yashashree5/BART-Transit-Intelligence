"""
ingestion/bart_client.py
Pulls live BART train departure data from the BART API.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Logging setup 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("bart_client")

# Config 
BART_API_KEY  = os.getenv("BART_API_KEY", "ZVA4-5K6R-9J8T-DWEI")
BART_BASE_URL = "https://api.bart.gov/api"
STAGING_DIR   = Path("staging/etd")


class BARTClient:

    def __init__(self):
        self.session = requests.Session()
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("BARTClient ready")

    def _get(self, endpoint: str, params: dict) -> dict | None:
        """Make API call with retry logic."""
        params.update({"key": BART_API_KEY, "json": "y"})
        url = f"{BART_BASE_URL}/{endpoint}"

        for attempt in range(1, 4):  # 3 retries
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                time.sleep(2 ** attempt)  # exponential backoff

        logger.error("All retries failed.")
        return None

    def fetch_departures(self, station: str = "all") -> dict | None:
        """Fetch real-time departures for a station (or all stations)."""
        data = self._get("etd.aspx", {"cmd": "etd", "orig": station})
        if data:
            self._save(data, feed_type="etd")
        return data

    def fetch_advisories(self) -> dict | None:
        """Fetch active service advisories and delays."""
        data = self._get("bsa.aspx", {"cmd": "bsa"})
        if data:
            self._save(data, feed_type="bsa")
        return data

    def _save(self, data: dict, feed_type: str) -> None:
        """Save raw JSON to staging folder with timestamp."""
        now = datetime.now(timezone.utc)
        folder = STAGING_DIR / f"{now.strftime('%Y-%m-%d')}"
        folder.mkdir(parents=True, exist_ok=True)

        filename = f"{feed_type}_{now.strftime('%H%M%S')}.json"
        filepath = folder / filename

        with open(filepath, "w") as f:
            json.dump({
                "ingested_at": now.isoformat(),
                "feed_type": feed_type,
                "payload": data
            }, f, indent=2)

        logger.info(f"Saved → {filepath}")

    def run(self):
        """Full ingestion run."""
        logger.info("=== Starting BART ingestion ===")
        self.fetch_advisories()
        self.fetch_departures(station="all")
        logger.info("=== Done ===")


if __name__ == "__main__":
    client = BARTClient()
    client.run()