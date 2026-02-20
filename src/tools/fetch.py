import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import get_settings
from src.tools.audit import audit_log
import json

settings = get_settings()

class SecureFetcher:
    """
    Zero-trust fetcher strictly enforcing HTTPS, TLS validation, and exponential backoff
    to prevent pipeline failure on intermittent API drops.
    """
    def __init__(self):
        self.client = httpx.AsyncClient(
            verify=True,      # Strict TLS
            timeout=15.0      # Hard limits on network hangs
        )

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def fetch_statsbomb_matches(self, competition_id: int, season_id: int) -> list:
        """Fetch match metadata for a specific competition and season."""
        url = f"{settings.statsbomb_github_url}/matches/{competition_id}/{season_id}.json"
        audit_log("fetch_start", "FetcherAgent", {"source": "StatsBomb", "url": url, "type": "matches"})
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            audit_log("fetch_success", "FetcherAgent", {"source": "StatsBomb", "type": "matches", "size_bytes": len(response.content)})
            return data
        except Exception as e:
            audit_log("fetch_error", "FetcherAgent", {"source": "StatsBomb", "type": "matches", "error": str(e)})
            raise

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def fetch_statsbomb_events(self, match_id: int) -> dict:
        """Fetch raw event data from StatsBomb open data gracefully."""
        url = f"{settings.statsbomb_github_url}/events/{match_id}.json"
        audit_log("fetch_start", "FetcherAgent", {"source": "StatsBomb", "url": url, "match_id": match_id})
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            audit_log("fetch_success", "FetcherAgent", {"source": "StatsBomb", "match_id": match_id, "size_bytes": len(response.content)})
            return data
        except Exception as e:
            audit_log("fetch_error", "FetcherAgent", {"source": "StatsBomb", "match_id": match_id, "error": str(e)})
            raise

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def fetch_metrica_tracking(self, home_or_away: str) -> str:
        """Fetch raw tracking CSV data from Metrica open GitHub securely."""
        url = f"https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_{home_or_away}_Team.csv"
        audit_log("fetch_start", "FetcherAgent", {"source": "Metrica", "url": url, "type": f"tracking_{home_or_away}"})
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            audit_log("fetch_success", "FetcherAgent", {"source": "Metrica", "type": f"tracking_{home_or_away}", "size_bytes": len(response.content)})
            return response.text
        except Exception as e:
            audit_log("fetch_error", "FetcherAgent", {"source": "Metrica", "type": f"tracking_{home_or_away}", "error": str(e)})
            raise

    async def close(self):
        await self.client.aclose()
