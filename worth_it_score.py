import sqlite3
from market_analysis import MarketAnalyzer

def calculate_score(price, size, rooms):
    """Legacy simple calculation - kept as fallback"""
    try:
        return round((rooms * 1000) / (price / size), 2)
    except (ZeroDivisionError, TypeError):
        return None

def main():
    conn = sqlite3.connect("real_estate_listings.db")
    cur = conn.cursor()

    # Add new columns if they don't exist
    new_columns = [
        "'Ár-Érték Index' REAL",
        "'Piaci Insight' TEXT", 
        "'Ár/m² Eltérés %' REAL",
        "'Érték Minősítés' TEXT"
    ]
    
    for column_def in new_columns:
        try:
            cur.execute(f"ALTER TABLE listings ADD COLUMN {column_def}")
        except sqlite3.OperationalError:
            # Column already exists
            pass

    # Initialize market analyzer
    analyzer = MarketAnalyzer()
    
    # Fetch all records with required fields
    cur.execute("""
        SELECT url, lokáció, Jelleg, Állapot, Méret_clean, price_huf_clean, rooms_clean 
        FROM listings
    """)
    rows = cur.fetchall()

    print(f"[ANALYSIS] Processing {len(rows)} properties for market analysis...")
    
    # Update each with enhanced analysis
    for i, row in enumerate(rows):
        url, lokacio, jelleg, allapot, size, price, rooms = row
        
        if i % 50 == 0:  # Progress indicator
            print(f"[ANALYSIS] Processed {i}/{len(rows)} properties...")
        
        # Calculate enhanced worth it score using market analysis
        enhanced_score = analyzer.calculate_enhanced_worth_it_score(
            lokacio, jelleg, allapot, size, price, rooms
        )
        
        # Get market insight for additional data
        market_insight = analyzer.get_property_market_insight(
            lokacio, jelleg, allapot, size, price
        )
        
        # Prepare update values
        update_values = {'score': enhanced_score}
        
        if market_insight:
            update_values.update({
                'insight': f"Piaci átlag: {market_insight['market_avg_price_per_sqm']:,.0f} Ft/m² ({market_insight['market_sample_count']} ingatlan alapján)",
                'price_diff_pct': market_insight['price_diff_pct'],
                'value_assessment': market_insight['value_assessment']
            })
        else:
            # Fallback for properties without market data
            simple_score = calculate_score(price, size, rooms)
            update_values.update({
                'score': simple_score,
                'insight': "Nincs elegendő piaci adat az összehasonlításhoz",
                'price_diff_pct': None,
                'value_assessment': "Ismeretlen"
            })
        
        # Update database
        cur.execute("""
            UPDATE listings SET 
                'Ár-Érték Index' = ?,
                'Piaci Insight' = ?,
                'Ár/m² Eltérés %' = ?,
                'Érték Minősítés' = ?
            WHERE url = ?
        """, (
            update_values['score'],
            update_values['insight'], 
            update_values['price_diff_pct'],
            update_values['value_assessment'],
            url
        ))

    print(f"[ANALYSIS] Completed market analysis for all properties")
    conn.commit()
    conn.close()

