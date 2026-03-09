#!/usr/bin/env python3
"""
OSINT Sherlock Pro v3.0 — Main CLI Entry Point
=================================================
Usage:
    python main.py username johndoe
    python main.py username "Budi Santoso"        # Full name auto-variant
    python main.py username johndoe --html --json --meta --recursive
    python main.py email johndoe@gmail.com --html
    python main.py search "Budi Santoso" --dork   # Google dorking
    python main.py breach johndoe@gmail.com --hibp-key KEY
    python main.py list-sites
    python main.py list-tags
"""

import argparse
import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import print_banner, log_info, log_warning, log_success, log_error, Colors
from src.modules.username_search import search_username
from src.modules.email_search import search_email
from src.modules.breach_checker import BreachChecker
from src.modules.dorking import DorkScanner
from src.modules.profile_scraper import ProfileMetadataCollector
from src.modules.recursive_search import RecursiveSearchEngine
from src.modules.name_generator import generate_variants, sanitize_for_filename
from src.core.async_engine import load_sites
from src.report.html_report import generate_html_report
from src.report.json_report import generate_json_report, generate_csv_report


# ─── Argument Parser ───────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="osint-sherlock-pro",
        description="🔍 OSINT Sherlock Pro v3.0 — Username & Email Intelligence Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py username johndoe --meta --recursive
  python main.py username "Budi Santoso" --html
  python main.py email johndoe@gmail.com --html --recursive
  python main.py search "Budi Santoso" --dork
  python main.py search "Budi Santoso" --dork --dork-live
  python main.py breach johndoe@gmail.com --hibp-key KEY
  python main.py list-sites | list-tags
  python main.py username johndoe --tags social gaming --workers 60
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # ── username ──────────────────────────────────────────────────────────
    up = sub.add_parser("username", help="Scan username or full name across 100+ sites")
    up.add_argument("target", help="Username or full name (e.g. 'Budi Santoso')")
    _add_scan_args(up)
    _add_output_args(up)
    _add_network_args(up)
    up.add_argument("--meta",      action="store_true", help="Scrape profile metadata (bio, location, followers)")
    up.add_argument("--recursive", action="store_true", help="Auto-discover & scan new targets from found profiles")
    up.add_argument("--dork",      action="store_true", help="Also generate dork queries for the target")

    # ── email ─────────────────────────────────────────────────────────────
    ep = sub.add_parser("email", help="Email OSINT (Gravatar, breach, username hints)")
    ep.add_argument("target", help="Email address")
    ep.add_argument("--hibp-key",   metavar="KEY", help="Have I Been Pwned API key")
    ep.add_argument("--recursive",  action="store_true", help="Auto-scan discovered usernames from email/breach")
    ep.add_argument("--also-scan",  action="store_true", help="Run username scan on email hints")
    _add_output_args(ep)
    _add_network_args(ep)

    # ── search (dork) ─────────────────────────────────────────────────────
    sp = sub.add_parser("search", help="Google Dorking — generate or run search queries")
    sp.add_argument("target",        help="Name or keyword to dork")
    sp.add_argument("--dork",        action="store_true", default=True, help="Generate dork queries")
    sp.add_argument("--dork-live",   action="store_true", help="Live DuckDuckGo search (rate-limited)")
    sp.add_argument("--dork-cats",   nargs="+", metavar="CAT",
                    help="Filter categories (Social Media, Developer, Documents, ...)")
    _add_output_args(sp)
    _add_network_args(sp)

    # ── breach ────────────────────────────────────────────────────────────
    bp = sub.add_parser("breach", help="Check email against breach databases")
    bp.add_argument("target",            help="Email address")
    bp.add_argument("--hibp-key",        metavar="KEY")
    bp.add_argument("--leakcheck-key",   metavar="KEY")
    bp.add_argument("--dehashed-user",   metavar="USER")
    bp.add_argument("--dehashed-key",    metavar="KEY")
    _add_network_args(bp)

    # ── list-sites / list-tags ────────────────────────────────────────────
    sub.add_parser("list-sites", help="List all sites in database")
    sub.add_parser("list-tags",  help="List all available site tags")

    # ── variants (debug helper) ───────────────────────────────────────────
    vp = sub.add_parser("variants", help="Preview username variants for a name")
    vp.add_argument("target", help="Name to generate variants for")
    vp.add_argument("--max", type=int, default=25)

    return parser


def _add_scan_args(p):
    p.add_argument("--workers", "-w", type=int, default=50)
    p.add_argument("--timeout", "-t", type=int, default=10)
    p.add_argument("--sites",   nargs="+", metavar="SITE")
    p.add_argument("--tags",    nargs="+", metavar="TAG")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--delay",   type=float, default=0.0)

def _add_output_args(p):
    p.add_argument("--json",       action="store_true")
    p.add_argument("--csv",        action="store_true")
    p.add_argument("--no-report",  action="store_true", help="Skip report generation")
    p.add_argument("--output-dir", default="reports", metavar="DIR")

def _add_network_args(p):
    p.add_argument("--proxy", metavar="URL")
    p.add_argument("--tor",   action="store_true")


# ─── Command: username ─────────────────────────────────────────────────────

def cmd_username(args):
    results = search_username(
        username = args.target,
        workers  = args.workers,
        timeout  = args.timeout,
        proxy    = args.proxy,
        use_tor  = args.tor,
        verbose  = args.verbose,
        sites    = args.sites,
        tags     = args.tags,
    )

    extra_data = {"original_name": args.target}
    found = [r for r in results if r.status == "FOUND"]

    # ── Feature 5: Metadata scraping ──────────────────────────────────
    if getattr(args, "meta", False) and found:
        log_info("Starting profile metadata collection...")
        collector = ProfileMetadataCollector(
            timeout=args.timeout, proxy=args.proxy
        )
        meta = collector.collect(found, username=re.sub(r"\s+","",args.target).lower())
        collector.close()
        extra_data["metadata"] = meta

    # ── Feature 2: Dork generation ────────────────────────────────────
    if getattr(args, "dork", False):
        scanner = DorkScanner(live_search=False)
        dork_results = scanner.scan(args.target)
        extra_data["dorks"] = [
            {"query": {"category":d.query.category,"description":d.query.description,
                       "query":d.query.query,"google_url":d.query.google_url},
             "results": d.results}
            for d in dork_results
        ]

    # ── Feature 6: Recursive search ───────────────────────────────────
    if getattr(args, "recursive", False) and found:
        profiles = extra_data.get("metadata", {}).get("profiles", [])
        engine   = RecursiveSearchEngine(
            max_depth=2, max_new_targets=4, auto_scan=False,
            workers=args.workers, timeout=args.timeout, proxy=args.proxy,
        )
        rec = engine.run_from_username(args.target, results, profiles)
        extra_data["recursive"] = rec

    safe_target = sanitize_for_filename(args.target)
    _save_reports("username", safe_target, results, args, extra_data)


# ─── Command: email ────────────────────────────────────────────────────────

def cmd_email(args):
    email_data = search_email(
        email       = args.target,
        timeout     = 10,
        proxy       = getattr(args, "proxy", None),
        use_tor     = getattr(args, "tor", False),
        hibp_api_key= getattr(args, "hibp_key", None),
    )

    extra_data = {
        "gravatar":       email_data.get("gravatar", {}),
        "breaches":       email_data.get("breaches", []),
        "username_hints": email_data.get("username_hints", []),
        "domain":         email_data.get("domain", ""),
    }

    results = []

    # Also scan username hints if requested
    if getattr(args, "also_scan", False) and email_data.get("username_hints"):
        for hint in email_data["username_hints"][:3]:
            results.extend(search_username(
                username=hint,
                workers=getattr(args,"workers",50),
                timeout=getattr(args,"timeout",10),
                proxy=getattr(args,"proxy",None),
            ))

    # ── Feature 6: Recursive from email ──────────────────────────────
    if getattr(args, "recursive", False):
        engine = RecursiveSearchEngine(
            max_depth=2, max_new_targets=5, auto_scan=False,
        )
        rec = engine.run_from_email(
            email       = args.target,
            email_data  = email_data,
            breach_data = email_data.get("breaches", []),
        )
        extra_data["recursive"] = rec

    if not getattr(args, "no_report", False):
        _save_reports("email", re.sub(r"[^\w.\-]","_",args.target), results, args, extra_data)


# ─── Command: search (dork) ────────────────────────────────────────────────

def cmd_search(args):
    live = getattr(args, "dork_live", False)
    cats = getattr(args, "dork_cats", None)
    scanner = DorkScanner(
        live_search=live,
        timeout=getattr(args,"timeout",15),
        proxy=getattr(args,"proxy",None),
        categories=cats,
    )
    dork_results = scanner.scan(args.target)
    scanner.close()

    if not getattr(args, "no_report", False):
        extra_data = {
            "dorks": [
                {"query": {"category":d.query.category,"description":d.query.description,
                           "query":d.query.query,"google_url":d.query.google_url},
                 "results": d.results}
                for d in dork_results
            ]
        }
        safe = sanitize_for_filename(args.target)
        _save_reports("search", safe, [], args, extra_data)


# ─── Command: breach ───────────────────────────────────────────────────────

def cmd_breach(args):
    checker = BreachChecker(
        hibp_key       = getattr(args, "hibp_key", None),
        leakcheck_key  = getattr(args, "leakcheck_key", None),
        dehashed_user  = getattr(args, "dehashed_user", None),
        dehashed_key   = getattr(args, "dehashed_key", None),
        proxy          = getattr(args, "proxy", None),
    )
    checker.check_all(args.target)
    checker.close()


# ─── Command: list-sites / list-tags ───────────────────────────────────────

def cmd_list_sites():
    sites = load_sites()
    print(f"\n  {Colors.CYAN}{Colors.BOLD}Sites in Database ({len(sites)} total){Colors.RESET}\n")
    for i, (name, data) in enumerate(sorted(sites.items()), 1):
        tags = ", ".join(data.get("tags", []))
        print(f"  {Colors.DIM}{i:>3}.{Colors.RESET} {Colors.BOLD}{name:<30}{Colors.RESET} {Colors.DIM}{tags}{Colors.RESET}")
    print()

def cmd_list_tags():
    sites = load_sites()
    tag_counts: dict = {}
    for data in sites.values():
        for tag in data.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    print(f"\n  {Colors.CYAN}{Colors.BOLD}Available Tags{Colors.RESET}\n")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 20)
        print(f"  {Colors.BLUE}{tag:<20}{Colors.RESET} {Colors.GREEN}{bar}{Colors.RESET} {count}")
    print()

def cmd_variants(args):
    from src.modules.name_generator import generate_variants
    vs = generate_variants(args.target, max_variants=args.max)
    print(f"\n  {Colors.CYAN}{Colors.BOLD}Username variants for: {args.target}{Colors.RESET}")
    print(f"  Generated {len(vs)} variants:\n")
    for i, v in enumerate(vs, 1):
        print(f"  {Colors.DIM}{i:>3}.{Colors.RESET} {Colors.BOLD}{v}{Colors.RESET}")
    print()


# ─── Report Helper ─────────────────────────────────────────────────────────

def _save_reports(scan_type, target, results, args, extra_data=None):
    if getattr(args, "no_report", False):
        return
    output_dir = getattr(args, "output_dir", "reports")

    # HTML always auto-generated
    html_path = generate_html_report(target, scan_type, results, extra_data, output_dir)
    log_success(f"HTML report → {html_path}")
    _try_open_browser(html_path)

    if getattr(args, "json", False):
        p = generate_json_report(target, scan_type, results, extra_data, output_dir)
        log_success(f"JSON report → {p}")
    if getattr(args, "csv", False) and results:
        p = generate_csv_report(target, scan_type, results, output_dir)
        log_success(f"CSV  report → {p}")

def _try_open_browser(filepath: str):
    import subprocess, platform as _platform
    path = os.path.abspath(filepath)
    try:
        sys_name = _platform.system()
        if sys_name == "Windows":
            os.startfile(path)
        elif sys_name == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log_info("Opening report in browser...")
    except Exception:
        pass


# ─── Entry Point ───────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args   = parser.parse_args()
    print_banner()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    t0 = time.time()
    dispatch = {
        "username":   cmd_username,
        "email":      cmd_email,
        "search":     cmd_search,
        "breach":     cmd_breach,
        "list-sites": lambda _: cmd_list_sites(),
        "list-tags":  lambda _: cmd_list_tags(),
        "variants":   cmd_variants,
    }
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()

    print(f"\n  {Colors.DIM}Total time: {time.time()-t0:.2f}s{Colors.RESET}\n")

if __name__ == "__main__":
    main()
