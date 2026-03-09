"""
HTML Dashboard Report Generator — Professional OSINT Report
"""
import os
from datetime import datetime
from typing import List, Dict, Any
from src.core.engine import ScanResult


def generate_html_report(
    target: str,
    scan_type: str,
    results: List[ScanResult],
    extra_data: Dict[str, Any] = None,
    output_dir: str = "reports",
) -> str:
    """Generate a full HTML dashboard report."""
    os.makedirs(output_dir, exist_ok=True)

    found = [r for r in results if r.status == "FOUND"]
    not_found = [r for r in results if r.status == "NOT_FOUND"]
    errors = [r for r in results if r.status == "ERROR"]

    # Build tag statistics
    tag_stats: Dict[str, int] = {}
    for r in found:
        for tag in r.tags:
            tag_stats[tag] = tag_stats.get(tag, 0) + 1

    # Build found rows HTML
    found_rows = ""
    for r in sorted(found, key=lambda x: x.platform):
        tags_html = " ".join(
            f'<span class="tag">{t}</span>' for t in r.tags
        )
        found_rows += f"""
        <tr class="found-row">
            <td><strong>{r.platform}</strong></td>
            <td><span class="badge badge-found">FOUND</span></td>
            <td><a href="{r.url}" target="_blank" rel="noopener">{r.url}</a></td>
            <td>{tags_html}</td>
            <td>{r.status_code or '—'}</td>
        </tr>"""

    # Build all results rows
    all_rows = ""
    for r in sorted(results, key=lambda x: (0 if x.status == "FOUND" else 1, x.platform)):
        if r.status == "FOUND":
            badge = '<span class="badge badge-found">FOUND</span>'
            row_class = "found-row"
        elif r.status == "NOT_FOUND":
            badge = '<span class="badge badge-notfound">NOT FOUND</span>'
            row_class = "notfound-row"
        else:
            badge = '<span class="badge badge-error">ERROR</span>'
            row_class = "error-row"

        tags_html = " ".join(f'<span class="tag">{t}</span>' for t in r.tags)
        url_cell = f'<a href="{r.url}" target="_blank" rel="noopener">{r.url}</a>' if r.url else "—"
        all_rows += f"""
        <tr class="{row_class}">
            <td><strong>{r.platform}</strong></td>
            <td>{badge}</td>
            <td>{url_cell}</td>
            <td>{tags_html}</td>
            <td>{r.status_code or '—'}</td>
        </tr>"""

    # Chart data
    chart_labels = list(tag_stats.keys()) if tag_stats else ["No data"]
    chart_values = list(tag_stats.values()) if tag_stats else [0]

    # Extra section (email/breach data)
    extra_section = ""
    if extra_data:
        if extra_data.get("gravatar", {}).get("found"):
            g = extra_data["gravatar"]
            extra_section += f"""
        <div class="info-card">
            <h3>📸 Gravatar Profile</h3>
            <table class="info-table">
                <tr><td>Hash</td><td>{g.get('hash','')}</td></tr>
                <tr><td>Display Name</td><td>{g.get('display_name','—')}</td></tr>
                <tr><td>Location</td><td>{g.get('location','—')}</td></tr>
                <tr><td>Profile URL</td><td><a href="{g.get('profile_url','#')}" target="_blank">{g.get('profile_url','—')}</a></td></tr>
            </table>
        </div>"""

        breaches = extra_data.get("breaches", [])
        if breaches:
            breach_rows = ""
            for b in breaches:
                dc = ", ".join(b.get("DataClasses", [])[:5])
                breach_rows += f"""
                <tr>
                    <td><strong>{b.get('Name','?')}</strong></td>
                    <td>{b.get('BreachDate','?')}</td>
                    <td>{b.get('PwnCount', 0):,}</td>
                    <td>{dc}</td>
                </tr>"""
            extra_section += f"""
        <div class="info-card breach-card">
            <h3>⚠️ Breach Data ({len(breaches)} found)</h3>
            <table class="data-table">
                <thead><tr><th>Source</th><th>Date</th><th>Records</th><th>Data Types</th></tr></thead>
                <tbody>{breach_rows}</tbody>
            </table>
        </div>"""

    username_hints = ""
    if extra_data and extra_data.get("username_hints"):
        hints = extra_data["username_hints"]
        hints_html = " ".join(f'<span class="tag tag-hint">{h}</span>' for h in hints)
        username_hints = f"""
        <div class="info-card">
            <h3>💡 Username Hints</h3>
            <p>Possible usernames derived from email:</p>
            <div class="hints-container">{hints_html}</div>
        </div>"""

    # ── Feature 5: Profile Metadata & Correlation ─────────────────────────
    metadata_section = ""
    if extra_data and extra_data.get("metadata"):
        meta = extra_data["metadata"]
        profiles = meta.get("profiles", [])
        correlations = meta.get("correlations", [])

        if profiles:
            profile_cards = ""
            for p in profiles:
                bio_html     = f"<p class='meta-bio'>{p.get('bio','')[:200]}</p>" if p.get("bio") else ""
                avatar_html  = f"<img class='meta-avatar' src='{p['avatar_url']}' onerror=\"this.style.display='none'\">" if p.get("avatar_url") else ""
                fields = []
                for label, key in [("📍 Location","location"),("🌐 Website","website"),
                                    ("👥 Followers","followers"),("📝 Posts","posts"),
                                    ("📅 Joined","joined_date")]:
                    val = p.get(key,"")
                    if val: fields.append(f"<span class='meta-field'>{label}: <b>{val}</b></span>")
                extra_fields = ""
                for k,v in (p.get("extra",{}) or {}).items():
                    if v: extra_fields += f"<span class='meta-field'>🔹 {k}: <b>{v[:50]}</b></span>"
                profile_cards += f"""
                <div class="profile-card">
                    {avatar_html}
                    <div class="profile-info">
                        <div class="profile-platform">{p.get('platform','')}</div>
                        <div class="profile-name">{p.get('display_name','') or p.get('username','')}</div>
                        {bio_html}
                        <div class="profile-fields">{''.join(fields)}{extra_fields}</div>
                        <a href="{p.get('url','#')}" target="_blank" class="profile-link">View Profile →</a>
                    </div>
                </div>"""
            metadata_section += f"""
        <div class="section">
            <div class="section-header">
                <h2>🧠 Profile Metadata ({len(profiles)} scraped)</h2>
                <span class="count-badge">{len(profiles)}</span>
            </div>
            <div class="profile-grid">{profile_cards}</div>
        </div>"""

        if correlations:
            corr_rows = ""
            for c in correlations:
                lvl = c.get("level","")
                color = {"HIGH":"#3fb950","MEDIUM":"#d29922","LOW":"#8b949e"}.get(lvl,"#8b949e")
                evidence = "; ".join(c.get("evidence",[]))
                corr_rows += f"""
                <tr>
                    <td><strong>{c.get('platform_a','')}</strong></td>
                    <td><strong>{c.get('platform_b','')}</strong></td>
                    <td style="color:{color};font-weight:700">{lvl}</td>
                    <td>{int(c.get('score',0)*100)}%</td>
                    <td style="font-size:0.82rem;color:var(--text-dim)">{evidence}</td>
                </tr>"""
            metadata_section += f"""
        <div class="section">
            <div class="section-header">
                <h2>🔗 Cross-Platform Correlation</h2>
                <span class="count-badge">{len(correlations)}</span>
            </div>
            <table class="data-table">
                <thead><tr><th>Platform A</th><th>Platform B</th><th>Level</th><th>Score</th><th>Evidence</th></tr></thead>
                <tbody>{corr_rows}</tbody>
            </table>
        </div>"""

    # ── Feature 2: Dork Queries ────────────────────────────────────────────
    dork_section = ""
    if extra_data and extra_data.get("dorks"):
        dorks = extra_data["dorks"]
        dork_by_cat: dict = {}
        for d in dorks:
            q = d.get("query", {})
            cat = q.get("category","Other") if isinstance(q,dict) else "Other"
            dork_by_cat.setdefault(cat, []).append(d)

        dork_cats_html = ""
        for cat, items in dork_by_cat.items():
            rows_html = ""
            for d in items:
                q = d.get("query",{}) if isinstance(d.get("query"),dict) else {}
                google_url = q.get("google_url","#")
                desc       = q.get("description","")
                query_str  = q.get("query","")
                hits       = d.get("results",[])
                results_html = ""
                for r in hits[:3]:
                    results_html += f"""
                    <div class="dork-hit">
                        <a href="{r.get('url','#')}" target="_blank">{r.get('title','')[:70]}</a>
                        <p>{r.get('snippet','')[:100]}</p>
                    </div>"""
                rows_html += f"""
                <div class="dork-row">
                    <div class="dork-desc">{desc}</div>
                    <div class="dork-query"><code>{query_str[:100]}</code></div>
                    <div class="dork-actions">
                        <a href="{google_url}" target="_blank" class="dork-btn">Google</a>
                    </div>
                    {results_html}
                </div>"""
            dork_cats_html += f"""
            <div class="dork-category">
                <div class="dork-cat-title">{cat}</div>
                {rows_html}
            </div>"""

        dork_section = f"""
        <div class="section">
            <div class="section-header">
                <h2>🔎 Google Dork Queries</h2>
                <span class="count-badge">{len(dorks)}</span>
            </div>
            <div class="dork-container">{dork_cats_html}</div>
        </div>"""

    # ── Feature 6: Recursive Search ───────────────────────────────────────
    recursive_section = ""
    if extra_data and extra_data.get("recursive"):
        rec = extra_data["recursive"]
        discovered = rec.get("discovered_targets", [])
        history    = rec.get("scan_history", [])

        if discovered:
            target_pills = ""
            for t in discovered:
                conf_class = {"HIGH":"pill-high","MEDIUM":"pill-medium","LOW":"pill-low"}.get(t.get("confidence",""),"pill-low")
                type_icon  = "📧" if t.get("type")=="email" else "👤"
                target_pills += f'<span class="pill {conf_class}" title="{t.get("source","")}">{type_icon} {t.get("value","")}</span>'

            history_rows = ""
            for h in history:
                found_links = " ".join(
                    f'<a href="{p["url"]}" target="_blank" class="small-link">{p["platform"]}</a>'
                    for p in h.get("profiles",[])[:5]
                )
                history_rows += f"""
                <tr>
                    <td><strong>{h.get('target','')}</strong></td>
                    <td><span class="badge badge-info">Depth {h.get('depth',0)}</span></td>
                    <td>{h.get('source','')[:60]}</td>
                    <td>{h.get('found',0)}/{h.get('total',0)}</td>
                    <td>{found_links or '—'}</td>
                </tr>"""

            recursive_section = f"""
        <div class="section">
            <div class="section-header">
                <h2>🔄 Recursive Discovery ({len(discovered)} targets)</h2>
                <span class="count-badge">{rec.get('total_new_profiles',0)} new profiles</span>
            </div>
            <div style="padding:1rem 1.5rem">
                <p style="color:var(--text-dim);font-size:0.85rem;margin-bottom:1rem">
                    Discovered targets from bios, breach data, and email hints:
                </p>
                <div class="pill-container">{target_pills}</div>
            </div>
            {"<table class='data-table'><thead><tr><th>Target</th><th>Depth</th><th>Source</th><th>Found</th><th>Profiles</th></tr></thead><tbody>" + history_rows + "</tbody></table>" if history_rows else ""}
        </div>"""

    # ── Confidence summary (Feature 4) ────────────────────────────────────
    high_conf   = sum(1 for r in found if getattr(r,"confidence","") == "HIGH")
    medium_conf = sum(1 for r in found if getattr(r,"confidence","") == "MEDIUM")
    low_conf    = sum(1 for r in found if getattr(r,"confidence","") == "LOW")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_icon = "📧" if scan_type == "email" else "🔍"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSINT Report — {target}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg: #0d1117;
            --surface: #161b22;
            --surface2: #1c2128;
            --border: #30363d;
            --text: #e6edf3;
            --text-dim: #8b949e;
            --green: #3fb950;
            --red: #f85149;
            --yellow: #d29922;
            --blue: #58a6ff;
            --cyan: #39c5cf;
            --purple: #bc8cff;
            --found: #1a3a2a;
            --found-border: #3fb950;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            line-height: 1.6;
        }}

        /* ── Header ──────────────────────────── */
        .header {{
            background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
            border-bottom: 1px solid var(--border);
            padding: 2rem 2rem 1.5rem;
        }}
        .header-inner {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .tool-name {{
            font-size: 1.1rem;
            color: var(--cyan);
            font-family: 'Courier New', monospace;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}
        .report-title {{
            font-size: 2.2rem;
            font-weight: 700;
            margin: 0.4rem 0;
            color: var(--text);
        }}
        .report-meta {{
            color: var(--text-dim);
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }}
        .report-meta span {{ margin-right: 1.5rem; }}
        .target-badge {{
            display: inline-block;
            background: rgba(88,166,255,0.1);
            border: 1px solid var(--blue);
            color: var(--blue);
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
            font-family: monospace;
            font-size: 1rem;
            margin-left: 0.5rem;
        }}
        .warning-bar {{
            background: rgba(210,153,34,0.1);
            border: 1px solid var(--yellow);
            border-radius: 6px;
            padding: 0.6rem 1rem;
            font-size: 0.85rem;
            color: var(--yellow);
            margin-top: 1rem;
        }}

        /* ── Layout ──────────────────────────── */
        .main {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}

        /* ── Stats Cards ─────────────────────── */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.2rem;
            text-align: center;
            transition: transform 0.2s;
        }}
        .stat-card:hover {{ transform: translateY(-2px); }}
        .stat-card .number {{
            font-size: 2.8rem;
            font-weight: 700;
            font-family: 'Courier New', monospace;
            line-height: 1.1;
        }}
        .stat-card .label {{
            color: var(--text-dim);
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.3rem;
        }}
        .stat-found {{ border-color: var(--green); }}
        .stat-found .number {{ color: var(--green); }}
        .stat-total .number {{ color: var(--blue); }}
        .stat-error .number {{ color: var(--red); }}
        .stat-rate .number {{ color: var(--purple); }}

        /* ── Charts ──────────────────────────── */
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        @media (max-width: 768px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
        .chart-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
        }}
        .chart-card h3 {{
            color: var(--text-dim);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 1rem;
        }}
        .chart-container {{ height: 220px; position: relative; }}

        /* ── Info Cards ──────────────────────── */
        .info-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .info-card h3 {{ margin-bottom: 1rem; font-size: 1rem; }}
        .breach-card {{ border-color: var(--yellow); background: rgba(210,153,34,0.05); }}
        .info-table td {{ padding: 0.4rem 0.8rem; }}
        .info-table tr:first-child td {{ padding-top: 0; }}
        .info-table td:first-child {{ color: var(--text-dim); width: 130px; }}
        .hints-container {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }}

        /* ── Tables ──────────────────────────── */
        .section {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        .section-header {{
            padding: 1rem 1.5rem;
            background: var(--surface2);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .section-header h2 {{ font-size: 1rem; }}
        .count-badge {{
            background: rgba(88,166,255,0.15);
            color: var(--blue);
            border: 1px solid rgba(88,166,255,0.3);
            padding: 0.1rem 0.6rem;
            border-radius: 12px;
            font-size: 0.8rem;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        .data-table th {{
            padding: 0.75rem 1rem;
            text-align: left;
            background: var(--surface2);
            color: var(--text-dim);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 600;
        }}
        .data-table td {{ padding: 0.65rem 1rem; border-top: 1px solid var(--border); }}
        .data-table a {{ color: var(--blue); text-decoration: none; word-break: break-all; }}
        .data-table a:hover {{ text-decoration: underline; }}
        .found-row {{ background: rgba(63,185,80,0.04); }}
        .error-row {{ opacity: 0.6; }}

        /* ── Filter Bar ──────────────────────── */
        .filter-bar {{
            padding: 0.8rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            gap: 0.5rem;
            align-items: center;
            flex-wrap: wrap;
        }}
        .filter-input {{
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.85rem;
            outline: none;
            width: 220px;
        }}
        .filter-input:focus {{ border-color: var(--blue); }}
        .filter-btn {{
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.82rem;
            cursor: pointer;
        }}
        .filter-btn:hover, .filter-btn.active {{ border-color: var(--blue); color: var(--blue); }}

        /* ── Badges ──────────────────────────── */
        .badge {{
            display: inline-block;
            padding: 0.15rem 0.55rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .badge-found {{ background: rgba(63,185,80,0.15); color: var(--green); border: 1px solid rgba(63,185,80,0.3); }}
        .badge-notfound {{ background: rgba(139,148,158,0.1); color: var(--text-dim); }}
        .badge-error {{ background: rgba(248,81,73,0.1); color: var(--red); }}

        /* ── Tags ────────────────────────────── */
        .tag {{
            display: inline-block;
            background: rgba(88,166,255,0.1);
            color: var(--blue);
            border-radius: 4px;
            padding: 0.1rem 0.4rem;
            font-size: 0.72rem;
            margin: 1px;
        }}
        .tag-hint {{
            background: rgba(188,140,255,0.1);
            color: var(--purple);
        }}

        /* ── Footer ──────────────────────────── */
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-dim);
            font-size: 0.82rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }}
        .footer a {{ color: var(--blue); text-decoration: none; }}

        /* ── Scrollbar ───────────────────────── */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg); }}
        ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}

        /* ── Feature 4: Confidence Badges ───── */
        .conf-high   {{ color: var(--green); font-size: 0.72rem; font-weight:700; }}
        .conf-medium {{ color: var(--yellow); font-size: 0.72rem; font-weight:700; }}
        .conf-low    {{ color: var(--red); font-size: 0.72rem; font-weight:700; }}
        .badge-info  {{ background:rgba(88,166,255,0.15);color:var(--blue);border:1px solid rgba(88,166,255,0.3); }}

        /* ── Feature 5: Profile Cards ────────── */
        .profile-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1rem;
            padding: 1.5rem;
        }}
        .profile-card {{
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            display: flex;
            gap: 0.75rem;
            transition: border-color 0.2s;
        }}
        .profile-card:hover {{ border-color: var(--blue); }}
        .meta-avatar {{
            width: 48px; height: 48px;
            border-radius: 50%;
            object-fit: cover;
            flex-shrink: 0;
            border: 2px solid var(--border);
        }}
        .profile-info {{ flex: 1; min-width: 0; }}
        .profile-platform {{
            font-size: 0.72rem;
            color: var(--cyan);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 700;
        }}
        .profile-name {{
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--text);
            margin: 0.15rem 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .meta-bio {{
            font-size: 0.8rem;
            color: var(--text-dim);
            margin: 0.3rem 0;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .profile-fields {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
            margin-top: 0.4rem;
        }}
        .meta-field {{
            font-size: 0.72rem;
            color: var(--text-dim);
            background: var(--surface);
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
        }}
        .meta-field b {{ color: var(--text); }}
        .profile-link {{
            display: inline-block;
            margin-top: 0.5rem;
            font-size: 0.78rem;
            color: var(--blue);
            text-decoration: none;
        }}
        .profile-link:hover {{ text-decoration: underline; }}

        /* ── Feature 2: Dork Queries ─────────── */
        .dork-container {{ padding: 1rem 1.5rem; }}
        .dork-category {{ margin-bottom: 1.5rem; }}
        .dork-cat-title {{
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--cyan);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.5rem;
            padding-bottom: 0.3rem;
            border-bottom: 1px solid var(--border);
        }}
        .dork-row {{
            padding: 0.6rem 0;
            border-bottom: 1px solid rgba(48,54,61,0.5);
        }}
        .dork-desc  {{ font-size: 0.85rem; font-weight: 600; color: var(--text); }}
        .dork-query {{ font-size: 0.78rem; color: var(--text-dim); margin: 0.2rem 0; }}
        .dork-query code {{
            background: var(--surface2);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            color: var(--yellow);
        }}
        .dork-btn {{
            display: inline-block;
            background: rgba(88,166,255,0.1);
            border: 1px solid rgba(88,166,255,0.3);
            color: var(--blue);
            padding: 0.15rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            text-decoration: none;
            margin-right: 0.4rem;
        }}
        .dork-btn:hover {{ background: rgba(88,166,255,0.2); }}
        .dork-hit {{
            margin-top: 0.3rem;
            padding: 0.4rem 0.8rem;
            background: var(--surface2);
            border-left: 2px solid var(--green);
            border-radius: 0 4px 4px 0;
        }}
        .dork-hit a {{ color: var(--blue); font-size: 0.82rem; text-decoration: none; }}
        .dork-hit p {{ font-size: 0.75rem; color: var(--text-dim); margin-top: 0.1rem; }}

        /* ── Feature 6: Recursive Pills ──────── */
        .pill-container {{ display: flex; flex-wrap: wrap; gap: 0.4rem; }}
        .pill {{
            padding: 0.25rem 0.7rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: default;
        }}
        .pill-high   {{ background:rgba(63,185,80,0.15);color:var(--green);border:1px solid rgba(63,185,80,0.3); }}
        .pill-medium {{ background:rgba(210,153,34,0.15);color:var(--yellow);border:1px solid rgba(210,153,34,0.3); }}
        .pill-low    {{ background:rgba(139,148,158,0.1);color:var(--text-dim);border:1px solid var(--border); }}
        .small-link {{ font-size:0.78rem;color:var(--blue);margin-right:0.3rem; }}
    </style>
</head>
<body>

<!-- ── HEADER ─────────────────────────────────────────────── -->
<div class="header">
    <div class="header-inner">
        <div class="tool-name">🕵️ OSINT Sherlock Pro</div>
        <h1 class="report-title">
            {scan_icon} {scan_type.title()} Intelligence Report
            <span class="target-badge">{target}</span>
        </h1>
        <div class="report-meta">
            <span>📅 {timestamp}</span>
            <span>🌐 {len(results)} sites scanned</span>
            <span>✅ {len(found)} profiles found</span>
            <span>⏱ Generated by OSINT Sherlock Pro v2.0</span>
        </div>
        <div class="warning-bar">
            ⚠️ This report is for educational and authorized security research purposes only.
            Unauthorized use of OSINT tools may violate privacy laws. Always obtain proper authorization.
        </div>
    </div>
</div>

<!-- ── MAIN ───────────────────────────────────────────────── -->
<div class="main">

    <!-- Stats -->
    <div class="stats-grid">
        <div class="stat-card stat-total">
            <div class="number">{len(results)}</div>
            <div class="label">Sites Scanned</div>
        </div>
        <div class="stat-card stat-found">
            <div class="number">{len(found)}</div>
            <div class="label">Profiles Found</div>
        </div>
        <div class="stat-card">
            <div class="number" style="color:var(--text-dim)">{len(not_found)}</div>
            <div class="label">Not Found</div>
        </div>
        <div class="stat-card stat-error">
            <div class="number">{len(errors)}</div>
            <div class="label">Errors/Timeouts</div>
        </div>
        <div class="stat-card stat-rate">
            <div class="number">{round(len(found)/len(results)*100) if results else 0}%</div>
            <div class="label">Hit Rate</div>
        </div>
        <div class="stat-card" style="border-color:var(--green)">
            <div class="number conf-high">{high_conf}</div>
            <div class="label">High Confidence</div>
        </div>
        <div class="stat-card" style="border-color:var(--yellow)">
            <div class="number conf-medium">{medium_conf}</div>
            <div class="label">Med Confidence</div>
        </div>
    </div>

    <!-- Charts -->
    <div class="charts-grid">
        <div class="chart-card">
            <h3>📊 Scan Result Distribution</h3>
            <div class="chart-container">
                <canvas id="pieChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <h3>🏷 Found by Category</h3>
            <div class="chart-container">
                <canvas id="barChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Extra data (email/breach) -->
    {username_hints}
    {extra_section}

    <!-- Feature 5: Profile Metadata & Correlation -->
    {metadata_section}

    <!-- Feature 2: Dork Queries -->
    {dork_section}

    <!-- Feature 6: Recursive Discovery -->
    {recursive_section}

    <!-- Found Profiles -->
    <div class="section">
        <div class="section-header">
            <h2>✅ Found Profiles</h2>
            <span class="count-badge">{len(found)}</span>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Platform</th>
                    <th>Status</th>
                    <th>Profile URL</th>
                    <th>Tags</th>
                    <th>HTTP</th>
                </tr>
            </thead>
            <tbody>
                {found_rows if found_rows else '<tr><td colspan="5" style="text-align:center;color:var(--text-dim);padding:2rem">No profiles found.</td></tr>'}
            </tbody>
        </table>
    </div>

    <!-- All Results -->
    <div class="section">
        <div class="section-header">
            <h2>📋 All Results</h2>
            <span class="count-badge">{len(results)}</span>
        </div>
        <div class="filter-bar">
            <input class="filter-input" id="searchFilter" placeholder="🔍  Filter platforms..." oninput="filterTable()">
            <button class="filter-btn active" onclick="filterStatus('all', this)">All</button>
            <button class="filter-btn" onclick="filterStatus('found', this)">Found</button>
            <button class="filter-btn" onclick="filterStatus('notfound', this)">Not Found</button>
            <button class="filter-btn" onclick="filterStatus('error', this)">Errors</button>
        </div>
        <table class="data-table" id="allTable">
            <thead>
                <tr>
                    <th>Platform</th>
                    <th>Status</th>
                    <th>URL</th>
                    <th>Tags</th>
                    <th>HTTP</th>
                </tr>
            </thead>
            <tbody id="allTableBody">
                {all_rows}
            </tbody>
        </table>
    </div>

</div>

<!-- ── FOOTER ─────────────────────────────────────────────── -->
<footer class="footer">
    <p>Generated by <strong>OSINT Sherlock Pro v2.0</strong> | {timestamp}</p>
    <p style="margin-top:0.3rem">For ethical and authorized use only. Respect privacy laws.</p>
</footer>

<script>
// ── Charts ────────────────────────────────────────────────
const pieCtx = document.getElementById('pieChart').getContext('2d');
new Chart(pieCtx, {{
    type: 'doughnut',
    data: {{
        labels: ['Found', 'Not Found', 'Error'],
        datasets: [{{
            data: [{len(found)}, {len(not_found)}, {len(errors)}],
            backgroundColor: ['rgba(63,185,80,0.8)', 'rgba(139,148,158,0.4)', 'rgba(248,81,73,0.7)'],
            borderColor: ['#3fb950', '#8b949e', '#f85149'],
            borderWidth: 1,
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
            legend: {{ labels: {{ color: '#8b949e', font: {{ size: 12 }} }} }}
        }}
    }}
}});

const barCtx = document.getElementById('barChart').getContext('2d');
new Chart(barCtx, {{
    type: 'bar',
    data: {{
        labels: {chart_labels},
        datasets: [{{
            label: 'Profiles Found',
            data: {chart_values},
            backgroundColor: 'rgba(88,166,255,0.6)',
            borderColor: '#58a6ff',
            borderWidth: 1,
            borderRadius: 4,
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ ticks: {{ color: '#8b949e', maxRotation: 45 }}, grid: {{ color: '#21262d' }} }},
            y: {{ ticks: {{ color: '#8b949e', stepSize: 1 }}, grid: {{ color: '#21262d' }}, beginAtZero: true }}
        }}
    }}
}});

// ── Table Filter ──────────────────────────────────────────
let currentStatus = 'all';

function filterTable() {{
    const query = document.getElementById('searchFilter').value.toLowerCase();
    const rows = document.querySelectorAll('#allTableBody tr');
    rows.forEach(row => {{
        const text = row.textContent.toLowerCase();
        const matchText = text.includes(query);
        const matchStatus =
            currentStatus === 'all' ||
            (currentStatus === 'found' && row.classList.contains('found-row')) ||
            (currentStatus === 'notfound' && row.classList.contains('notfound-row')) ||
            (currentStatus === 'error' && row.classList.contains('error-row'));
        row.style.display = (matchText && matchStatus) ? '' : 'none';
    }});
}}

function filterStatus(status, btn) {{
    currentStatus = status;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filterTable();
}}
</script>
</body>
</html>"""

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{scan_type}_{target}_{timestamp_str}.html"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    return filename
