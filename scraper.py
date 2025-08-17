import requests
from bs4 import BeautifulSoup
import time
import sqlite3
import link_generator
import scrape_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from datetime import datetime, timedelta

BASE_URL = "https://www.oc.hu"
LIST_URL = f"{BASE_URL}/ingatlanok/lista/jelleg:lakas;ertekesites:elado;elhelyezkedes:budapest08"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Thread-local storage for sessions
thread_local = threading.local()

# Global cache for responses (thread-safe with simple dict + lock)
response_cache = {}
cache_lock = threading.Lock()
CACHE_DURATION_HOURS = 2

def get_session():
    """Get or create a thread-local session with optimized settings"""
    if not hasattr(thread_local, 'session'):
        thread_local.session = requests.Session()
        thread_local.session.headers.update(HEADERS)
        # Connection pooling settings
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,   # Fewer per thread since we have multiple threads
            pool_maxsize=10,      # Maximum connections in pool per thread
            max_retries=3         # Retry failed requests
        )
        thread_local.session.mount('http://', adapter)
        thread_local.session.mount('https://', adapter)
    return thread_local.session

def get_cached_response(url):
    """Get cached response if available and not expired"""
    with cache_lock:
        if url in response_cache:
            cached_data, timestamp = response_cache[url]
            if datetime.now() - timestamp < timedelta(hours=CACHE_DURATION_HOURS):
                return cached_data
            else:
                # Remove expired cache entry
                del response_cache[url]
    return None

def cache_response(url, response_text):
    """Cache response with timestamp"""
    with cache_lock:
        response_cache[url] = (response_text, datetime.now())

def clear_expired_cache():
    """Remove expired entries from cache"""
    cutoff_time = datetime.now() - timedelta(hours=CACHE_DURATION_HOURS)
    with cache_lock:
        expired_urls = [url for url, (_, timestamp) in response_cache.items() 
                       if timestamp < cutoff_time]
        for url in expired_urls:
            del response_cache[url]
        if expired_urls:
            print(f"[CACHE] Cleaned up {len(expired_urls)} expired entries")

def listing_needs_update(listing_data, existing_listings):
    """Check if a listing needs to be updated based on basic data changes"""
    url = listing_data.get("url")
    if url not in existing_listings:
        return True  # New listing
    
    # Check if basic data has changed
    existing_price, existing_size = existing_listings[url]
    current_price = listing_data.get("price_huf", "")
    current_size = listing_data.get("size", "")
    
    # Compare basic fields for changes
    if existing_price != current_price or existing_size != current_size:
        return True  # Data changed
    
    return False  # No update needed

def should_process_listing(listing_data, filters):
    """Pre-filter listings based on basic criteria before expensive detail fetching"""
    try:
        # Always process project pages - they contain multiple apartments
        if '/uj-lakas/' in listing_data.get("url", ""):
            return True
        
        # Extract basic price and size info for quick filtering
        price_str = listing_data.get("price_huf", "")
        size_str = listing_data.get("size", "")
        
        # Basic price filtering (parse M suffix or raw numbers)
        if filters.get("ar_min") or filters.get("ar_max"):
            try:
                if "M" in price_str:
                    price_num = float(price_str.replace("M", "").replace(" ", "").replace(",", ".")) * 1000000
                else:
                    # Try to extract number from string
                    import re
                    price_match = re.search(r'[\d,.\s]+', price_str.replace(" ", ""))
                    if price_match:
                        price_num = float(price_match.group().replace(",", ".").replace(" ", ""))
                    else:
                        price_num = None
                
                if price_num:
                    if filters.get("ar_min") and price_num < float(filters["ar_min"]) * 1000000:
                        return False
                    if filters.get("ar_max") and price_num > float(filters["ar_max"]) * 1000000:
                        return False
            except (ValueError, TypeError):
                pass  # Skip filtering if can't parse price
        
        # Basic size filtering
        if filters.get("meret_min") or filters.get("meret_max"):
            try:
                import re
                size_match = re.search(r'(\d+)', size_str)
                if size_match:
                    size_num = float(size_match.group())
                    if filters.get("meret_min") and size_num < float(filters["meret_min"]):
                        return False
                    if filters.get("meret_max") and size_num > float(filters["meret_max"]):
                        return False
            except (ValueError, TypeError):
                pass  # Skip filtering if can't parse size
        
        return True  # Process if passes basic filters or can't determine
    except Exception:
        return True  # Process if any error in pre-filtering

def process_listing_details(listing_data, delay=0.1):
    """Process a single listing's details - designed for concurrent execution"""
    try:
        session = get_session()
        
        # Add small delay to be respectful
        time.sleep(delay)
        
        # Merge in detailed fields
        details = get_listing_details(listing_data["url"], session)
        
        # Standard single listing processing
        if not details.get('Jelleg'):
            if listing_data["jelleg"] == "lakas":
                details['Jelleg'] = "lakás"
            elif listing_data["jelleg"] == "haz":
                details['Jelleg'] = "ház"
            else:
                details['Jelleg'] = "telek"
        
        # Remove temporary jelleg field
        listing_data.pop("jelleg", None)
        listing_data.update(details)

        # Normalize to all keys (missing ones will be None)
        normalized = {key: listing_data.get(key, None) for key in keys}
        return normalized
        
    except Exception as e:
        print(f"Error processing listing {listing_data.get('url', 'unknown')}: {e}")
        return None

# Keys from the full database schema
keys = [
    'url', 'location','size', 'rooms', 'price_huf', 'price_eur', 'description',
    'Értékesités', 'Jogi státusz', 'Jelleg', 'Építési mód', 'Méret', 'Bruttó méret',
    'Fűtés', 'Belmagasság', 'Tájolás', 'Panoráma', 'Lépcsőház típusa', 'Állapot',
    'Homlokzat állapota', 'Építés éve', 'Fürdőszobák száma', 'Lift', 'szoba', 'konyha',
    'közlekedő', 'Lépcsőház állapota', 'Környék', 'Fekvés', 'Víz', 'Villany', 'Csatorna',
    'nappali', 'konyha-étkező', 'fürdőszoba', 'előszoba', 'Közös költség', 'Garázs',
    'hálószoba', 'fürdőszoba-wc', 'Terasz / erkély mérete', 'Pince', 'Gáz', 'wc', 'kamra',
    'erkély', 'Lakáson belüli szintszám', 'Tároló', 'ebédlő', 'Társaház kert', 'terasz',
    'galéria','lokáció','Ár-Érték Index'
]

def create_table(conn):
    columns = ", ".join([f'"{key}" TEXT' for key in keys])
    conn.execute(f"CREATE TABLE IF NOT EXISTS listings ({columns});")
    conn.commit()

def insert_listing(conn, listing_data):
    values = [listing_data.get(key, None) for key in keys]
    placeholders = ','.join(['?'] * len(keys))
    columns_escaped = ", ".join([f'"{k}"' for k in keys])
    conn.execute(f"INSERT INTO listings ({columns_escaped}) VALUES ({placeholders})", values)
    # Note: Commit removed - will be done in batch

def batch_upsert_listings(conn, all_listings):
    """Insert or update multiple listings in a single transaction"""
    if not all_listings:
        return
    
    placeholders = ','.join(['?'] * len(keys))
    columns_escaped = ", ".join([f'"{k}"' for k in keys])
    update_clauses = ", ".join([f'"{k}" = excluded."{k}"' for k in keys if k != 'url'])
    
    all_values = []
    for listing_data in all_listings:
        values = [listing_data.get(key, None) for key in keys]
        all_values.append(values)
    
    # Use INSERT OR REPLACE for SQLite upsert functionality
    conn.executemany(f"""
        INSERT OR REPLACE INTO listings ({columns_escaped}) 
        VALUES ({placeholders})
    """, all_values)
    conn.commit()
    print(f"[BATCH] Upserted {len(all_listings)} listings in single transaction")

def get_individual_apartments_from_project(project_url, session=None):
    """Extract individual apartment URLs from a new construction project page"""
    try:
        if session is None:
            session = get_session()
        
        response = session.get(project_url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find links to individual apartments
        apartment_links = soup.find_all('a', href=True)
        individual_urls = []
        
        for link in apartment_links:
            href = link.get('href')
            if href and '/ingatlanok/' in href and any(char.isdigit() for char in href):
                full_url = f"{BASE_URL}{href}" if href.startswith('/') else href
                individual_urls.append(full_url)
        
        # Remove duplicates
        individual_urls = list(set(individual_urls))
        print(f"[PROJECT] Found {len(individual_urls)} individual apartments in project {project_url}")
        return individual_urls
        
    except Exception as e:
        print(f"Failed to extract apartments from project {project_url}: {e}")
        return []

def get_listing_details(url, session=None):
    try:
        # For project pages, treat them as single listings with summary data
        if '/uj-lakas/' in url:
            print(f"[PROJECT] Treating project page as single listing: {url}")
            # Return minimal data that will pass through as a single listing
            return {
                "Jelleg": "lakás",
                "lokáció": "Budapest V. kerület",  # We know this from the search filter
                "_is_project_page": True
            }
        
        # Standard individual listing processing
        # Check cache first
        cached_response = get_cached_response(url)
        if cached_response:
            response_text = cached_response
        else:
            # Fetch from server
            if session is None:
                session = get_session()
            res = session.get(url)
            response_text = res.text
            # Cache the response
            cache_response(url, response_text)
        
        # Parse the response (cached or fresh)
        detail_soup = BeautifulSoup(response_text, "html.parser")
        data_labels = detail_soup.select("div.row.row-cols-2 .data-label")
        data_values = detail_soup.select("div.row.row-cols-2 .data-value")
        details = {label.text.strip(): value.text.strip() for label, value in zip(data_labels, data_values)}
        lokacio_elem = detail_soup.select_one(".head-address")
        details["lokáció"] = lokacio_elem.get_text(strip=True) if lokacio_elem else None
        return details
    except Exception as e:
        print(f"Failed to get details from {url}: {e}")
        return {}

def main(jelleg="lakas",
    ar_min=None,
    ar_max=None,
    elhelyezkedes=None,
    meret_min=None,
    meret_max=None,
    szoba_min=None,
    szoba_max=None):
    conn = sqlite3.connect("real_estate_listings.db")
    create_table(conn)
    
    # Smart update: Check existing listings instead of clearing everything
    cursor = conn.cursor()
    cursor.execute("SELECT url, price_huf, size FROM listings")
    existing_listings = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    
    print(f"[SMART UPDATE] Found {len(existing_listings)} existing listings in database")
    
    # Get optimized session for all requests
    session = get_session()
    
    # Clean up expired cache entries
    clear_expired_cache()
    
    res1 = session.get(
        link_generator.generate_oc_link(jelleg, "elado", ar_min, ar_max, elhelyezkedes, meret_min, meret_max, szoba_min,
                                        szoba_max) + f"?page=1")
    soup1 = BeautifulSoup(res1.text, "html.parser")
    number_of_pages = int(int(((soup1.select_one(".py-2").get_text()).strip().split())[0])/12)+1
    
    # Collect all listings before processing for batch operations
    all_listings_to_process = []
    
    # First pass: Collect all basic listing info
    for i in range(1,number_of_pages+1):
        print(f"[COLLECT] Scraping page {i}/{number_of_pages}")
        res = session.get(link_generator.generate_oc_link(jelleg,"elado",ar_min, ar_max, elhelyezkedes,meret_min, meret_max, szoba_min,szoba_max) + f"?page={i}")
        soup = BeautifulSoup(res.text, "html.parser")

        for listing in soup.select("a[data-action='seo#selectItem']"):
            try:
                url_suffix = listing.get("href")
                full_url = f"{BASE_URL}{url_suffix}"

                location = listing.select_one(".info-row:nth-of-type(2) .text-left")
                size = listing.select_one(".info-row:nth-of-type(2) .text-end")
                rooms = listing.select_one(".info-row:nth-of-type(3) .text-end")
                price_huf = listing.select_one(".price-huf")
                price_eur = listing.select_one(".price-eur")
                description = listing.select_one(".description p")

                listing_data = {
                    "url": full_url,
                    "location": location.text.strip() if location else None,
                    "size": size.text.strip() if size else None,
                    "rooms": rooms.text.strip() if rooms else None,
                    "price_huf": price_huf.text.strip() if price_huf else None,
                    "price_eur": price_eur.text.strip() if price_eur else None,
                    "description": description.text.strip() if description else None,
                    "jelleg": jelleg  # Store for later detail fetching
                }
                
                all_listings_to_process.append(listing_data)
                
            except Exception as e:
                print("Skipping listing due to error:", e)
    
    print(f"[COLLECT] Collected {len(all_listings_to_process)} listings for processing")
    
    # Apply smart update filtering and selective filtering
    filters_dict = {
        "ar_min": ar_min,
        "ar_max": ar_max, 
        "meret_min": meret_min,
        "meret_max": meret_max
    }
    
    # First: Filter for updates needed
    update_needed_listings = []
    unchanged_count = 0
    for listing_data in all_listings_to_process:
        if listing_needs_update(listing_data, existing_listings):
            update_needed_listings.append(listing_data)
        else:
            unchanged_count += 1
    
    if unchanged_count > 0:
        print(f"[SMART UPDATE] Skipping {unchanged_count} unchanged listings")
    
    # Second: Apply selective filtering
    filtered_listings = []
    for listing_data in update_needed_listings:
        if should_process_listing(listing_data, filters_dict):
            filtered_listings.append(listing_data)
    
    filter_skipped = len(update_needed_listings) - len(filtered_listings)
    if filter_skipped > 0:
        print(f"[SELECTIVE] Pre-filtered out {filter_skipped} listings that don't match criteria")
        
    total_skipped = len(all_listings_to_process) - len(filtered_listings)
    print(f"[OPTIMIZATION] Processing {len(filtered_listings)}/{len(all_listings_to_process)} listings ({total_skipped} skipped)")
    
    # Second pass: Process details concurrently
    processed_listings = []
    max_workers = 8  # Concurrent threads - adjust based on server tolerance
    
    print(f"[CONCURRENT] Processing details with {max_workers} concurrent workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_listing = {
            executor.submit(process_listing_details, listing_data.copy()): i 
            for i, listing_data in enumerate(filtered_listings)
        }
        
        completed = 0
        for future in as_completed(future_to_listing):
            listing_index = future_to_listing[future]
            try:
                result = future.result()
                if result:
                    processed_listings.append(result)
                completed += 1
                
                if completed % 10 == 0:
                    print(f"[CONCURRENT] Completed {completed}/{len(filtered_listings)} listings")
                    
            except Exception as e:
                print(f"Error in concurrent processing for listing {listing_index}: {e}")
    
    print(f"[CONCURRENT] Completed processing {len(processed_listings)} listings successfully")
    
    # Batch upsert all processed listings
    if processed_listings:
        batch_upsert_listings(conn, processed_listings)
    scrape_logger.log_scrape(filters = {"jelleg": jelleg, "ar_min": ar_min,"ar_max": ar_max,"elhelyezkedes": elhelyezkedes,"meret_min": meret_min,"meret_max": meret_max,"szoba_min": szoba_min, "szoba_max": szoba_max})
    conn.close()

