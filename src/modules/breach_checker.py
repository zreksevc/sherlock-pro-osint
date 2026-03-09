"""
Breach Checker Module — Multi-source breach detection
"""
from typing import Dict, List, Optional, Any
from src.utils.request_handler import RequestHandler
from src.utils.logger import log_section, log_info, log_warning, log_success, log_error, Colors


class BreachChecker:
    """
    Multi-source breach detection engine.

    Supported sources:
    - Have I Been Pwned (HIBP) — requires API key
    - LeakCheck.io           — requires API key
    - DeHashed               — requires API key
    - Public heuristics      — free (domain checks)
    """

    def __init__(
        self,
        hibp_key: Optional[str] = None,
        leakcheck_key: Optional[str] = None,
        dehashed_user: Optional[str] = None,
        dehashed_key: Optional[str] = None,
        timeout: int = 15,
        proxy: Optional[str] = None,
    ):
        self.hibp_key = hibp_key
        self.leakcheck_key = leakcheck_key
        self.dehashed_user = dehashed_user
        self.dehashed_key = dehashed_key
        self.handler = RequestHandler(timeout=timeout, proxy=proxy)

    def check_all(self, email: str) -> Dict[str, Any]:
        """Run all available breach checks for an email."""
        log_section(f"BREACH CHECK: {email}")
        results: Dict[str, Any] = {
            "email": email,
            "hibp": [],
            "leakcheck": [],
            "dehashed": [],
            "total_breaches": 0,
            "risk_level": "LOW",
        }

        if self.hibp_key:
            results["hibp"] = self._check_hibp(email)
        else:
            log_info("HIBP: No API key provided (--hibp-key)")

        if self.leakcheck_key:
            results["leakcheck"] = self._check_leakcheck(email)
        else:
            log_info("LeakCheck: No API key provided (--leakcheck-key)")

        if self.dehashed_user and self.dehashed_key:
            results["dehashed"] = self._check_dehashed(email)
        else:
            log_info("DeHashed: No credentials provided")

        # Calculate totals
        total = len(results["hibp"]) + len(results["leakcheck"]) + len(results["dehashed"])
        results["total_breaches"] = total
        results["risk_level"] = self._calc_risk(total)

        # Display
        log_section("BREACH SUMMARY")
        log_info(f"Total breaches found : {total}")
        log_info(f"Risk level           : {self._risk_color(results['risk_level'])}")

        if results["hibp"]:
            print(f"\n  {Colors.RED}[HIBP BREACHES]{Colors.RESET}")
            for b in results["hibp"]:
                name = b.get("Name", "Unknown")
                date = b.get("BreachDate", "Unknown")
                count = b.get("PwnCount", 0)
                data_classes = ", ".join(b.get("DataClasses", [])[:4])
                print(f"    {Colors.YELLOW}●{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET} ({date}) — {count:,} accounts")
                print(f"      Data: {Colors.DIM}{data_classes}{Colors.RESET}")

        return results

    def _check_hibp(self, email: str) -> List[Dict]:
        """Have I Been Pwned v3 API."""
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"
        self.handler.session.headers.update({
            "hibp-api-key": self.hibp_key,
            "user-agent": "OSINT-Sherlock-Pro/2.0",
        })
        resp = self.handler.get(url)
        if resp is None:
            log_error("HIBP", "Request failed")
            return []
        if resp.status_code == 200:
            data = resp.json()
            log_warning(f"HIBP: {len(data)} breach(es) found!")
            return data
        elif resp.status_code == 404:
            log_success("HIBP: No breaches found.")
            return []
        elif resp.status_code == 401:
            log_error("HIBP", "Unauthorized — check your API key")
            return []
        elif resp.status_code == 429:
            log_error("HIBP", "Rate limited — slow down requests")
            return []
        return []

    def _check_leakcheck(self, email: str) -> List[Dict]:
        """LeakCheck.io API."""
        url = f"https://leakcheck.io/api/public?key={self.leakcheck_key}&check={email}"
        resp = self.handler.get(url)
        if resp is None:
            log_error("LeakCheck", "Request failed")
            return []
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("found", 0) > 0:
                sources = data.get("sources", [])
                log_warning(f"LeakCheck: Found in {len(sources)} source(s)")
                return sources
            else:
                log_success("LeakCheck: No breaches found.")
                return []
        log_error("LeakCheck", f"HTTP {resp.status_code}")
        return []

    def _check_dehashed(self, email: str) -> List[Dict]:
        """DeHashed API."""
        import base64
        url = f"https://api.dehashed.com/search?query=email:{email}"
        creds = base64.b64encode(f"{self.dehashed_user}:{self.dehashed_key}".encode()).decode()
        self.handler.session.headers.update({
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
        })
        resp = self.handler.get(url)
        if resp is None:
            log_error("DeHashed", "Request failed")
            return []
        if resp.status_code == 200:
            data = resp.json()
            entries = data.get("entries", []) or []
            if entries:
                log_warning(f"DeHashed: Found {len(entries)} record(s)")
            else:
                log_success("DeHashed: No records found.")
            return entries
        log_error("DeHashed", f"HTTP {resp.status_code}")
        return []

    def _calc_risk(self, count: int) -> str:
        if count == 0:
            return "LOW"
        elif count <= 2:
            return "MEDIUM"
        elif count <= 5:
            return "HIGH"
        return "CRITICAL"

    def _risk_color(self, risk: str) -> str:
        colors = {
            "LOW": f"{Colors.GREEN}LOW{Colors.RESET}",
            "MEDIUM": f"{Colors.YELLOW}MEDIUM{Colors.RESET}",
            "HIGH": f"{Colors.RED}HIGH{Colors.RESET}",
            "CRITICAL": f"{Colors.RED}{Colors.BOLD}CRITICAL{Colors.RESET}",
        }
        return colors.get(risk, risk)

    def close(self):
        self.handler.close()
