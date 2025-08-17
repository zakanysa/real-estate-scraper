# Magyar Ingatlan Scraper és Piaci Elemző

Átfogó web scraping és piaci elemzés eszköz magyar ingatlan hirdetésekhez az oc.hu-ról. Ez a projekt fejlett web scraping technikákat kombinál kifinomult piaci elemzési algoritmusokkal, hogy olyan betekintést nyújtson, amely összehasonlítható a professzionális ingatlan platformokkal, mint az ingatlan.com.

## English Description

A comprehensive web scraping and market analysis tool for Hungarian real estate listings from oc.hu. This project combines advanced web scraping techniques with sophisticated market analysis algorithms to provide insights comparable to professional real estate platforms like ingatlan.com.

## 🚀 Funkciók

### Fejlett Web Scraping
- **Intelligens scraping** az oc.hu ingatlan hirdetésekből
- **Projekt oldal kezelés** új építésű fejlesztésekhez
- **Egyidejű feldolgozás** ThreadPoolExecutor-ral az optimális teljesítményért
- **Okos gyorsítótár rendszer** TTL-lel a szerver terhelés csökkentéséért
- **Session újrafelhasználás és kapcsolat pooling** a hatékonyságért
- **Robusztus hibakezelés** és újrapróbálkozási mechanizmusok

### Piaci Elemzési Motor
- **Méret intervallum alapú szegmentálás** pontos piaci összehasonlításokhoz
- **Statisztikai elemzés** átlag, medián és szórás számításokkal
- **Összehasonlító árképzési betekintések** amelyek mutatják a pozíciót a piaci átlaghoz képest
- **Továbbfejlesztett pontozási algoritmus** figyelembe véve az ingatlan típusát, állapotát és piaci bizalmat
- **Valós idejű piaci betekintések** hasonlóan a professzionális platformokhoz

### Webalkalmazás
- **Flask alapú webes felület** reszponzív Bootstrap dizájnnal
- **Fejlett szűrés** helyszín, ár, méret és szobaszám szerint
- **Dinamikus rendezés** ár, méret vagy piaci érték metrikák szerint
- **Valós idejű piaci adatok megjelenítése** színkódolt érték értékelésekkel
- **Intelligens keresési gyorsítótárazás** a szükségtelen újrascraping elkerülésére

### Teljesítmény Optimalizálások
- **Kötegelt adatbázis műveletek** a jobb áteresztőképességért
- **Szelektív részlet lekérés** szűrési kritériumok alapján
- **Okos részleges frissítések** csak a megváltozott hirdetések feldolgozására
- **Válasz gyorsítótárazás** automatikus lejárattal
- **Előszűrési logika** a irreleváns hirdetések korai kihagyására

## 🛠️ Technológiai Stack

- **Backend**: Python, Flask, SQLite
- **Scraping**: requests, BeautifulSoup4
- **Párhuzamosság**: ThreadPoolExecutor
- **Frontend**: HTML5, Bootstrap 5, Jinja2
- **Adatelemzés**: Egyedi statisztikai algoritmusok
- **Adatbázis**: SQLite optimalizált sémával

## 📊 Piaci Elemzési Funkciók

### Méret Intervallumok
Az ingatlanok piaci szegmensekbe vannak csoportosítva méret szerint a pontos összehasonlításokhoz:
- 0-30 m², 31-50 m², 51-70 m², 71-90 m², 91-120 m²
- 121-150 m², 151-200 m², 201-300 m², 301-500 m², 501+ m²

### Érték Értékelési Kategóriák
- **Kiváló ár-érték arány** - 15%+ piaci átlag alatt
- **Jó ár-érték arány** - 5-15% piaci átlag alatt  
- **Piaci átlag** - ±5%-on belül a piaci átlaghoz képest
- **Piaci átlag felett** - 5-15% piaci átlag felett
- **Drága** - 15%+ piaci átlag felett

### Továbbfejlesztett Pontozási Algoritmus
Az ár-érték pontszám (0-100) figyelembe veszi:
- **Piaci összehasonlítás** (0-50 pont) - Pozíció az összehasonlítható ingatlanokhoz képest
- **Szoba hatékonyság** (0-25 pont) - Különböző kritériumok házak vs lakások esetén
- **Piaci bizalom** (0-15 pont) - Az összehasonlítható ingatlanok mintanagyságán alapuló
- **Állapot bónusz** (0-10 pont) - Ingatlan állapot minősége
- **Méret prémium** (0-3 pont) - Bónusz luxus méretű ingatlanokhoz

## 🏗️ Installation

1. **Clone the repository**
```bash
git clone [repository-url]
cd oc_scraper
```

2. **Install dependencies**
```bash
pip install flask beautifulsoup4 requests
```

3. **Run the application**
```bash
python app.py
```

4. **Access the web interface**
Open your browser to `http://localhost:5000`

## 📖 Usage

### Web Interface
1. **Select search criteria** - property type, location, price range, size, rooms
2. **Click "Keresés"** to start scraping and analysis
3. **View results** with market insights and sorting options
4. **Use "Rendezés"** to sort by different criteria without re-scraping

### Command Line Usage
```python
import scraper
import normalizer
import worth_it_score

# Scrape apartments in Budapest District V, 100-130 m²
scraper.main(jelleg='lakas', elhelyezkedes='budapest05', meret_min=100, meret_max=130)

# Normalize and analyze data
normalizer.main()
worth_it_score.main()
```

## 🏛️ Architecture

### Data Pipeline
1. **Extraction** - Concurrent scraping with smart filtering
2. **Transformation** - Data normalization and cleaning
3. **Analysis** - Market statistics and scoring
4. **Presentation** - Web interface with real-time insights

### Database Schema
- **listings** table with 70+ fields for comprehensive property data
- **search_log** table for intelligent caching
- **Normalized fields** for reliable numerical operations

### Performance Features
- **Smart update detection** - Only processes changed listings
- **Selective filtering** - Pre-filters listings before expensive detail fetching
- **Batch operations** - Single-transaction database updates
- **Connection pooling** - Optimized HTTP connections per thread

## 📈 Market Insights

The system provides insights comparable to professional platforms:

- **Price per m² analysis** compared to market segment averages
- **Market position indicators** showing competitive pricing
- **Sample size confidence** for statistical reliability
- **Property-specific scoring** adapted for houses vs apartments
- **Condition and location premiums** in scoring calculations

## 🔄 Scraping Strategy

### Project Page Handling
- **Detects new construction projects** (`/uj-lakas/` URLs)
- **Treats project pages as single listings** matching oc.hu's approach
- **Handles size ranges** like "71,6-142,1 m²" correctly

### Respectful Scraping
- **Rate limiting** with configurable delays
- **Session reuse** to minimize connection overhead
- **Caching** to avoid repeated requests
- **robots.txt compliance** verified

## ⚖️ Legal Compliance

This tool respects oc.hu's robots.txt file and implements responsible scraping practices:
- Rate limiting and respectful request patterns
- Caching to minimize server load
- No circumvention of access controls
- Educational and personal use intended

## 🚀 Performance Metrics

Optimizations achieved approximately **10-50x performance improvement**:
- **Batch database operations** - Single transaction for multiple records
- **Concurrent processing** - 8 parallel workers for detail fetching
- **Smart caching** - 2-hour TTL for responses
- **Selective filtering** - Process only relevant listings
- **Connection pooling** - Reuse HTTP connections efficiently

## 💼 Skills Demonstrated

- **Advanced Web Scraping** - Complex site navigation and data extraction
- **Performance Engineering** - Systematic optimization and concurrent processing
- **Statistical Analysis** - Market segmentation and comparative algorithms
- **Full-Stack Development** - Complete web application with database
- **Data Pipeline Design** - ETL process with normalization and analysis
- **Problem Solving** - Handling edge cases and data inconsistencies

## 📝 Note on Usage

This project is designed for educational and personal use. When using web scraping tools, always:
- Respect robots.txt and website terms of service
- Implement rate limiting and respectful request patterns
- Consider the impact on target servers
- Use scraped data responsibly and ethically

---

*This project demonstrates advanced Python development skills, web scraping expertise, data analysis capabilities, and full-stack web development proficiency.*