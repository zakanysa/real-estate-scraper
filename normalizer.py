import sqlite3
import re


def to_number(value):
    if not value:
        return None

    # Remove all non-digit characters except comma and dot
    value = re.sub(r"[^\d,\.]", "", str(value))

    # Handle comma as decimal separator (Hungarian/European style)
    if value.count(",") == 1 and value.count(".") == 0:
        value = value.replace(",", ".")

    # Remove any thousands separators (either space, dot, or comma used wrongly)
    value = value.replace(" ", "").replace("\xa0", "").replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None
def parse_price(price_str):
    if not price_str:
        return None

    # Remove non-breaking spaces, regular spaces, currency symbols
    cleaned = (
        str(price_str)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace("Ft", "")
        .replace("HUF", "")
        .replace("€", "")
    )

    # Match M-suffix prices like '1.5M', '275M'
    match = re.match(r"([\d.,]+)M", cleaned)
    if match:
        number = match.group(1).replace(",", ".")
        try:
            return float(number) * 1_000_000
        except ValueError:
            return None

    # Otherwise, assume it's a raw number like 199000000 or '264,9'
    try:
        return float(cleaned.replace(",", "."))
    except ValueError:
        return None

def main():
    conn = sqlite3.connect("real_estate_listings.db")
    cursor = conn.cursor()

    # Add new columns if not already there
    cursor.execute("PRAGMA table_info(listings)")
    columns = [row[1] for row in cursor.fetchall()]

    for col_name in [
        "Méret_clean",
        "Bruttó méret_clean",
        "rooms_clean",
        "price_huf_clean",
        "price_eur_clean",
        "Belmagasság_clean"
    ]:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE listings ADD COLUMN '{col_name}' REAL")

    # Select all rows with original columns
    cursor.execute("""
        SELECT url, size, `Bruttó méret`, rooms, price_huf, price_eur, Belmagasság
        FROM listings
    """)
    rows = cursor.fetchall()

    # Normalize and update
    for row in rows:
        url, raw_size, raw_gross_size, raw_rooms, raw_price_huf, raw_price_eur, raw_height = row

        size_val = to_number(raw_size)
        gross_size_val = to_number(raw_gross_size)
        room_val = int(to_number(raw_rooms)) if to_number(raw_rooms) is not None else None
        price_huf_val = parse_price(raw_price_huf)
        price_eur_val = to_number(raw_price_eur.replace("€", "") if raw_price_eur else None)
        height_val = to_number(raw_height)

        cursor.execute("""
            UPDATE listings
            SET Méret_clean = ?,
                `Bruttó méret_clean` = ?,
                rooms_clean = ?,
                price_huf_clean = ?,
                price_eur_clean = ?,
                Belmagasság_clean = ?
            WHERE url = ?
        """, (
            size_val,
            gross_size_val,
            room_val,
            price_huf_val,
            price_eur_val,
            height_val,
            url
        ))

    conn.commit()
    conn.close()
