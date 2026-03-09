"""
JSON Report Generator
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from src.core.engine import ScanResult


def generate_json_report(
    target: str,
    scan_type: str,
    results: List[ScanResult],
    extra_data: Dict[str, Any] = None,
    output_dir: str = "reports",
) -> str:
    """Generate a JSON report from scan results."""
    os.makedirs(output_dir, exist_ok=True)

    found = [r for r in results if r.status == "FOUND"]
    not_found = [r for r in results if r.status == "NOT_FOUND"]
    errors = [r for r in results if r.status == "ERROR"]

    report = {
        "meta": {
            "tool": "OSINT Sherlock Pro",
            "version": "2.0",
            "scan_type": scan_type,
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "total_sites": len(results),
            "found": len(found),
            "not_found": len(not_found),
            "errors": len(errors),
        },
        "found_profiles": [
            {
                "platform": r.platform,
                "url": r.url,
                "status_code": r.status_code,
                "tags": r.tags,
            }
            for r in sorted(found, key=lambda x: x.platform)
        ],
        "errors": [
            {"platform": r.platform, "error": r.error_msg}
            for r in errors
        ],
    }

    if extra_data:
        report["extra"] = extra_data

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{scan_type}_{target}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return filename


def generate_csv_report(
    target: str,
    scan_type: str,
    results: List[ScanResult],
    output_dir: str = "reports",
) -> str:
    """Generate a CSV report from scan results."""
    import csv

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{scan_type}_{target}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Platform", "Status", "URL", "HTTP Code", "Tags"])
        for r in sorted(results, key=lambda x: (x.status, x.platform)):
            writer.writerow([
                r.platform,
                r.status,
                r.url,
                r.status_code or "",
                "|".join(r.tags),
            ])

    return filename
