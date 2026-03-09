"""
Username Search Module — Full Name + Async Engine + Recursive
"""
import re
from typing import Optional, List, Dict

from src.core.async_engine import AsyncScanEngine, ScanResult
from src.modules.name_generator import (
    generate_variants, is_full_name, sanitize_for_filename
)
from src.utils.logger import (
    log_section, log_info, log_success, log_warning, Colors
)


def search_username(
    username: str,
    workers:  int = 50,
    timeout:  int = 10,
    proxy:    Optional[str] = None,
    use_tor:  bool = False,
    verbose:  bool = False,
    sites:    Optional[List[str]] = None,
    tags:     Optional[List[str]] = None,
) -> List[ScanResult]:
    raw = username.strip()
    if not raw:
        log_warning("Username/name cannot be empty.")
        return []
    if is_full_name(raw):
        return _search_full_name(raw, workers, timeout, proxy, use_tor, verbose, sites, tags)
    return _search_single(raw, workers, timeout, proxy, use_tor, verbose, sites, tags)


def _search_full_name(full_name, workers, timeout, proxy, use_tor, verbose, sites, tags):
    log_section(f"FULL NAME SEARCH: {full_name}")
    variants = generate_variants(full_name, max_variants=20)

    print(f"\n  {Colors.CYAN}[*]{Colors.RESET} Detected: {Colors.BOLD}Full Name{Colors.RESET}")
    print(f"  {Colors.CYAN}[*]{Colors.RESET} Generated {Colors.BOLD}{len(variants)}{Colors.RESET} username variants:\n")
    for i, v in enumerate(variants, 1):
        print(f"      {Colors.DIM}{i:>2}.{Colors.RESET}  {Colors.BOLD}{Colors.CYAN}{v}{Colors.RESET}")
    print()

    found_platforms: Dict[str, ScanResult] = {}

    for i, variant in enumerate(variants, 1):
        print(f"\n  {Colors.YELLOW}[→]{Colors.RESET} Scanning variant "
              f"{Colors.BOLD}{i}/{len(variants)}{Colors.RESET}: "
              f"{Colors.BOLD}{Colors.CYAN}{variant}{Colors.RESET}")
        for r in _search_single(variant, workers, timeout, proxy, use_tor, verbose, sites, tags):
            existing = found_platforms.get(r.platform)
            if existing is None or (r.status == "FOUND" and existing.status != "FOUND"):
                found_platforms[r.platform] = r

    all_results = list(found_platforms.values())
    found  = [r for r in all_results if r.status == "FOUND"]
    errors = [r for r in all_results if r.status == "ERROR"]

    log_section("FULL NAME SEARCH COMPLETE")
    log_info(f"Variants scanned : {len(variants)}")
    log_info(f"Sites checked    : {len(all_results)}")
    log_success(f"Profiles FOUND   : {len(found)}")
    if errors:
        log_warning(f"Errors/Timeouts  : {len(errors)}")
    if found:
        print(f"\n  {Colors.BOLD}{Colors.CYAN}All found profiles:{Colors.RESET}")
        for r in sorted(found, key=lambda x: x.platform):
            conf_badge = ""
            if hasattr(r, "confidence") and r.confidence:
                c = {"HIGH": Colors.GREEN, "MEDIUM": Colors.YELLOW, "LOW": Colors.RED}
                conf_badge = f" {c.get(r.confidence,'')}[{r.confidence}]{Colors.RESET}"
            print(f"    {Colors.GREEN}→{Colors.RESET} "
                  f"{Colors.BOLD}{r.platform:<25}{Colors.RESET}"
                  f"{conf_badge}  {r.url}")
    return all_results


def _search_single(username, workers, timeout, proxy, use_tor, verbose, sites, tags):
    username = re.sub(r"[^\w.\-]", "", username).lower()
    if not username:
        log_warning("After sanitization, username is empty. Skipping.")
        return []
    log_section(f"USERNAME: {username}")
    engine = AsyncScanEngine(
        workers=workers, timeout=timeout,
        proxy=proxy, use_tor=use_tor,
        verbose=verbose, sites_filter=sites, tags_filter=tags,
    )
    results = engine.scan(username)
    found  = [r for r in results if r.status == "FOUND"]
    errors = [r for r in results if r.status == "ERROR"]
    log_info(f"Found: {Colors.GREEN}{len(found)}{Colors.RESET} / {len(results)} | "
             f"Errors: {len(errors)}")
    return results
