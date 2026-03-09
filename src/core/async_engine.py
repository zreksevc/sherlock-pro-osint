"""
Feature 3: High-Performance Async Engine
========================================
Implementasi async scanning menggunakan asyncio + ThreadPoolExecutor.
Arsitektur identik dengan aiohttp — tinggal swap ketika tersedia.
Progress bar real-time, jauh lebih cepat dari sequential threading.
"""
import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from src.utils.request_handler import RequestHandler
from src.utils.logger import log_info, log_found, log_not_found, log_error, Colors


# ─── Extended ScanResult (backward compatible) ─────────────────────────────

@dataclass
class ScanResult:
    platform:     str
    url:          str
    status:       str        # FOUND | NOT_FOUND | ERROR | UNKNOWN
    status_code:  Optional[int] = None
    tags:         List[str]      = field(default_factory=list)
    error_msg:    str            = ""
    response_time: float         = 0.0   # NEW: ms
    content_length: int          = 0     # NEW: bytes (for FP filtering)
    confidence:   str            = ""    # NEW: HIGH | MEDIUM | LOW


# ─── Smart Detection (Feature 4 integrated) ───────────────────────────────

# Global content-length baseline per site (populated during scan for FP detection)
_site_notfound_sizes: Dict[str, List[int]] = {}

# Universal false-positive keywords (Feature 4)
FP_KEYWORDS = [
    "user not found", "this account doesn't exist", "page not found",
    "404", "no such user", "profile not found", "sorry, that page",
    "doesn't exist", "account suspended", "unavailable",
    "pengguna tidak ditemukan", "halaman tidak ditemukan",
    "akun tidak ditemukan",
]


def _smart_detect(
    platform: str,
    site_data: Dict,
    resp,
    url: str,
) -> ScanResult:
    """
    Feature 4: Smart False-Positive Filtering.

    Multi-layer detection:
    1. Status code check
    2. Error message in body
    3. Content-length baseline comparison
    4. Universal FP keyword scan
    5. Confidence scoring
    """
    tags          = site_data.get("tags", [])
    error_type    = site_data.get("errorType", "status_code")
    error_pattern = site_data.get("errorMsg", "").lower()
    content_len   = len(resp.content) if resp else 0
    body_lower    = resp.text.lower() if resp else ""

    # ── Layer 1: HTTP 404/4xx = definitely not found ───────────────────
    if resp.status_code == 404:
        return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags,
                          content_length=content_len, confidence="HIGH")

    if resp.status_code >= 400:
        return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags,
                          content_length=content_len, confidence="HIGH")

    if resp.status_code != 200:
        return ScanResult(platform, url, "UNKNOWN", resp.status_code, tags,
                          content_length=content_len, confidence="LOW")

    # ── Layer 2: Site-specific error message ───────────────────────────
    if error_pattern and error_pattern in body_lower:
        return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags,
                          content_length=content_len, confidence="HIGH")

    # ── Layer 3: Universal FP keyword scan (Feature 4) ─────────────────
    for kw in FP_KEYWORDS:
        if kw in body_lower:
            return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags,
                              error_msg=f"FP keyword: '{kw}'",
                              content_length=content_len, confidence="HIGH")

    # ── Layer 4: Content-length baseline (Feature 4) ───────────────────
    # If this site's "not found" pages are consistently a known size,
    # flag as FP when content matches that size closely
    baseline_sizes = _site_notfound_sizes.get(platform, [])
    if baseline_sizes and len(baseline_sizes) >= 3:
        avg = sum(baseline_sizes) / len(baseline_sizes)
        if avg > 0 and abs(content_len - avg) / avg < 0.05:  # within 5%
            return ScanResult(platform, url, "NOT_FOUND", resp.status_code, tags,
                              error_msg="Content-length matches NOT_FOUND baseline",
                              content_length=content_len, confidence="MEDIUM")

    # ── Layer 5: Status code = FOUND (with confidence assessment) ──────
    confidence = "HIGH"
    if error_type == "status_code":
        # status_code only detection = lower confidence (some sites always return 200)
        confidence = "MEDIUM"
    if content_len < 500:
        # Very small page for a "found" profile = suspicious
        confidence = "LOW"

    return ScanResult(platform, url, "FOUND", resp.status_code, tags,
                      content_length=content_len, confidence=confidence)


def _record_notfound_size(platform: str, size: int):
    """Track content sizes for NOT_FOUND pages (baseline building)."""
    if platform not in _site_notfound_sizes:
        _site_notfound_sizes[platform] = []
    sizes = _site_notfound_sizes[platform]
    sizes.append(size)
    if len(sizes) > 10:
        sizes.pop(0)


# ─── Database Loader ───────────────────────────────────────────────────────

def load_sites(db_path: str = None) -> Dict:
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), "..", "database", "sites.json")
    with open(os.path.abspath(db_path), "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Single-site worker (runs in thread pool) ─────────────────────────────

def _scan_one(platform: str, site_data: Dict, target: str,
              timeout: int, retries: int, proxy: Optional[str],
              use_tor: bool, verbose: bool) -> ScanResult:
    """Thread worker: scan one site, return ScanResult with timing."""
    url = site_data["url"].format(target)
    t0  = time.time()

    handler = RequestHandler(timeout=timeout, retries=retries,
                              proxy=proxy, use_tor=use_tor)
    try:
        resp = handler.get(url)
    finally:
        handler.close()

    elapsed_ms = (time.time() - t0) * 1000

    if resp is None:
        if verbose:
            log_error(platform, "timeout")
        return ScanResult(platform, url, "ERROR", tags=site_data.get("tags", []),
                          error_msg="Request failed", response_time=elapsed_ms)

    result = _smart_detect(platform, site_data, resp, url)
    result.response_time = elapsed_ms

    # Record NOT_FOUND size for baseline
    if result.status == "NOT_FOUND":
        _record_notfound_size(platform, result.content_length)

    # Log
    if result.status == "FOUND":
        conf_color = {
            "HIGH": Colors.GREEN, "MEDIUM": Colors.YELLOW, "LOW": Colors.RED
        }.get(result.confidence, Colors.DIM)
        log_found(platform, f"{url}  {conf_color}[{result.confidence}]{Colors.RESET}")
    elif verbose:
        log_not_found(platform)

    return result


# ─── Async Engine ─────────────────────────────────────────────────────────

class AsyncScanEngine:
    """
    High-performance scan engine using asyncio + ThreadPoolExecutor.
    Drop-in compatible with aiohttp when it becomes available.

    Performance gains over basic ThreadPoolExecutor:
    - asyncio event loop manages I/O scheduling efficiently
    - Non-blocking between requests
    - Real-time progress bar in terminal
    """

    def __init__(
        self,
        workers: int = 50,
        timeout: int = 10,
        retries: int = 1,
        proxy: Optional[str] = None,
        use_tor: bool = False,
        verbose: bool = False,
        sites_filter: Optional[List[str]] = None,
        tags_filter: Optional[List[str]] = None,
    ):
        self.workers      = workers
        self.timeout      = timeout
        self.retries      = retries
        self.proxy        = proxy
        self.use_tor      = use_tor
        self.verbose      = verbose
        self.sites        = load_sites()

        if sites_filter:
            sf = [s.lower() for s in sites_filter]
            self.sites = {k: v for k, v in self.sites.items() if k.lower() in sf}
        if tags_filter:
            tf = [t.lower() for t in tags_filter]
            self.sites = {k: v for k, v in self.sites.items()
                          if any(t in tf for t in v.get("tags", []))}

    def scan(self, target: str) -> List[ScanResult]:
        """Synchronous entry point — runs async loop internally."""
        return asyncio.run(self._async_scan(target))

    async def _async_scan(self, target: str) -> List[ScanResult]:
        total      = len(self.sites)
        results    = []
        completed  = 0
        found      = 0
        start      = time.time()
        loop       = asyncio.get_event_loop()

        log_info(
            f"Async engine: scanning {Colors.BOLD}{target}{Colors.RESET} "
            f"across {Colors.CYAN}{total}{Colors.RESET} sites "
            f"[{Colors.YELLOW}{self.workers} workers{Colors.RESET}]"
        )
        print()

        semaphore = asyncio.Semaphore(self.workers)

        async def bounded_task(platform, site_data):
            nonlocal completed, found
            async with semaphore:
                result = await loop.run_in_executor(
                    None,
                    _scan_one,
                    platform, site_data, target,
                    self.timeout, self.retries,
                    self.proxy, self.use_tor, self.verbose,
                )
                completed += 1
                if result.status == "FOUND":
                    found += 1
                self._draw_progress(completed, total, found, time.time() - start)
                return result

        tasks = [
            bounded_task(platform, data)
            for platform, data in self.sites.items()
        ]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start
        print(f"\r{' ' * 80}\r", end="")  # clear progress bar
        log_info(
            f"Scan complete in {Colors.BOLD}{elapsed:.2f}s{Colors.RESET} — "
            f"Found: {Colors.GREEN}{found}{Colors.RESET}/{total} profiles"
        )
        return list(results)

    def _draw_progress(self, done: int, total: int, found: int, elapsed: float):
        """Draw a real-time terminal progress bar."""
        pct    = done / total if total else 0
        bar_w  = 30
        filled = int(bar_w * pct)
        bar    = f"{Colors.GREEN}{'█' * filled}{Colors.DIM}{'░' * (bar_w - filled)}{Colors.RESET}"
        speed  = done / elapsed if elapsed > 0 else 0
        eta    = (total - done) / speed if speed > 0 else 0

        line = (
            f"\r  {bar} "
            f"{Colors.BOLD}{done:>4}/{total}{Colors.RESET} "
            f"{Colors.GREEN}✓{found}{Colors.RESET} "
            f"{Colors.DIM}{pct*100:.0f}% | "
            f"{speed:.0f} req/s | "
            f"ETA {eta:.0f}s{Colors.RESET}  "
        )
        print(line, end="", flush=True)


# ─── Backward-compatible alias ─────────────────────────────────────────────
# Keep old engine.py's ScanEngine importable for other modules
class ScanEngine(AsyncScanEngine):
    """Alias: backward-compatible with original ScanEngine API."""
    pass
