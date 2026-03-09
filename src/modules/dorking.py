"""
Feature 2: Google Dorking Automation Module
==========================================
Generate dan format Google dork queries untuk OSINT manual.
Juga mencoba scraping via DuckDuckGo HTML (tidak perlu API key).
"""
import re
import urllib.parse
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from src.utils.request_handler import RequestHandler
from src.utils.logger import log_section, log_info, log_warning, log_success, log_error, Colors


# ─── Data Classes ──────────────────────────────────────────────────────────

@dataclass
class DorkQuery:
    category:    str
    description: str
    query:       str
    search_url:  str
    google_url:  str

@dataclass
class DorkResult:
    query:      DorkQuery
    results:    List[Dict[str, str]] = field(default_factory=list)
    success:    bool = False
    error:      str  = ""


# ─── Dork Template Builder ─────────────────────────────────────────────────

class DorkBuilder:
    """Build categorized dork queries for a given name/username/email."""

    DORK_TEMPLATES = [
        # ── Social Media ──────────────────────────────────────────────────
        ("Social Media", "LinkedIn Profile",
         'site:linkedin.com/in "{target}"'),
        ("Social Media", "Instagram Profile",
         'site:instagram.com "{target}"'),
        ("Social Media", "Twitter/X Profile",
         'site:twitter.com "{target}" OR site:x.com "{target}"'),
        ("Social Media", "Facebook Profile",
         'site:facebook.com "{target}"'),
        ("Social Media", "TikTok Profile",
         'site:tiktok.com "@{target}"'),

        # ── Professional / Developer ──────────────────────────────────────
        ("Developer", "GitHub Profile",
         'site:github.com "{target}"'),
        ("Developer", "GitLab Profile",
         'site:gitlab.com "{target}"'),
        ("Developer", "Stack Overflow",
         'site:stackoverflow.com/users "{target}"'),
        ("Developer", "Dev.to Profile",
         'site:dev.to "{target}"'),
        ("Developer", "Medium Profile",
         'site:medium.com "@{target}"'),

        # ── Documents & Files ─────────────────────────────────────────────
        ("Documents", "PDF Documents",
         '"{target}" filetype:pdf'),
        ("Documents", "Word Documents",
         '"{target}" filetype:doc OR filetype:docx'),
        ("Documents", "CV / Resume",
         '"{target}" filetype:pdf (CV OR resume OR curriculum)'),
        ("Documents", "Spreadsheets",
         '"{target}" filetype:xlsx OR filetype:csv'),
        ("Documents", "Presentations",
         '"{target}" filetype:pptx OR filetype:ppt'),

        # ── Email & Contact ───────────────────────────────────────────────
        ("Contact", "Email Exposure",
         '"{target}" "@gmail.com" OR "@yahoo.com" OR "@outlook.com"'),
        ("Contact", "Phone Number Exposure",
         '"{target}" (phone OR "phone number" OR "no hp" OR "nomor hp")'),
        ("Contact", "Contact Page",
         '"{target}" (contact OR "hubungi saya" OR "kontak")'),

        # ── News & Mentions ───────────────────────────────────────────────
        ("Mentions", "News Articles",
         '"{target}" (news OR artikel OR berita)'),
        ("Mentions", "Forum Discussions",
         '"{target}" site:reddit.com OR site:quora.com OR site:kaskus.co.id'),
        ("Mentions", "Blog Mentions",
         '"{target}" (blogspot.com OR wordpress.com OR medium.com)'),
        ("Mentions", "Academic Papers",
         '"{target}" site:scholar.google.com OR site:researchgate.net'),

        # ── Indonesian Specific ───────────────────────────────────────────
        ("Indonesia", "Indonesian Directories",
         '"{target}" site:linkedin.com OR site:kaskus.co.id OR site:detik.com'),
        ("Indonesia", "Indonesian Social",
         '"{target}" site:instagram.com OR site:line.me'),
        ("Indonesia", "Academic Indonesia",
         '"{target}" site:academia.edu OR site:.ac.id'),

        # ── Leaked / Sensitive ────────────────────────────────────────────
        ("Security", "Pastebin Leaks",
         'site:pastebin.com "{target}"'),
        ("Security", "GitHub Code Mentions",
         'site:github.com "{target}" password OR token OR credential'),
        ("Security", "Wayback Machine",
         'site:web.archive.org "{target}"'),
    ]

    def build(self, target: str) -> List[DorkQuery]:
        queries = []
        for category, description, template in self.DORK_TEMPLATES:
            raw_query = template.replace("{target}", target)
            encoded   = urllib.parse.quote_plus(raw_query)
            ddg_url   = f"https://html.duckduckgo.com/html/?q={encoded}"
            google_url= f"https://www.google.com/search?q={encoded}"
            queries.append(DorkQuery(
                category    = category,
                description = description,
                query       = raw_query,
                search_url  = ddg_url,
                google_url  = google_url,
            ))
        return queries


# ─── DuckDuckGo Scraper (no API needed) ───────────────────────────────────

class DuckDuckGoScraper:
    """
    Scrape search results from DuckDuckGo HTML endpoint.
    No API key required. Rate-limited to avoid blocks.
    """

    def __init__(self, handler: RequestHandler, delay: float = 2.0):
        self.handler = handler
        self.delay   = delay

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Run a single DDG search, return list of {title, url, snippet}."""
        encoded = urllib.parse.quote_plus(query)
        url     = f"https://html.duckduckgo.com/html/?q={encoded}"

        time.sleep(self.delay)
        resp = self.handler.get(url)
        if resp is None or resp.status_code != 200:
            return []

        return self._parse_html(resp.text, max_results)

    def _parse_html(self, html: str, max_results: int) -> List[Dict[str, str]]:
        """Extract results from DDG HTML response."""
        results = []
        # DDG HTML result pattern: <a class="result__a" href="...">title</a>
        # Snippet: <a class="result__snippet">...</a>
        link_pattern    = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)

        links    = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (href, title) in enumerate(links[:max_results]):
            # DDG uses redirect URLs — extract real URL
            real_url = self._extract_url(href)
            title    = re.sub(r"<[^>]+>", "", title).strip()
            snippet  = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""

            if real_url and title:
                results.append({
                    "title":   title,
                    "url":     real_url,
                    "snippet": snippet[:200],
                })

        return results

    def _extract_url(self, href: str) -> str:
        """Extract real URL from DDG redirect."""
        if href.startswith("//duckduckgo.com/l/?"):
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse("https:" + href).query)
            return parsed.get("uddg", [href])[0]
        if href.startswith("http"):
            return href
        return ""


# ─── Main Dorking Module ───────────────────────────────────────────────────

class DorkScanner:
    """
    Orchestrate dork query generation + optional live search.
    """

    def __init__(
        self,
        live_search: bool = False,
        timeout: int = 15,
        proxy: Optional[str] = None,
        categories: Optional[List[str]] = None,
        max_results_per_query: int = 5,
    ):
        self.live_search   = live_search
        self.categories    = [c.lower() for c in categories] if categories else None
        self.max_results   = max_results_per_query
        self.builder       = DorkBuilder()

        if live_search:
            self.handler = RequestHandler(timeout=timeout, proxy=proxy)
            self.scraper = DuckDuckGoScraper(self.handler, delay=2.5)
        else:
            self.handler = None
            self.scraper = None

    def scan(self, target: str) -> List[DorkResult]:
        queries = self.builder.build(target)

        # Filter by category
        if self.categories:
            queries = [q for q in queries if q.category.lower() in self.categories]

        log_section(f"GOOGLE DORKING: {target}")
        log_info(f"Generated {len(queries)} dork queries")

        if not self.live_search:
            log_info("Mode: QUERY GENERATION ONLY (use --dork-live for live search)")
            log_warning("Live search disabled to avoid rate limiting by default.")

        results = []
        by_cat: Dict[str, List[DorkResult]] = {}

        for q in queries:
            dr = DorkResult(query=q)

            if self.live_search and self.scraper:
                log_info(f"Searching: {q.description}...")
                hits = self.scraper.search(q.query, self.max_results)
                dr.results = hits
                dr.success = True
                if hits:
                    log_success(f"  {q.description}: {len(hits)} result(s)")
                else:
                    log_info(f"  {q.description}: no results")
            else:
                dr.success = False  # no live search

            results.append(dr)
            by_cat.setdefault(q.category, []).append(dr)

        # Print query summary
        self._print_summary(by_cat, target)
        return results

    def _print_summary(self, by_cat: Dict, target: str):
        log_section("DORK QUERIES (copy to browser)")
        for category, items in by_cat.items():
            print(f"\n  {Colors.CYAN}{Colors.BOLD}[{category}]{Colors.RESET}")
            for dr in items:
                print(f"    {Colors.DIM}→{Colors.RESET} {Colors.YELLOW}{dr.query.description:<35}{Colors.RESET}")
                print(f"      {Colors.DIM}{dr.query.google_url[:100]}...{Colors.RESET}")
                if dr.results:
                    for r in dr.results[:3]:
                        print(f"        {Colors.GREEN}•{Colors.RESET} {r['title'][:60]}")
                        print(f"          {Colors.BLUE}{r['url'][:80]}{Colors.RESET}")

    def close(self):
        if self.handler:
            self.handler.close()


# ─── Standalone test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    scanner = DorkScanner(live_search=False)
    results = scanner.scan("Budi Santoso")
    print(f"\nTotal dork queries generated: {len(results)}")
