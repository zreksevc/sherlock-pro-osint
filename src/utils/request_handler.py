"""
Request Handler — HTTP engine with proxy, Tor, user-agent rotation, retry
"""
import random
import time
import requests
from typing import Optional, Dict

# User-agent pool (desktop + mobile)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.1; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}


class RequestHandler:
    def __init__(
        self,
        timeout: int = 10,
        retries: int = 2,
        proxy: Optional[str] = None,
        use_tor: bool = False,
        delay: float = 0.0,
    ):
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.session = requests.Session()

        # Configure proxy / Tor
        if use_tor:
            self.session.proxies = {
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050",
            }
        elif proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def _build_headers(self) -> Dict[str, str]:
        headers = BASE_HEADERS.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        return headers

    def get(self, url: str) -> Optional[requests.Response]:
        """Send GET request with retry logic."""
        for attempt in range(self.retries + 1):
            try:
                if self.delay > 0:
                    time.sleep(self.delay)
                resp = self.session.get(
                    url,
                    headers=self._build_headers(),
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                return resp
            except requests.exceptions.Timeout:
                if attempt == self.retries:
                    return None
            except requests.exceptions.ConnectionError:
                if attempt == self.retries:
                    return None
            except requests.exceptions.TooManyRedirects:
                return None
            except Exception:
                return None
        return None

    def close(self):
        self.session.close()
