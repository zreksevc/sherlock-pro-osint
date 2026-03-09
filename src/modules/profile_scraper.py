"""
Feature 5: Metadata & Profile Correlation Scraper
=================================================
Scrape lightweight profile data dari platform yang ditemukan.
Digunakan untuk memverifikasi apakah akun di berbagai platform
adalah orang yang sama (cross-platform correlation).
"""
import re
import json
import hashlib
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field

from src.utils.request_handler import RequestHandler
from src.utils.logger import log_info, log_success, log_warning, log_error, Colors


# ─── Profile Data Model ────────────────────────────────────────────────────

@dataclass
class ProfileData:
    platform:    str
    url:         str
    username:    str = ""
    display_name:str = ""
    bio:         str = ""
    location:    str = ""
    website:     str = ""
    followers:   str = ""
    following:   str = ""
    posts:       str = ""
    avatar_url:  str = ""
    joined_date: str = ""
    verified:    bool = False
    extra:       Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "platform":     self.platform,
            "url":          self.url,
            "username":     self.username,
            "display_name": self.display_name,
            "bio":          self.bio,
            "location":     self.location,
            "website":      self.website,
            "followers":    self.followers,
            "avatar_url":   self.avatar_url,
            "joined_date":  self.joined_date,
            "verified":     self.verified,
            "extra":        self.extra,
        }

    def correlation_score(self, other: "ProfileData") -> float:
        """
        Compute similarity score with another profile (0.0 – 1.0).
        Used to detect if two accounts belong to the same person.
        """
        score = 0.0
        checks = 0

        def _compare_field(a: str, b: str, weight: float):
            nonlocal score, checks
            if not a or not b:
                return
            checks += 1
            a_l, b_l = a.lower().strip(), b.lower().strip()
            if a_l == b_l:
                score += weight
            elif a_l in b_l or b_l in a_l:
                score += weight * 0.5

        _compare_field(self.display_name, other.display_name, 2.0)
        _compare_field(self.bio,          other.bio,          1.5)
        _compare_field(self.location,     other.location,     1.0)
        _compare_field(self.website,      other.website,      2.5)
        _compare_field(self.username,     other.username,     1.0)

        if checks == 0:
            return 0.0
        max_score = sum([2.0, 1.5, 1.0, 2.5, 1.0])
        return min(score / max_score, 1.0)


# ─── Platform-specific Scrapers ────────────────────────────────────────────

class ProfileScraper:
    """
    Lightweight meta-scraper for OSINT-relevant public profile data.
    Uses regex on HTML — no API keys required.
    """

    def __init__(self, handler: RequestHandler):
        self.handler = handler

    def scrape(self, platform: str, url: str, username: str) -> Optional[ProfileData]:
        """Dispatch to the correct platform scraper."""
        p = platform.lower()
        scrapers = {
            "github":       self._github,
            "twitter":      self._twitter,
            "instagram":    self._instagram,
            "reddit":       self._reddit,
            "linkedin":     self._linkedin,
            "medium":       self._medium,
            "devto":        self._devto,
            "hackernews":   self._hackernews,
        }
        fn = scrapers.get(p, self._generic)
        try:
            return fn(url, username)
        except Exception as e:
            log_error(platform, f"scrape failed: {e}")
            return self._generic(url, username)

    # ── GitHub ─────────────────────────────────────────────────────────

    def _github(self, url: str, username: str) -> Optional[ProfileData]:
        """Use GitHub public JSON API (no auth for basic info)."""
        api_url = f"https://api.github.com/users/{username}"
        resp    = self.handler.get(api_url)
        if resp is None or resp.status_code != 200:
            return self._generic(url, username)
        try:
            data = resp.json()
            return ProfileData(
                platform     = "GitHub",
                url          = url,
                username     = data.get("login", ""),
                display_name = data.get("name", ""),
                bio          = data.get("bio", "") or "",
                location     = data.get("location", "") or "",
                website      = data.get("blog", "") or "",
                followers    = str(data.get("followers", "")),
                following    = str(data.get("following", "")),
                posts        = str(data.get("public_repos", "")),
                avatar_url   = data.get("avatar_url", ""),
                joined_date  = data.get("created_at", "")[:10],
                extra        = {
                    "company": data.get("company", "") or "",
                    "public_repos": str(data.get("public_repos", 0)),
                    "public_gists": str(data.get("public_gists", 0)),
                    "twitter": data.get("twitter_username", "") or "",
                }
            )
        except Exception:
            return self._generic(url, username)

    # ── Reddit ─────────────────────────────────────────────────────────

    def _reddit(self, url: str, username: str) -> Optional[ProfileData]:
        """Use Reddit JSON API."""
        api_url = f"https://www.reddit.com/user/{username}/about.json"
        self.handler.session.headers.update({"User-Agent": "OSINT-Tool/2.0"})
        resp    = self.handler.get(api_url)
        if resp is None or resp.status_code != 200:
            return self._generic(url, username)
        try:
            data = resp.json().get("data", {})
            karma = data.get("total_karma", 0)
            return ProfileData(
                platform     = "Reddit",
                url          = url,
                username     = data.get("name", ""),
                bio          = data.get("subreddit", {}).get("public_description", ""),
                avatar_url   = data.get("icon_img", ""),
                joined_date  = "",
                extra        = {
                    "link_karma":    str(data.get("link_karma", 0)),
                    "comment_karma": str(data.get("comment_karma", 0)),
                    "total_karma":   str(karma),
                    "is_mod":        str(data.get("is_mod", False)),
                    "verified":      str(data.get("verified", False)),
                }
            )
        except Exception:
            return self._generic(url, username)

    # ── HackerNews ─────────────────────────────────────────────────────

    def _hackernews(self, url: str, username: str) -> Optional[ProfileData]:
        api_url = f"https://hacker-news.firebaseio.com/v0/user/{username}.json"
        resp    = self.handler.get(api_url)
        if resp is None or resp.status_code != 200:
            return self._generic(url, username)
        try:
            data = resp.json() or {}
            return ProfileData(
                platform    = "HackerNews",
                url         = url,
                username    = data.get("id", ""),
                bio         = re.sub(r"<[^>]+>", "", data.get("about", "") or ""),
                joined_date = "",
                extra       = {
                    "karma":        str(data.get("karma", 0)),
                    "submitted":    str(len(data.get("submitted", []))),
                }
            )
        except Exception:
            return self._generic(url, username)

    # ── Dev.to ─────────────────────────────────────────────────────────

    def _devto(self, url: str, username: str) -> Optional[ProfileData]:
        api_url = f"https://dev.to/api/users/by_username?url={username}"
        resp    = self.handler.get(api_url)
        if resp is None or resp.status_code != 200:
            return self._generic(url, username)
        try:
            data = resp.json()
            return ProfileData(
                platform     = "Dev.to",
                url          = url,
                username     = data.get("username", ""),
                display_name = data.get("name", ""),
                bio          = data.get("summary", "") or "",
                location     = data.get("location", "") or "",
                website      = data.get("website_url", "") or "",
                avatar_url   = data.get("profile_image", ""),
                joined_date  = data.get("joined_at", "")[:10],
                extra        = {
                    "twitter":  data.get("twitter_username", "") or "",
                    "github":   data.get("github_username", "") or "",
                }
            )
        except Exception:
            return self._generic(url, username)

    # ── Twitter (HTML scrape only) ────────────────────────────────────

    def _twitter(self, url: str, username: str) -> Optional[ProfileData]:
        return self._generic_meta(url, username, "Twitter")

    def _instagram(self, url: str, username: str) -> Optional[ProfileData]:
        return self._generic_meta(url, username, "Instagram")

    def _linkedin(self, url: str, username: str) -> Optional[ProfileData]:
        return self._generic_meta(url, username, "LinkedIn")

    def _medium(self, url: str, username: str) -> Optional[ProfileData]:
        return self._generic_meta(url, username, "Medium")

    # ── Generic HTML meta-scraper ─────────────────────────────────────

    def _generic_meta(self, url: str, username: str, platform: str) -> Optional[ProfileData]:
        """Extract Open Graph / meta tags from any page."""
        resp = self.handler.get(url)
        if resp is None or resp.status_code != 200:
            return None
        return self._parse_meta(resp.text, platform, url, username)

    def _generic(self, url: str, username: str) -> Optional[ProfileData]:
        """Fallback: try meta tags."""
        return self._generic_meta(url, username, "Unknown")

    def _parse_meta(self, html: str, platform: str, url: str, username: str) -> ProfileData:
        """Extract OG/meta tags and schema.org data."""
        pd = ProfileData(platform=platform, url=url, username=username)

        patterns = {
            "display_name": [
                r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"',
                r'<title>([^<|]+)',
            ],
            "bio": [
                r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"',
                r'<meta[^>]+name="description"[^>]+content="([^"]+)"',
            ],
            "avatar_url": [
                r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
            ],
        }

        for field_name, pats in patterns.items():
            for pat in pats:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    if val and len(val) > 2:
                        setattr(pd, field_name, val)
                        break

        return pd


# ─── Correlation Engine ────────────────────────────────────────────────────

class CorrelationEngine:
    """
    Compare scraped profiles across platforms to detect same-person accounts.
    """

    @staticmethod
    def correlate(profiles: List[ProfileData]) -> List[Dict[str, Any]]:
        """Return pairwise similarity scores."""
        matches = []
        for i in range(len(profiles)):
            for j in range(i + 1, len(profiles)):
                a, b = profiles[i], profiles[j]
                score = a.correlation_score(b)
                if score > 0.2:
                    matches.append({
                        "platform_a": a.platform,
                        "platform_b": b.platform,
                        "score":      round(score, 2),
                        "level":      CorrelationEngine._level(score),
                        "evidence":   CorrelationEngine._evidence(a, b),
                    })
        return sorted(matches, key=lambda x: -x["score"])

    @staticmethod
    def _level(score: float) -> str:
        if score >= 0.7: return "HIGH"
        if score >= 0.4: return "MEDIUM"
        return "LOW"

    @staticmethod
    def _evidence(a: ProfileData, b: ProfileData) -> List[str]:
        ev = []
        def check(field_name, label):
            va = getattr(a, field_name, "").lower().strip()
            vb = getattr(b, field_name, "").lower().strip()
            if va and vb and (va == vb or va in vb or vb in va):
                ev.append(f"Same {label}: '{va[:40]}'")
        check("display_name", "display name")
        check("bio",          "bio keywords")
        check("location",     "location")
        check("website",      "website")
        return ev


# ─── Orchestrator ──────────────────────────────────────────────────────────

class ProfileMetadataCollector:
    """
    Collect metadata from all FOUND profiles and run correlation analysis.
    """

    SUPPORTED_PLATFORMS = {
        "github", "reddit", "hackernews", "devto",
        "twitter", "instagram", "linkedin", "medium",
    }

    def __init__(self, timeout: int = 10, proxy: Optional[str] = None,
                 max_profiles: int = 20):
        self.handler    = RequestHandler(timeout=timeout, proxy=proxy)
        self.scraper    = ProfileScraper(self.handler)
        self.correlator = CorrelationEngine()
        self.max        = max_profiles

    def collect(self, found_results: list, username: str) -> Dict[str, Any]:
        """
        Collect metadata from all found profiles.
        Returns dict with profiles + correlation report.
        """
        from src.utils.logger import log_section
        log_section("PROFILE METADATA COLLECTION")

        profiles   : List[ProfileData] = []
        scraped     = 0

        for result in found_results:
            if scraped >= self.max:
                break
            if result.status != "FOUND":
                continue
            if result.platform.lower() not in self.SUPPORTED_PLATFORMS:
                continue

            log_info(f"Scraping {result.platform}...")
            pd = self.scraper.scrape(result.platform, result.url, username)
            if pd:
                profiles.append(pd)
                scraped += 1
                # Show what was found
                fields_found = [f for f in ["display_name","bio","location","website"]
                                if getattr(pd, f)]
                if fields_found:
                    log_success(f"  {result.platform}: {', '.join(fields_found)}")
                else:
                    log_info(f"  {result.platform}: no metadata")

        # Correlation analysis
        correlations = self.correlator.correlate(profiles) if len(profiles) >= 2 else []

        if correlations:
            print(f"\n  {Colors.CYAN}{Colors.BOLD}Cross-Platform Correlation:{Colors.RESET}")
            for c in correlations[:5]:
                level_color = {
                    "HIGH": Colors.GREEN, "MEDIUM": Colors.YELLOW, "LOW": Colors.DIM
                }.get(c["level"], Colors.DIM)
                print(f"    {level_color}[{c['level']}]{Colors.RESET} "
                      f"{c['platform_a']} ↔ {c['platform_b']}  "
                      f"score: {c['score']:.0%}")
                for ev in c.get("evidence", []):
                    print(f"      {Colors.DIM}• {ev}{Colors.RESET}")

        return {
            "profiles":      [p.to_dict() for p in profiles],
            "correlations":  correlations,
            "scraped_count": scraped,
        }

    def close(self):
        self.handler.close()
