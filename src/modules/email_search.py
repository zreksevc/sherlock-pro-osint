"""
Email Search Module — Gravatar lookup + breach detection
"""
import hashlib
import re
from typing import Optional, Dict, Any, List

from src.utils.request_handler import RequestHandler
from src.utils.logger import log_section, log_info, log_found, log_error, log_warning, log_success, Colors


def _validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _md5_hash(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode()).hexdigest()


def check_gravatar(email: str, handler: RequestHandler) -> Dict[str, Any]:
    """Check if email has a Gravatar profile."""
    email_hash = _md5_hash(email)
    url = f"https://www.gravatar.com/{email_hash}.json"
    resp = handler.get(url)

    if resp and resp.status_code == 200:
        try:
            data = resp.json()
            entry = data.get("entry", [{}])[0]
            return {
                "found": True,
                "hash": email_hash,
                "url": f"https://gravatar.com/{email_hash}",
                "display_name": entry.get("displayName", ""),
                "profile_url": entry.get("profileUrl", ""),
                "about": entry.get("aboutMe", ""),
                "location": entry.get("currentLocation", ""),
            }
        except Exception:
            return {"found": True, "hash": email_hash, "url": f"https://gravatar.com/{email_hash}"}
    return {"found": False}


def search_email(
    email: str,
    timeout: int = 10,
    proxy: Optional[str] = None,
    use_tor: bool = False,
    hibp_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform email OSINT lookup.

    Checks:
    - Email format validation
    - Gravatar profile lookup
    - HIBP breach check (requires API key)
    - Username variants extraction

    Returns:
        Dictionary with all findings
    """
    log_section(f"EMAIL SEARCH: {email}")
    results: Dict[str, Any] = {
        "email": email,
        "valid": False,
        "gravatar": {},
        "breaches": [],
        "username_hints": [],
    }

    # Validate
    if not _validate_email(email):
        log_warning(f"'{email}' does not appear to be a valid email address.")
        return results

    results["valid"] = True
    log_info(f"Valid email format confirmed.")

    # Extract username hints
    local_part = email.split("@")[0]
    domain = email.split("@")[1]
    results["username_hints"] = _extract_username_hints(local_part)
    results["domain"] = domain
    log_info(f"Username hints extracted: {', '.join(results['username_hints'])}")

    handler = RequestHandler(timeout=timeout, proxy=proxy, use_tor=use_tor)

    # Gravatar check
    log_info("Checking Gravatar profile...")
    gravatar = check_gravatar(email, handler)
    results["gravatar"] = gravatar
    if gravatar["found"]:
        log_found("Gravatar", gravatar.get("url", ""))
        if gravatar.get("display_name"):
            log_info(f"  Name     : {gravatar['display_name']}")
        if gravatar.get("location"):
            log_info(f"  Location : {gravatar['location']}")
    else:
        log_info("No Gravatar profile found.")

    # HIBP breach check
    if hibp_api_key:
        log_info("Checking Have I Been Pwned...")
        breaches = check_hibp(email, hibp_api_key, handler)
        results["breaches"] = breaches
        if breaches:
            log_warning(f"⚠ Email found in {len(breaches)} breach(es)!")
            for b in breaches:
                print(f"    {Colors.RED}[BREACH]{Colors.RESET} {b.get('Name','?')} ({b.get('BreachDate','?')}) — {b.get('DataClasses',[]).__str__()[:80]}")
        else:
            log_success("No breaches found in HIBP database.")
    else:
        log_info("Skipping HIBP check (no API key). Use --hibp-key to enable.")

    handler.close()

    # Summary
    log_section("EMAIL OSINT SUMMARY")
    log_info(f"Email       : {email}")
    log_info(f"Domain      : {domain}")
    log_info(f"Gravatar    : {'✓ Found' if results['gravatar'].get('found') else '✗ Not found'}")
    log_info(f"Breaches    : {len(results['breaches'])} found")
    log_info(f"Username hints: {', '.join(results['username_hints'])}")

    return results


def check_hibp(email: str, api_key: str, handler: RequestHandler) -> List[Dict]:
    """Check email against Have I Been Pwned API v3."""
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
    handler.session.headers.update({
        "hibp-api-key": api_key,
        "user-agent": "OSINT-Sherlock-Pro/2.0",
    })
    resp = handler.get(url)
    if resp is None:
        log_error("HIBP", "Request failed")
        return []
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 404:
        return []
    elif resp.status_code == 401:
        log_error("HIBP", "Invalid API key")
        return []
    elif resp.status_code == 429:
        log_error("HIBP", "Rate limit hit — wait before retrying")
        return []
    return []


def _extract_username_hints(local_part: str) -> List[str]:
    """Extract possible usernames from email local part."""
    hints = set()
    hints.add(local_part)

    # Remove common separators and numbers
    clean = re.sub(r"[._\-]", "", local_part)
    hints.add(clean)

    # Split on separators
    parts = re.split(r"[._\-]", local_part)
    if len(parts) > 1:
        hints.add(parts[0])              # first part
        hints.add("".join(parts))        # joined
        hints.add(parts[0] + parts[-1])  # first + last

    # Remove numbers suffix
    no_num = re.sub(r"\d+$", "", local_part)
    if no_num and no_num != local_part:
        hints.add(no_num)

    return [h for h in hints if h and len(h) >= 2]
