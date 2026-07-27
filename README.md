# ⚡ Employmentmaxxing — Telemetry AI Job Command Center

A free, self-hosted AI job tracker for CS students targeting **US AI/ML, SWE, and Quantum internships, co-ops, and entry-level positions**.

Employmentmaxxing directly scrapes official company career portals (Greenhouse & Lever APIs), top Y Combinator & VC portfolio startups, community tracking repos, and job boards multiple times daily. It sanitizes HTML formatting, verifies direct apply URLs via active HTTP checks, purges Senior/Lead roles, and provides an honest 7-factor resume match score calibrated to your exact background.

---

## ✨ Features

- ⚡ **Direct Official Company ATS Scraper**: Scrapes 100+ top tech companies (Stripe, OpenAI, Anthropic, Databricks, Figma, Vercel, Scale AI, Coinbase, Roblox, Cloudflare, etc.).
- 🚀 **Top 130 AI & Tech Startup Scraper**: Queries Y Combinator (YC), a16z, Sequoia, and Benchmark portfolio startups.
- 🔗 **Active Link Verification Layer**: Performs async HTTP checks on `apply_url` links to automatically detect and deactivate 404/expired postings.
- 🇺🇸 **Strict US Location Enforcement**: Filters out international listings (London, Berlin, Barcelona, Tokyo, etc.) so only US & US-Remote jobs are indexed.
- 🚫 **Senior & Lead Role Exclusion**: Purges "Senior", "Lead", "Principal", "Director", "Manager", "Staff" roles to focus strictly on Internships, Co-ops, and Entry-Level / New Grad positions.
- 📅 **Released Date & Scraped Timestamp**: Shows exact posting release dates so you can apply early.
- 🎨 **Sci-Fi Cyber-Telemetry Command HUD UI**: Inspired by futuristic space telemetry interfaces with pure jet black `#010101`, electric purple `#8b4bbe`, and neon green `#83f558` accents.
- 📊 **Multi-Select Checkboxes & Company Tiers**: Multi-select categories (`AI/ML`, `SWE`, `Quantum`, `Data Science`), experience levels (`Internship`, `Co-op`, `New Grad`), and company tiers (`Top 10`, `Top 20`, `Top 50`, `Startups Only`).
- 📌 **Kanban Application Board**: Track applications across 6 stages (`Interested` → `Applied` → `Screening` → `Interview` → `Offer` → `Rejected`).

---

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.11+), SQLite (WAL mode), APScheduler, httpx, BeautifulSoup4, rapidfuzz.
- **AI / Matching Engine**: Gemini Flash API + Deterministic 7-Factor Resume Match Engine.
- **Frontend**: Vanilla HTML5, CSS3 Cyber-HUD Theme, JavaScript ES Modules, Chart.js.

---

## 🚀 Quick Start

### 1. Installation

```bash
cd /home/kesh/Documents/Projects/employmentmaxxing/backend

# Create virtual environment and install dependencies
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in `backend/`:

```env
GEMINI_API_KEY=your_google_ai_studio_key_here
SCRAPE_INTERVAL_HOURS=4
DEBUG=true
```

### 3. Run Server

```bash
./venv/bin/python main.py
```

Open your browser to:
👉 **`http://localhost:8000`**

---

## 📁 Project Structure

```
employmentmaxxing/
├── backend/
│   ├── main.py                    # FastAPI application & server entrypoint
│   ├── config.py                  # Settings & environment variables
│   ├── database.py                # SQLite schema, queries & US location filter
│   ├── scheduler.py               # APScheduler background automation
│   ├── clean_html.py              # HTML tag sanitizer & Senior role purger
│   ├── scrapers/
│   │   ├── company_ats_scraper.py # Greenhouse & Lever official company API scraper
│   │   ├── startup_scraper.py     # YC & VC portfolio startup scraper
│   │   ├── link_verifier.py       # Active HTTP link verification layer
│   │   ├── jobspy_scraper.py      # LinkedIn / Indeed / Glassdoor / Google Jobs
│   │   ├── github_scraper.py      # Community tracking repo scraper
│   │   ├── quantum_scraper.py     # Quantum-specific job board scraper
│   │   └── deduplicator.py        # Cross-source fuzzy deduplication
│   ├── analysis/
│   │   ├── jd_parser.py           # Structured JD data extractor
│   │   ├── chance_scorer.py       # 7-factor resume match scorer
│   │   └── skill_taxonomy.py      # 200+ canonical skill mappings
│   └── routes/
│       ├── jobs.py                # Jobs listing API with company tiers & sorting
│       ├── profile.py             # User profile & CV matrix CRUD
│       ├── applications.py        # Application tracker Kanban CRUD
│       └── analytics.py           # Statistics & scrape triggers
├── frontend/
│   ├── index.html                 # Main Cyber-HUD Single Page Application
│   ├── css/
│   │   └── style.css              # Cyber-Telemetry theme (#010101, #8b4bbe, #83f558)
│   └── js/
│       ├── app.js                 # SPA router & state manager
│       └── components/            # Modular UI components
└── README.md
```

---

## 📜 License

MIT License — Built for personal, self-hosted job tracking.
