from flask import Flask, render_template, request
import sqlite3

import scrape_logger
import scraper
import normalizer
import worth_it_score
from market_analysis import MarketAnalyzer

app = Flask(__name__)

districts = {
    f"budapest{str(i).zfill(2)}": f"Budapest {roman} kerület"
    for i, roman in zip(range(1, 24), [
        "I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.", "IX.",
        "X.", "XI.", "XII.", "XIII.", "XIV.", "XV.", "XVI.", "XVII.", "XVIII.",
        "XIX.", "XX.", "XXI.", "XXII.", "XXIII."
    ])
}

def query_db(filters):
    con = sqlite3.connect("real_estate_listings.db")
    con.row_factory = sqlite3.Row  # So we can use column names
    cur = con.cursor()

    query = "SELECT * FROM listings WHERE 1=1"
    params = []

    # Filter logic
    if filters.get("type"):
        query += " AND Jelleg = ?"
        if filters["type"] == "haz":
            params.append("ház")
        elif filters["type"] == "lakas":
            params.append("lakás")
        else:
            params.append(filters["type"])

    if filters.get("location"):
        query += " AND location LIKE ?"
        params.append(f"%{districts[filters['location']]}%")

    if filters.get("min_price"):
        try:
            query += " AND price_huf_clean >= ?"
            params.append(float(filters["min_price"]))
        except (ValueError, TypeError):
            pass

    if filters.get("max_price"):
        try:
            query += " AND price_huf_clean <= ?"
            params.append(float(filters["max_price"]))
        except (ValueError, TypeError):
            pass

    if filters.get("min_size"):
        try:
            query += " AND Méret_clean >= ?"
            params.append(float(filters["min_size"]))
        except (ValueError, TypeError):
            pass

    if filters.get("max_size"):
        try:
            query += " AND Méret_clean <= ?"
            params.append(float(filters["max_size"]))
        except (ValueError, TypeError):
            pass

    if filters.get("min_rooms"):
        try:
            query += " AND rooms_clean >= ?"
            params.append(float(filters["min_rooms"]))
        except (ValueError, TypeError):
            pass

    if filters.get("max_rooms"):
        try:
            query += " AND rooms_clean <= ?"
            params.append(float(filters["max_rooms"]))
        except (ValueError, TypeError):
            pass

    # Sorting logic
    sort = filters.get("sort")
    if sort == "price_asc":
        query += " ORDER BY price_huf_clean ASC"
    elif sort == "price_desc":
        query += " ORDER BY price_huf_clean DESC"
    elif sort == "size_asc":
        query += " ORDER BY Méret_clean ASC"
    elif sort == "size_desc":
        query += " ORDER BY Méret_clean DESC"
    elif sort == "worth_it_asc":
        query += ' ORDER BY "Ár-Érték Index" ASC'
    elif sort == "worth_it_desc":
        query += ' ORDER BY "Ár-Érték Index" DESC'
    elif sort == "value_assessment_asc":
        query += ' ORDER BY "Érték Minősítés" ASC'
    elif sort == "value_assessment_desc":
        query += ' ORDER BY "Érték Minősítés" DESC'
    elif sort == "price_diff_asc":
        query += ' ORDER BY "Ár/m² Eltérés %" ASC'
    elif sort == "price_diff_desc":
        query += ' ORDER BY "Ár/m² Eltérés %" DESC'

    rows = cur.execute(query, params).fetchall()
    con.close()
    return rows


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/start_search", methods=["POST"])
def start_search():
    filters = {
        "type": request.form.get("type"),
        "location": request.form.get("location"),
        "min_price": request.form.get("min_price"),
        "max_price": request.form.get("max_price"),
        "min_size": request.form.get("min_size"),
        "max_size": request.form.get("max_size"),
        "min_rooms": request.form.get("min_rooms"),
        "max_rooms": request.form.get("max_rooms"),
        "sort": request.form.get("sort")
    }

    # Store filters in a session or pass via query string
    query = "&".join([f"{k}={v}" for k, v in filters.items() if v])
    return render_template("loading.html", query=query)

@app.route("/results")
def results():
    filters = {
        "type": request.args.get("type"),
        "location": request.args.get("location"),
        "min_price": request.args.get("min_price"),
        "max_price": request.args.get("max_price"),
        "min_size": request.args.get("min_size"),
        "max_size": request.args.get("max_size"),
        "min_rooms": request.args.get("min_rooms"),
        "max_rooms": request.args.get("max_rooms"),
        "sort": request.args.get("sort")
    }

    # Only scrape if this came from start_search, not from sorting
    came_from_search = request.args.get("from_search") == "true"
    
    if came_from_search:
        # Map frontend filters to backend parameter names for caching logic
        backend_filters = {
            "jelleg": filters.get("type"),
            "ar_min": filters.get("min_price"),
            "ar_max": filters.get("max_price"),
            "elhelyezkedes": filters.get("location"),
            "meret_min": filters.get("min_size"),
            "meret_max": filters.get("max_size"),
            "szoba_min": filters.get("min_rooms"),
            "szoba_max": filters.get("max_rooms")
        }
        
        # Check if we need to scrape or can use existing data
        should_scrape_new, compatible_filters = scrape_logger.should_scrape(filters=backend_filters)
        
        if should_scrape_new:
            print("[SCRAPING] New data required, starting scrape...")
            
            # Use intelligent interval detection for size parameters
            analyzer = MarketAnalyzer()
            original_min_size = filters.get("min_size")
            original_max_size = filters.get("max_size")
            
            if original_min_size or original_max_size:
                expanded_min, expanded_max = analyzer.get_required_intervals_for_search(
                    original_min_size, original_max_size
                )
                print(f"[INTERVALS] Original size range: {original_min_size}-{original_max_size}")
                print(f"[INTERVALS] Expanded to cover market intervals: {expanded_min}-{expanded_max}")
                
                # Use expanded range for scraping to get complete market data
                scraper.main(filters["type"], filters["min_price"], filters["max_price"], 
                           filters["location"], expanded_min, expanded_max, 
                           filters["min_rooms"], filters["max_rooms"])
            else:
                # No size filters, scrape as normal
                scraper.main(filters["type"], filters["min_price"], filters["max_price"], 
                           filters["location"], filters["min_size"], filters["max_size"], 
                           filters["min_rooms"], filters["max_rooms"])
            
            normalizer.main()
            worth_it_score.main()
        else:
            print(f"[CACHE] Using existing data from compatible search: {compatible_filters}")

    filters = {k: v for k, v in filters.items() if v}
    ads = query_db(filters)
    return render_template("results.html", ads=ads)

if __name__ == "__main__":
    app.run(debug=True)