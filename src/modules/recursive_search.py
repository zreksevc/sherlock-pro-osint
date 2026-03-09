"""
Feature 6: Recursive Search Engine
====================================
Otomatis temukan dan scan target baru dari hasil pencarian sebelumnya.

Flow:
  email → breach → temukan username → scan username → temukan profil
       → extract metadata → temukan username/email baru → scan lagi

Setiap iterasi dibatasi depth-nya untuk menghindari infinite loop.
"""
import re
from typing import Set, List, Dict, Optional, Any
from dataclasses import dataclass, field

from src.utils.logger import (
    log_section, log_info, log_success, log_warning, log_error, Colors
)


# ─── Discovered Target ────────────────────────────────────────────────────

@dataclass
class DiscoveredTarget:
    value:      str           # username or email
    type:       str           # 'username' | 'email'
    source:     str           # where it was found (e.g. "GitHub bio")
    depth:      int  = 0      # recursion level (0 = original input)
    confidence: str = "LOW"   # HIGH | MEDIUM | LOW


# ─── Target Extractor ─────────────────────────────────────────────────────

class TargetExtractor:
    """
    Extract new potential usernames and emails from various data sources:
    - Profile bios
    - Breach data
    - GitHub APIs
    - Email metadata
    """

    EMAIL_PATTERN    = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    USERNAME_PATTERN = re.compile(r"(?:^|[\s@/])([a-zA-Z0-9][a-zA-Z0-9_.\-]{2,29})(?:\s|$|[,;()])")
    SOCIAL_PATTERN   = re.compile(
        r"(?:twitter|instagram|github|tiktok|linkedin)[.:/]+(?:@?)([a-zA-Z0-9_.\-]{3,30})",
        re.IGNORECASE
    )

    def from_profile_bio(self, bio: str, source: str,
                          depth: int) -> List[DiscoveredTarget]:
        """Extract usernames/emails mentioned in a profile bio."""
        targets = []

        # Emails
        for m in self.EMAIL_PATTERN.finditer(bio):
            targets.append(DiscoveredTarget(
                value=m.group(0), type="email",
                source=f"bio on {source}", depth=depth, confidence="HIGH"
            ))

        # Social media handles
        for m in self.SOCIAL_PATTERN.finditer(bio):
            targets.append(DiscoveredTarget(
                value=m.group(1), type="username",
                source=f"social link in {source} bio",
                depth=depth, confidence="HIGH"
            ))

        return targets

    def from_breach_data(self, breach_records: List[Dict],
                          depth: int) -> List[DiscoveredTarget]:
        """Extract username/password hints from breach records."""
        targets = []
        for record in breach_records:
            # Breach database often contains username fields
            for field in ["username", "login", "user", "nick"]:
                val = record.get(field, "")
                if val and isinstance(val, str) and 3 <= len(val) <= 30:
                    targets.append(DiscoveredTarget(
                        value=val, type="username",
                        source=f"breach: {record.get('Name','?')}",
                        depth=depth, confidence="MEDIUM"
                    ))
            # Additional emails
            for field in ["email", "email_address"]:
                val = record.get(field, "")
                if val and "@" in val:
                    targets.append(DiscoveredTarget(
                        value=val, type="email",
                        source=f"breach: {record.get('Name','?')}",
                        depth=depth, confidence="HIGH"
                    ))
        return targets

    def from_github_data(self, github_data: Dict,
                          depth: int) -> List[DiscoveredTarget]:
        """Extract additional targets from GitHub profile API data."""
        targets = []

        # Twitter handle in GitHub
        tw = github_data.get("extra", {}).get("twitter", "")
        if tw:
            targets.append(DiscoveredTarget(
                value=tw, type="username",
                source="GitHub profile (Twitter field)",
                depth=depth, confidence="HIGH"
            ))

        # Email (if public)
        email = github_data.get("extra", {}).get("email", "")
        if email and "@" in email:
            targets.append(DiscoveredTarget(
                value=email, type="email",
                source="GitHub public profile",
                depth=depth, confidence="HIGH"
            ))

        # Blog/website → extract domain-based username hints
        website = github_data.get("website", "")
        if website:
            m = re.search(r"//(?:www\.)?([a-zA-Z0-9_\-]+)\.", website)
            if m:
                hint = m.group(1)
                if hint not in ("github", "twitter", "linkedin", "instagram"):
                    targets.append(DiscoveredTarget(
                        value=hint, type="username",
                        source=f"GitHub website field",
                        depth=depth, confidence="LOW"
                    ))
        return targets

    def from_email_hints(self, email: str, depth: int) -> List[DiscoveredTarget]:
        """Extract username candidates from an email address."""
        from src.modules.name_generator import generate_variants
        local = email.split("@")[0]
        targets = []
        for variant in generate_variants(local, max_variants=8, add_numbers=False):
            targets.append(DiscoveredTarget(
                value=variant, type="username",
                source=f"email local-part: {local}",
                depth=depth, confidence="MEDIUM"
            ))
        return targets


# ─── Recursive Search Orchestrator ────────────────────────────────────────

class RecursiveSearchEngine:
    """
    Orchestrate recursive OSINT:
    1. Start from email → find username → scan → extract new targets → repeat
    2. Depth-limited to prevent infinite loops
    3. Deduplication via visited set
    """

    def __init__(
        self,
        max_depth:         int  = 2,
        max_new_targets:   int  = 5,
        auto_scan:         bool = True,
        workers:           int  = 30,
        timeout:           int  = 10,
        proxy:             Optional[str] = None,
    ):
        self.max_depth       = max_depth
        self.max_new_targets = max_new_targets
        self.auto_scan       = auto_scan
        self.workers         = workers
        self.timeout         = timeout
        self.proxy           = proxy
        self.extractor       = TargetExtractor()

        # State
        self.visited:       Set[str]                   = set()
        self.all_targets:   List[DiscoveredTarget]     = []
        self.scan_history:  List[Dict[str, Any]]       = []

    def run_from_email(
        self,
        email:          str,
        email_data:     Dict,
        breach_data:    List[Dict] = None,
        scan_profiles:  bool = True,
    ) -> Dict[str, Any]:
        """
        Entry point: start recursive search from an email result.

        Args:
            email:         original email
            email_data:    result from email_search module
            breach_data:   breach records (may contain usernames)
            scan_profiles: whether to auto-scan discovered usernames
        """
        log_section("RECURSIVE SEARCH ENGINE")
        log_info(f"Starting from: {Colors.BOLD}{email}{Colors.RESET}")
        log_info(f"Max depth: {self.max_depth} | Max new targets: {self.max_new_targets}")

        self.visited.add(email.lower())

        # ── Depth 0: extract from email itself ────────────────────────
        initial = self.extractor.from_email_hints(email, depth=0)
        self._register_targets(initial)

        # ── Depth 0: extract from breach data ─────────────────────────
        if breach_data:
            breach_targets = self.extractor.from_breach_data(breach_data, depth=0)
            self._register_targets(breach_targets)

        # ── Depth 0: extract from email hints ─────────────────────────
        hints = email_data.get("username_hints", [])
        for h in hints:
            if h not in self.visited:
                self.all_targets.append(DiscoveredTarget(
                    value=h, type="username",
                    source="email username hint", depth=0, confidence="MEDIUM"
                ))

        # ── Auto-scan discovered targets ──────────────────────────────
        if scan_profiles:
            self._scan_discovered(current_depth=0)

        return self._build_report()

    def run_from_username(
        self,
        username:   str,
        scan_results: list,
        profiles:   Optional[List] = None,
    ) -> Dict[str, Any]:
        """
        Run recursive search starting from username scan results.
        Extracts new targets from found profile bios.
        """
        log_section(f"RECURSIVE SEARCH: {username}")
        self.visited.add(username.lower())

        if profiles:
            for p in profiles:
                if isinstance(p, dict):
                    bio = p.get("bio", "")
                    platform = p.get("platform", "?")
                    if bio:
                        bio_targets = self.extractor.from_profile_bio(bio, platform, depth=1)
                        self._register_targets(bio_targets)

                    # GitHub-specific extraction
                    if platform == "GitHub":
                        gh_targets = self.extractor.from_github_data(p, depth=1)
                        self._register_targets(gh_targets)

        if self.all_targets:
            self._scan_discovered(current_depth=1)

        return self._build_report()

    # ── Internal Helpers ──────────────────────────────────────────────────

    def _register_targets(self, targets: List[DiscoveredTarget]):
        """Add new unique targets to the queue."""
        for t in targets:
            key = t.value.lower()
            if key not in self.visited and len(self.all_targets) < 50:
                self.all_targets.append(t)

    def _scan_discovered(self, current_depth: int):
        """Scan all unvisited targets at current depth."""
        if current_depth >= self.max_depth:
            log_warning(f"Max recursion depth ({self.max_depth}) reached. Stopping.")
            return

        to_scan = [
            t for t in self.all_targets
            if t.value.lower() not in self.visited
               and t.depth <= current_depth
               and t.type == "username"
        ][:self.max_new_targets]

        if not to_scan:
            log_info("No new username targets to scan recursively.")
            return

        log_info(f"Recursion depth {current_depth+1}: "
                 f"scanning {len(to_scan)} discovered username(s)...")

        for target in to_scan:
            self.visited.add(target.value.lower())
            self._print_discovered(target)

            if self.auto_scan:
                from src.modules.username_search import _search_single
                results = _search_single(
                    target.value, self.workers, self.timeout,
                    self.proxy, False, False, None, None
                )
                found = [r for r in results if r.status == "FOUND"]
                self.scan_history.append({
                    "target":   target.value,
                    "source":   target.source,
                    "depth":    current_depth + 1,
                    "total":    len(results),
                    "found":    len(found),
                    "profiles": [{"platform": r.platform, "url": r.url}
                                 for r in found],
                })
                log_success(f"  → {target.value}: {len(found)} profile(s) found")

    def _print_discovered(self, target: DiscoveredTarget):
        conf_color = {
            "HIGH": Colors.GREEN, "MEDIUM": Colors.YELLOW, "LOW": Colors.DIM
        }.get(target.confidence, Colors.DIM)
        type_color = Colors.CYAN if target.type == "username" else Colors.MAGENTA
        print(
            f"    {conf_color}[{target.confidence}]{Colors.RESET} "
            f"{type_color}{target.type.upper()}{Colors.RESET} "
            f"{Colors.BOLD}{target.value}{Colors.RESET} "
            f"{Colors.DIM}← {target.source}{Colors.RESET}"
        )

    def _build_report(self) -> Dict[str, Any]:
        total_found = sum(h.get("found", 0) for h in self.scan_history)
        return {
            "discovered_targets": [
                {
                    "value":      t.value,
                    "type":       t.type,
                    "source":     t.source,
                    "depth":      t.depth,
                    "confidence": t.confidence,
                }
                for t in self.all_targets
            ],
            "scan_history":       self.scan_history,
            "total_new_profiles": total_found,
            "recursion_depth":    self.max_depth,
        }
