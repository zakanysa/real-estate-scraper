# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Hungarian real estate scraper and search application that collects property listings from oc.hu (a major Hungarian real estate website). The system provides a Flask web interface for searching properties with filters and implements intelligent caching to avoid unnecessary re-scraping.

## Quick Start Commands

**Start the application:**
```bash
cd C:\pytprg\oc_scraper
python app.py
```
The application will run on http://127.0.0.1:5000

**Install dependencies (if needed):**
```bash
pip install flask beautifulsoup4 requests
```

**Test all functionality:**
```bash
python -c "import scraper, normalizer, worth_it_score, scrape_logger, app; print('All imports working')"
```

## Architecture Overview

### Core Data Flow
1. **Search Request** → Flask app (`app.py`) → **Intelligent Cache Check** → Scrape decision
2. **Fresh Scrape** → `scraper.py` → `normalizer.py` → `worth_it_score.py` → Database
3. **Results** → Database query with filters → Template rendering

### Key Components

**`app.py`** - Main Flask application with three critical routes:
- `/` - Search form (GET)
- `/start_search` - Processes form and redirects to loading (POST) 
- `/results` - Handles both new searches and sorting (GET)

**`scraper.py`** - Web scraping engine:
- Clears `real_estate_listings.db` on each fresh scrape
- Scrapes property listing pages and detail pages from oc.hu
- Stores 45+ property attributes per listing
- Logs each scrape operation via `scrape_logger`

**`scrape_logger.py`** - Intelligent caching system:
- `should_scrape()` - Determines if new scrape needed or use cache
- `is_subset_search()` - Detects if current search is subset of recent search
- Searches within 24 hours are candidates for cache reuse
- Cache logic: subset if all current filters are equal or more restrictive than existing

**`normalizer.py`** - Data cleaning pipeline:
- Converts Hungarian number formats (comma decimal separators)
- Handles "M" suffix prices (e.g., "25M" → 25,000,000)
- Creates `*_clean` columns for numeric filtering

**`worth_it_score.py`** - Value calculation:
- Formula: `(rooms * 1000) / (price / size)`
- Adds "Ár-Érték Index" column for value-based sorting

**`link_generator.py`** - oc.hu URL builder:
- Constructs search URLs with proper filter syntax
- Handles Hungarian property types: "lakas", "haz", "telek"

### Database Schema

**`real_estate_listings.db`:**
- `listings` table with 45+ columns (Hungarian property attributes)
- Key cleaned columns: `price_huf_clean`, `Méret_clean`, `rooms_clean`, `Ár-Érték Index`
- Completely replaced on each fresh scrape

**`search_log.db`:**
- `search_log` table: `id`, `filters` (JSON), `searched_at` (ISO timestamp)
- Used for intelligent cache decisions

### Frontend Structure

**Templates:**
- `index.html` - Search form with Budapest district dropdown
- `loading.html` - Auto-redirects to results with `from_search=true` parameter
- `results.html` - Sortable table with hidden form fields to preserve filters

**Important:** The sorting form includes all original search parameters as hidden fields to enable sorting without re-scraping.

## Key Behavioral Notes

### Cache Intelligence
- **Subset Detection:** Search for "20-40M HUF" will use cache from "10-50M HUF" search
- **Location Matching:** Must be exact match (budapest08 ≠ budapest09)
- **Temporal Limit:** Only searches within 24 hours are considered
- **Cache Miss Triggers:** Broader price ranges, different locations, different property types

### Hungarian Localization
- Property types: "lakas" (apartment), "haz" (house), "telek" (plot)
- Budapest districts: budapest01-budapest23 mapped to Roman numerals
- Price parsing handles Hungarian comma decimal format

### Development Notes
- Flask runs in debug mode by default
- All database operations use SQLite with absolute paths
- Web scraping includes 0.5s delay between requests
- Room counts display as integers (not floats) in results table

## Critical Dependencies
- Flask, BeautifulSoup4, requests (installed via pip)
- SQLite (built-in with Python)
- Target website: https://www.oc.hu (Hungarian real estate site)