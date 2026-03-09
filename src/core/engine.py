"""
Core Scanning Engine — ThreadPoolExecutor-based concurrent scanner
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from src.utils.request_handler import RequestHandler
from src.utils.logger import log_found, log_not_found, log_error, log_info


# ─── Result Data Class ──────────────────────────────────────────────────────

@dataclass
class ScanResult:
    platform: str
    url: str
    status: str        # FOUND | NOT_FOUND | ERROR | UNKNOWN
    status_code: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    error_msg: str = ""


# ─── Site Database Loader ───────────────────────────────────────────────────

def load_sites(db_path: str = None) -> Dict:
    """Load sites.json database."""
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(__file__), "..", "database", "sites.json"
        )
    db_path = os.path.abspath(db_path)
    with open(db_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Single Site Scanner ───────────────────────────────────────────────────

def scan_single_site(
    platform: str,
    site_data: Dict,
    target: str,
    handler: RequestHandler,
    verbose: bool = False,
) -> ScanResult:
    """Scan one site for a username/target."""
    url = site_data["url"].format(target)
    error_type = site_data.get("errorType", "status_code")
    error_msg_pattern = site_data.get("errorMsg", "")
    tags = site_data.get("tags", [])

    resp = handler.get(url)

    if resp is None:
        if verbose:
            log_error(platform, "timeout/connection error")
        return ScanResult(platform, url, "ERROR", tags=tags, error_msg="Request failed")

    # Detection logic
    if error_type == "status_code":
        if resp.status_code == 200:
            log_found(platform, url)
            return ScanResult(platform, url, "FOUND", resp.status_code, tags)
        else:
            if verbose:
                log_not_found(platform)
            return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags)

    elif error_type == "message":
        if resp.status_code == 200:
            if error_msg_pattern and error_msg_pattern.lower() in resp.text.lower():
                if verbose:
                    log_not_found(platform)
                return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags)
            else:
                log_found(platform, url)
                return ScanResult(platform, url, "FOUND", resp.status_code, tags)
        else:
            if verbose:
                log_not_found(platform)
            return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags)

    elif error_type == "response_url":
        # Some sites redirect to error page
        error_url = site_data.get("errorUrl", "")
        if error_url and error_url in resp.url:
            if verbose:
                log_not_found(platform)
            return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags)
        elif resp.status_code == 200:
            log_found(platform, url)
            return ScanResult(platform, url, "FOUND", resp.status_code, tags)
        else:
            if verbose:
                log_not_found(platform)
            return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags)

    return ScanResult(platform, url, "UNKNOWN", resp.status_code, tags)


# ─── Main Engine ────────────────────────────────────────────────────────────

class ScanEngine:
    def __init__(
        self,
        workers: int = 30,
        timeout: int = 10,
        retries: int = 1,
        proxy: Optional[str] = None,
        use_tor: bool = False,
        delay: float = 0.0,
        verbose: bool = False,
        sites_filter: Optional[List[str]] = None,
        tags_filter: Optional[List[str]] = None,
    ):
        self.workers = workers
        self.timeout = timeout
        self.retries = retries
        self.proxy = proxy
        self.use_tor = use_tor
        self.delay = delay
        self.verbose = verbose
        self.sites_filter = [s.lower() for s in sites_filter] if sites_filter else None
        self.tags_filter = [t.lower() for t in tags_filter] if tags_filter else None

        # Load site database
        self.sites = load_sites()

        # Apply filters
        if self.sites_filter:
            self.sites = {
                k: v for k, v in self.sites.items()
                if k.lower() in self.sites_filter
            }
        if self.tags_filter:
            self.sites = {
                k: v for k, v in self.sites.items()
                if any(t in self.tags_filter for t in v.get("tags", []))
            }

    def scan(self, target: str) -> List[ScanResult]:
        """Scan all sites for target using thread pool."""
        results: List[ScanResult] = []
        total = len(self.sites)
        completed = 0
        start_time = time.time()

        log_info(f"Scanning {Colors_placeholder('BOLD')}{target}{Colors_placeholder('RESET')} across {total} sites with {self.workers} threads...")
        print()

        # Create one handler per worker thread
        def worker_task(args):
            platform, site_data = args
            handler = RequestHandler(
                timeout=self.timeout,
                retries=self.retries,
                proxy=self.proxy,
                use_tor=self.use_tor,
                delay=self.delay,
            )
            result = scan_single_site(platform, site_data, target, handler, self.verbose)
            handler.close()
            return result

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(worker_task, (platform, data)): platform
                for platform, data in self.sites.items()
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    platform = futures[future]
                    results.append(ScanResult(platform, "", "ERROR", error_msg=str(e)))
                completed += 1

        elapsed = time.time() - start_time
        found_count = sum(1 for r in results if r.status == "FOUND")

        print()
        log_info(f"Scan complete in {elapsed:.2f}s — Found: {found_count}/{total} profiles")
        return results


def Colors_placeholder(attr: str) -> str:
    """Placeholder to avoid circular import; returns empty string."""
    return ""
