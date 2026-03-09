# 🕵️ OSINT Sherlock Pro v4.0

> **Username & Full Name Intelligence Scanner**  
> 104 Sites | Async Engine | Smart FP Filter | Google Dorking | Profile Correlation | Recursive Discovery

---

## 📋 Daftar Isi

- [Quick Start](#-quick-start)
- [Usage Flow](#-usage-flow)
- [Commands](#-commands)
- [Semua Flag & Opsi](#-semua-flag--opsi)
- [Fitur Unggulan](#-fitur-unggulan)
- [HTML Dashboard](#-html-dashboard)
- [API Keys](#-api-keys-opsional)
- [Available Tags](#-available-tags)
- [Project Structure](#-project-structure)
- [Legal & Ethics](#-legal--ethics)
- [Roadmap](#-roadmap)

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Scan username (HTML report otomatis terbuat)
python main.py username Budi Santoso

# 3. Scan nama lengkap (auto-generate username variants)
python main.py username "Budi Santoso"

# 4. Scan + metadata + recursive discovery
python main.py username "Budi Santoso" --meta --recursive --dork

# 5. Scan email
python main.py email budisantoso@gmail.com

# 6. Google Dorking
python main.py search "Budi Santoso" --dork
python main.py search "Budi Santoso" --dork-live

# 7. Breach check
python main.py breach budisantoso@gmail.com --hibp-key YOUR_KEY

# 8. Preview username variants
python main.py variants "Budi Santoso"
```

> **💡 Catatan:** HTML report **selalu otomatis dibuat** setiap scan selesai di folder `reports/`  
> Tidak perlu flag `--html`. Gunakan `--no-report` untuk menonaktifkan.

---

## 🔄 Usage Flow

Workflow yang disarankan untuk investigasi menyeluruh:

```
1. IDENTIFY
   └─ Input nama lengkap atau email target
      python main.py username "Budi Santoso"
      python main.py email budi@gmail.com

2. ANALYZE
   └─ Lihat HTML dashboard — pola penyebaran akun (Gaming vs Professional vs Social)
      Cek chart "Found by Category" untuk memahami online persona target

3. CORRELATE
   └─ Gunakan --meta untuk scrape bio, lokasi, followers dari profil yang ditemukan
      python main.py username "Budi Santoso" --meta
      → Cross-platform correlation mendeteksi apakah akun GitHub = akun Twitter

4. DORK
   └─ Generate Google dork queries untuk menemukan jejak di luar platform
      python main.py search "Budi Santoso" --dork
      → Temukan CV, dokumen, email exposure, berita, forum

5. INVESTIGATE
   └─ Cek breach database untuk password yang bocor (untuk audit keamanan)
      python main.py breach budi@gmail.com --hibp-key KEY

6. RECURSE
   └─ Biarkan tool auto-discover username/email baru dari bio profil
      python main.py username "Budi Santoso" --recursive
      → Temukan akun tersembunyi dari link di bio GitHub/Twitter
```

---

## 🛠 Commands

| Command | Deskripsi |
|---|---|
| `username <target>` | Scan username atau **nama lengkap** di 104+ situs |
| `email <email>` | Email OSINT — Gravatar, breach check, username hints |
| `search <target>` | **Google Dorking** — generate/jalankan dork queries |
| `breach <email>` | Cek breach database (HIBP, LeakCheck, DeHashed) |
| `variants <name>` | Preview username variants yang akan discan |
| `list-sites` | Tampilkan semua situs dalam database |
| `list-tags` | Tampilkan semua tag yang tersedia |

---

## ⚙️ Semua Flag & Opsi

### Scan Options (`username`)

| Flag | Default | Deskripsi |
|---|---|---|
| `--workers N` | `50` | Jumlah concurrent async workers |
| `--timeout SEC` | `10` | HTTP request timeout per situs |
| `--sites SITE...` | semua | Batasi ke situs tertentu saja |
| `--tags TAG...` | semua | Filter berdasarkan kategori tag |
| `--verbose / -v` | off | Tampilkan juga hasil NOT_FOUND |
| `--delay SEC` | `0` | Jeda antar request per thread |
| `--meta` | off | **Scrape metadata** profil (bio, lokasi, followers) |
| `--recursive` | off | **Auto-discover** target baru dari bio profil |
| `--dork` | off | **Generate Google dork queries** sekaligus |

### Output Options

| Flag | Deskripsi |
|---|---|
| `--json` | Juga generate JSON report |
| `--csv` | Juga generate CSV report |
| `--no-report` | Skip semua report generation |
| `--output-dir DIR` | Direktori output (default: `reports/`) |

### Network Options

| Flag | Deskripsi |
|---|---|
| `--proxy URL` | HTTP/SOCKS proxy (e.g. `http://127.0.0.1:8080`) |
| `--tor` | Route melalui Tor (butuh Tor running di port 9050) |

### Dork Options (`search`)

| Flag | Deskripsi |
|---|---|
| `--dork-live` | Jalankan live search via DuckDuckGo (rate-limited) |
| `--dork-cats CAT...` | Filter kategori dork: `Social Media` `Developer` `Documents` dll |

### Breach Options (`breach`)

| Flag | Deskripsi |
|---|---|
| `--hibp-key KEY` | Have I Been Pwned API key |
| `--leakcheck-key KEY` | LeakCheck.io API key |
| `--dehashed-user USER` | DeHashed username |
| `--dehashed-key KEY` | DeHashed API key |

---

## 🚀 Fitur Unggulan

### 1️⃣ Name-to-Username Generator

Input nama asli → otomatis generate **20+ username variant** realistis.  
Variant diurutkan berdasarkan probabilitas — yang paling mungkin dipakai muncul duluan.

```bash
python main.py variants "Budi Santoso"
# Output:
#  1. budis           7. b.santoso
#  2. budisan         8. budsantoso
#  3. bsantoso        9. budisantoso
#  4. budisant       10. budi.san
#  5. budisanto      11. budi_san
#  6. budi_s         ...
```

Pattern yang dihasilkan:
- `budisantoso` — joined tanpa separator
- `budi.santoso` / `budi_santoso` / `budi-santoso` — semua separator
- `bsantoso` / `b.santoso` — inisial + nama belakang
- `budis` / `budisant` — truncated versions
- `santoso.budi` — reversed order
- `budisantoso99` / `budisantoso.official` — dengan suffix

### 2️⃣ Google Dorking Otomatis

Generate **28 dork query** dalam 7 kategori sekaligus:

| Kategori | Contoh Query |
|---|---|
| Social Media | `site:linkedin.com/in "Budi Santoso"` |
| Developer | `site:github.com "Budi Santoso"` |
| Documents | `"Budi Santoso" filetype:pdf` |
| Contact | `"Budi Santoso" "@gmail.com"` |
| Mentions | `"Budi Santoso" site:reddit.com` |
| Indonesia | `"Budi Santoso" site:kaskus.co.id` |
| Security | `site:pastebin.com "Budi Santoso"` |

```bash
# Generate query saja (buka di browser manual)
python main.py search "Budi Santoso" --dork

# Live search via DuckDuckGo (tanpa API key)
python main.py search "Budi Santoso" --dork-live

# Filter kategori tertentu
python main.py search "Budi Santoso" --dork-live --dork-cats "Documents" "Security"
```

### 3️⃣ Async Engine + Progress Bar

Engine berbasis `asyncio` dengan Semaphore — jauh lebih efisien dari threading biasa.  
Progress bar real-time di terminal:

```
  ████████████████░░░░░░░░░░░░░░   62/104  ✓8  60% | 34 req/s | ETA 2s
```

Arsitektur identik dengan `aiohttp` — siap di-upgrade kapanpun.

### 4️⃣ Smart False-Positive Filter

Multi-layer detection untuk **mengurangi false positive** yang umum terjadi di OSINT tools:

```
Layer 1: HTTP 404/4xx → NOT_FOUND (pasti)
Layer 2: Site-specific error message di body HTML
Layer 3: Universal FP keyword scan (EN + ID):
         "user not found", "pengguna tidak ditemukan", "akun tidak ditemukan", ...
Layer 4: Content-length baseline — jika ukuran halaman = ukuran halaman 404 kustom
Layer 5: Confidence scoring → HIGH / MEDIUM / LOW
```

Dashboard menampilkan kolom **Confidence** per hasil:
- 🟢 `HIGH` — status code + body content match
- 🟡 `MEDIUM` — hanya status code 200 (situs mungkin selalu return 200)
- 🔴 `LOW` — halaman sangat kecil atau deteksi ambigu

### 5️⃣ Profile Metadata & Correlation

Scrape data publik dari profil yang ditemukan **tanpa API key**:

| Platform | Data yang Diambil |
|---|---|
| GitHub | Bio, lokasi, website, followers, public repos, bahasa, Twitter |
| Reddit | Bio, karma (link + comment + total), mod status |
| HackerNews | Bio, karma, submission count |
| Dev.to | Bio, lokasi, website, followers, Twitter/GitHub link |
| Semua lain | Open Graph tags (og:title, og:description, og:image) |

**Cross-platform correlation** membandingkan:
- Display name (sama persis atau substring)
- Bio keywords (kata kunci yang sama)
- Lokasi (kota/negara yang sama)
- Website/URL (link yang sama)

```
[HIGH] GitHub ↔ Dev.to  score: 85%
  • Same website: 'budisantoso.dev'
  • Same location: 'Jakarta, Indonesia'

[LOW]  GitHub ↔ Instagram  score: 32%
  • Same display name: 'Budi Santoso'
```

### 6️⃣ Recursive Search

Otomatis temukan target baru dari hasil scan:

```
Input email: budi@gmail.com
  ↓
Extract username hints dari local-part email
  ↓
Scan username → Temukan GitHub profile
  ↓
Scrape bio: "Follow me on Twitter @budisantoso99"
  ↓
Extract target baru: username=budisantoso99 [HIGH confidence]
  ↓
Auto-scan budisantoso99 (depth 1)
  ↓
Temukan TikTok, Snapchat, dll
```

Dilengkapi depth limit dan deduplication untuk mencegah infinite loop.

---

## 📊 HTML Dashboard

Report otomatis terbuat di `reports/<scan_type>_<target>_<timestamp>.html`  
Langsung dibuka di browser setelah scan selesai.

**Sections dalam dashboard:**

| Section | Deskripsi |
|---|---|
| 📈 Stats Cards | Total scanned, Found, Errors, Hit Rate, High/Med Confidence |
| 🍩 Doughnut Chart | Found vs Not Found vs Error distribution |
| 📊 Bar Chart | Found profiles by category (social, coding, gaming, dll) |
| 🧠 Profile Metadata | Card per platform dengan bio, lokasi, avatar, followers |
| 🔗 Cross-Platform Correlation | Tabel similarity antar platform dengan evidence |
| 🔎 Dork Queries | Semua dork query dengan tombol langsung ke Google |
| 🔄 Recursive Discovery | Target baru yang ditemukan beserta confidence level |
| ✅ Found Profiles | Tabel lengkap semua profil yang ditemukan |
| 📋 All Results | Tabel semua situs + filter real-time by status/keyword |

---

## 🔑 API Keys (Opsional)

Tool tetap berfungsi penuh tanpa API key. Key hanya diperlukan untuk fitur breach detection.

| Service | Flag | Cara Dapat |
|---|---|---|
| Have I Been Pwned | `--hibp-key` | https://haveibeenpwned.com/API/Key (~$3.50/bulan) |
| LeakCheck.io | `--leakcheck-key` | https://leakcheck.io (ada free tier) |
| DeHashed | `--dehashed-user` + `--dehashed-key` | https://dehashed.com |

---

## 🏷 Available Tags

Filter scan ke kategori tertentu dengan `--tags`:

| Tag | Platform Contoh | Jumlah |
|---|---|---|
| `social` | Instagram, Twitter, TikTok, VK, Mastodon | 20+ |
| `coding` | GitHub, GitLab, CodePen, Replit, NPM, PyPI | 15+ |
| `gaming` | Steam, Twitch, Roblox, Xbox, PlayStation | 8+ |
| `music` | Spotify, SoundCloud, Bandcamp, LastFM | 5+ |
| `security` | HackTheBox, TryHackMe, HackerOne, BugCrowd | 4 |
| `design` | Behance, Dribbble, DeviantArt, ArtStation | 5+ |
| `professional` | LinkedIn, Xing, AngelList, Crunchbase | 4 |
| `blog` | Medium, Substack, Hashnode, WordPress | 5+ |
| `web3` | OpenSea, Mirror.xyz, Etherscan | 3 |
| `education` | Kaggle, Coursera, Duolingo, Academia | 4 |
| `photo` | Flickr, 500px, Unsplash, Imgur | 4 |

```bash
# Contoh: scan hanya platform gaming
python main.py username johndoe --tags gaming

# Scan platform coding + security saja
python main.py username johndoe --tags coding security
```

---

## 📁 Project Structure

```
osint-sherlock-pro/
│
├── main.py                          # CLI entry point (argparse)
├── requirements.txt
│
├── src/
│   ├── core/
│   │   ├── async_engine.py          # ⭐ Async scan engine + Smart FP Filter
│   │   └── engine.py                # Legacy ThreadPool engine (backward compat)
│   │
│   ├── modules/
│   │   ├── name_generator.py        # ⭐ Name-to-Username permutation generator
│   │   ├── username_search.py       # Username / full name scan orchestrator
│   │   ├── email_search.py          # Email OSINT (Gravatar, hints, HIBP)
│   │   ├── breach_checker.py        # Multi-source breach detection
│   │   ├── dorking.py               # ⭐ Google Dork generator + DDG scraper
│   │   ├── profile_scraper.py       # ⭐ Profile metadata + correlation engine
│   │   └── recursive_search.py      # ⭐ Recursive target discovery engine
│   │
│   ├── database/
│   │   └── sites.json               # 104 site definitions (url, errorType, tags)
│   │
│   ├── report/
│   │   ├── html_report.py           # Full HTML dashboard generator
│   │   └── json_report.py           # JSON + CSV report generators
│   │
│   └── utils/
│       ├── logger.py                # Colored ANSI CLI output
│       └── request_handler.py       # HTTP engine (proxy, Tor, UA rotation)
│
└── reports/                         # Auto-generated reports (gitignored)
```

---

## ⚠️ Legal & Ethics

Tool ini dibuat **untuk keperluan edukasi dan riset keamanan yang sah**.

**✅ Penggunaan yang diizinkan:**
- OSINT pada diri sendiri (self-audit)
- Authorized penetration testing
- Digital forensics dengan izin resmi
- Riset keamanan akademis
- Verifikasi identitas digital dalam konteks legal

**❌ Penggunaan yang DILARANG:**
- Stalking atau penguntitan
- Harassment atau intimidasi
- Profiling tanpa izin
- Doxxing
- Segala aktivitas yang melanggar hukum privasi

Selalu patuhi regulasi yang berlaku: **UU ITE (Indonesia)**, GDPR (Eropa), CCPA (AS).

---

## 🗺 Roadmap

### ✅ Selesai

- [x] Phase 1 — Core username scanner (20 sites)
- [x] Phase 2 — ThreadPool engine (30 workers)
- [x] Phase 3 — 104 sites database + tag system
- [x] Phase 4 — Email OSINT + Gravatar + breach detection
- [x] Phase 5 — HTML dashboard + JSON/CSV reports (auto-generated)
- [x] Phase 6 — Proxy + Tor support + User-Agent rotation
- [x] Phase 7 — **Async engine** (asyncio + real-time progress bar)
- [x] Phase 8 — **Name-to-Username Generator** (20+ variants, ranked)
- [x] Phase 9 — **Google Dorking** (28 queries, 7 kategori, DDG live search)
- [x] Phase 10 — **Smart False-Positive Filter** (4-layer + confidence scoring)
- [x] Phase 11 — **Profile Metadata Scraper** (GitHub/Reddit/HN/DevTo)
- [x] Phase 12 — **Cross-Platform Correlation Engine**
- [x] Phase 13 — **Recursive Search Engine** (depth-limited auto-discovery)

### 🔜 Planned

- [ ] Phase 14 — aiohttp upgrade (1000+ sites in <2s)
- [ ] Phase 15 — Web UI (Flask/FastAPI + React)
- [ ] Phase 16 — Docker image + docker-compose
- [ ] Phase 17 — Phone number OSINT module
- [ ] Phase 18 — Image reverse search integration
- [ ] Phase 19 — Telegram/WhatsApp number lookup
- [ ] Phase 20 — Scheduled monitoring (cron-based alerts)

---

## 📝 Changelog

### v4.0 (Latest)
- ✨ Name-to-Username Generator dengan 20+ variant permutasi
- ✨ Google Dorking module — 28 queries, 7 kategori, live DDG search
- ✨ Async engine dengan asyncio semaphore + real-time progress bar
- ✨ Smart False-Positive Filter — 4 layer detection + confidence scoring
- ✨ Profile Metadata Scraper — GitHub API, Reddit JSON, HN, Dev.to
- ✨ Cross-Platform Correlation Engine
- ✨ Recursive Search Engine — auto-discover dari bio & breach data
- 🆕 Command: `search` (dorking), `variants` (preview)
- 🆕 Flag: `--meta`, `--recursive`, `--dork`, `--dork-live`

### v3.0
- ✨ Full Name support dengan spasi (auto-sanitize untuk filename)
- 🐛 Fix: URL invalid ketika nama mengandung spasi

### v2.0
- ✨ HTML auto-generated setiap scan (tidak perlu `--html`)
- ✨ Auto-open browser setelah scan
- 🆕 Flag `--no-report`
