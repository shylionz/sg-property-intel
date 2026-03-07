"""
URA Session Manager - handles CSRF token extraction and session persistence.
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional
import brotli  # For brotli decompression


class URASession:
    """Manages URA e-Service session with CSRF token handling."""
    
    TRANSACTION_URL = "https://eservice.ura.gov.sg/property-market-information/pmiResidentialTransactionSearch"
    RENTAL_URL = "https://eservice.ura.gov.sg/property-market-information/pmiResidentialRentalSearch"
    
    def __init__(self):
        self.session = requests.Session()
        
        # Enable compression handling
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",  # Include br for brotli
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
        })
        
        # Configure adapter to handle compression
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self._csrf_token: Optional[str] = None
    
    def get_csrf(self, url: str) -> str:
        """Fetch a URA page and extract CSRF token."""
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        
        # Ensure we have the text (handles decompression automatically)
        html_content = resp.text
        
        soup = BeautifulSoup(html_content, "lxml")
        
        # Try to find in input field (name="_csrf")
        csrf_input = soup.find("input", {"name": "_csrf"})
        if csrf_input and csrf_input.get("value"):
            self._csrf_token = csrf_input["value"]
            return self._csrf_token
        
        # Try meta tag with name="_csrf" - use content attribute
        csrf_meta = soup.find("meta", {"name": "_csrf"})
        if csrf_meta and csrf_meta.get("content"):
            self._csrf_token = csrf_meta["content"]
            return self._csrf_token
        
        # Try from form hidden input
        form_csrf = soup.find("input", {"type": "hidden", "name": "_csrf"})
        if form_csrf and form_csrf.get("value"):
            self._csrf_token = form_csrf["value"]
            return self._csrf_token
        
        raise ValueError(f"CSRF token not found on page: {url}")
    
    def refresh_csrf(self, url: str) -> str:
        """Force refresh CSRF token."""
        return self.get_csrf(url)
    
    @property
    def csrf(self) -> Optional[str]:
        """Get current CSRF token."""
        return self._csrf_token
    
    def post(self, url: str, data: dict, timeout: int = 30) -> requests.Response:
        """POST data to URA endpoint."""
        resp = self.session.post(url, data=data, timeout=timeout)
        return resp


# Singleton instance
_ura_session: Optional[URASession] = None


def get_ura_session() -> URASession:
    """Get or create URA session singleton."""
    global _ura_session
    if _ura_session is None:
        _ura_session = URASession()
    return _ura_session


def reset_ura_session():
    """Reset URA session (for testing or recovery)."""
    global _ura_session
    _ura_session = URASession()
