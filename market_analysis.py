import sqlite3
import json
from datetime import datetime
import statistics

class MarketAnalyzer:
    """
    Market analysis system for Hungarian real estate data.
    Provides market insights similar to ingatlan.com.
    """
    
    # Standard size intervals for market analysis (m²)
    SIZE_INTERVALS = [
        (0, 30),
        (31, 50),
        (51, 70),
        (71, 90), 
        (91, 120),
        (121, 150),
        (151, 200),
        (201, 300),
        (301, 500),
        (501, float('inf'))
    ]
    
    def __init__(self, db_path="real_estate_listings.db"):
        self.db_path = db_path
    
    def get_size_interval(self, size):
        """Get the size interval that contains the given size."""
        if not size:
            return None
        
        for min_size, max_size in self.SIZE_INTERVALS:
            if min_size <= size <= max_size:
                return (min_size, max_size)
        return None
    
    def get_required_intervals_for_search(self, min_size, max_size):
        """
        Determine which size intervals are needed to cover the search range.
        Returns the expanded range that should be scraped.
        """
        if not min_size and not max_size:
            return None, None
            
        min_size = float(min_size) if min_size else 0
        max_size = float(max_size) if max_size else float('inf')
        
        required_intervals = []
        for interval_min, interval_max in self.SIZE_INTERVALS:
            # Check if this interval overlaps with the search range
            if not (interval_max < min_size or interval_min > max_size):
                required_intervals.append((interval_min, interval_max))
        
        if not required_intervals:
            return min_size, max_size
            
        # Return the expanded range covering all required intervals
        expanded_min = min(interval[0] for interval in required_intervals)
        expanded_max = max(interval[1] for interval in required_intervals)
        
        # Handle infinity case
        if expanded_max == float('inf'):
            expanded_max = None
            
        return expanded_min, expanded_max
    
    def calculate_market_stats(self):
        """
        Calculate market statistics for all location/type/condition/size combinations.
        Returns a dictionary with market data.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all properties with complete data
        cursor.execute("""
            SELECT lokáció, Jelleg, Állapot, Méret_clean, price_huf_clean 
            FROM listings 
            WHERE lokáció IS NOT NULL 
                AND Jelleg IS NOT NULL 
                AND Állapot IS NOT NULL 
                AND Méret_clean IS NOT NULL 
                AND price_huf_clean IS NOT NULL
                AND Méret_clean > 0
                AND price_huf_clean > 0
        """)
        
        properties = cursor.fetchall()
        conn.close()
        
        # Group properties by market segments
        market_segments = {}
        
        for lokacio, jelleg, allapot, meret, price in properties:
            # Calculate price per m²
            price_per_sqm = price / meret
            
            # Get size interval
            size_interval = self.get_size_interval(meret)
            if not size_interval:
                continue
            
            # Create market segment key
            segment_key = (lokacio, jelleg, allapot, size_interval)
            
            if segment_key not in market_segments:
                market_segments[segment_key] = []
            
            market_segments[segment_key].append({
                'meret': meret,
                'price': price,
                'price_per_sqm': price_per_sqm
            })
        
        # Calculate statistics for each segment
        market_stats = {}
        for segment_key, properties in market_segments.items():
            if len(properties) < 2:  # Need at least 2 properties for meaningful stats
                continue
                
            prices_per_sqm = [p['price_per_sqm'] for p in properties]
            
            market_stats[segment_key] = {
                'count': len(properties),
                'avg_price_per_sqm': statistics.mean(prices_per_sqm),
                'median_price_per_sqm': statistics.median(prices_per_sqm),
                'min_price_per_sqm': min(prices_per_sqm),
                'max_price_per_sqm': max(prices_per_sqm),
                'std_price_per_sqm': statistics.stdev(prices_per_sqm) if len(prices_per_sqm) > 1 else 0,
                'properties': properties
            }
        
        return market_stats
    
    def get_property_market_insight(self, lokacio, jelleg, allapot, meret, price):
        """
        Get market insight for a specific property.
        Returns comparison with market average and other insights.
        """
        if not all([lokacio, jelleg, allapot, meret, price]) or meret <= 0 or price <= 0:
            return None
        
        size_interval = self.get_size_interval(meret)
        if not size_interval:
            return None
        
        market_stats = self.calculate_market_stats()
        segment_key = (lokacio, jelleg, allapot, size_interval)
        
        property_price_per_sqm = price / meret
        
        # Try to find exact match first
        market_data = market_stats.get(segment_key)
        
        # If no exact match, try broader matches
        fallback_matches = []
        if not market_data:
            for key, data in market_stats.items():
                key_lokacio, key_jelleg, key_allapot, key_interval = key
                
                # Same location and type, any condition
                if lokacio == key_lokacio and jelleg == key_jelleg and size_interval == key_interval:
                    fallback_matches.append(('same_location_type', data))
                # Same type and condition, any location in same district
                elif (jelleg == key_jelleg and allapot == key_allapot and size_interval == key_interval 
                      and lokacio.split(',')[0] == key_lokacio.split(',')[0]):
                    fallback_matches.append(('same_district_type', data))
        
        # Use the best available match
        comparison_type = 'exact'
        if market_data:
            market_avg = market_data['avg_price_per_sqm']
            market_count = market_data['count']
            market_std = market_data['std_price_per_sqm']
        elif fallback_matches:
            # Use the first fallback match
            comparison_type, market_data = fallback_matches[0]
            market_avg = market_data['avg_price_per_sqm']
            market_count = market_data['count']
            market_std = market_data['std_price_per_sqm']
        else:
            return None
        
        # Calculate insights
        price_diff_pct = ((property_price_per_sqm - market_avg) / market_avg) * 100
        price_diff_absolute = property_price_per_sqm - market_avg
        
        # Determine value assessment
        if price_diff_pct <= -15:
            value_assessment = "Kiváló ár-érték arány"
        elif price_diff_pct <= -5:
            value_assessment = "Jó ár-érték arány"  
        elif price_diff_pct <= 5:
            value_assessment = "Piaci átlag"
        elif price_diff_pct <= 15:
            value_assessment = "Piaci átlag felett"
        else:
            value_assessment = "Drága"
        
        return {
            'property_price_per_sqm': property_price_per_sqm,
            'market_avg_price_per_sqm': market_avg,
            'price_diff_pct': price_diff_pct,
            'price_diff_absolute': price_diff_absolute,
            'market_sample_count': market_count,
            'comparison_type': comparison_type,
            'value_assessment': value_assessment,
            'market_std': market_std,
            'size_interval': size_interval
        }
    
    def calculate_enhanced_worth_it_score(self, lokacio, jelleg, allapot, meret, price, rooms):
        """
        Calculate an enhanced worth it score based on market analysis.
        Returns a score between 0-100 where higher is better value.
        """
        insight = self.get_property_market_insight(lokacio, jelleg, allapot, meret, price)
        
        if not insight:
            # Fallback to simple calculation if no market data
            try:
                return round((rooms * 1000) / (price / meret), 2)
            except (ZeroDivisionError, TypeError):
                return None
        
        # Base score from market comparison (0-50 points)
        price_diff_pct = insight['price_diff_pct']
        if price_diff_pct <= -20:
            market_score = 50
        elif price_diff_pct <= -10:
            market_score = 40 + ((-10 - price_diff_pct) / 10) * 10
        elif price_diff_pct <= 0:
            market_score = 30 + ((0 - price_diff_pct) / 10) * 10  
        elif price_diff_pct <= 10:
            market_score = 20 - (price_diff_pct / 10) * 10
        elif price_diff_pct <= 20:
            market_score = 10 - ((price_diff_pct - 10) / 10) * 10
        else:
            market_score = 0
        
        # Property type specific adjustments
        is_house = jelleg and 'ház' in jelleg.lower()
        is_apartment = jelleg and 'lakás' in jelleg.lower()
        
        # Room efficiency scoring - different criteria for houses vs apartments
        if rooms and meret:
            if is_house:
                # Houses: More lenient room density expectations
                room_density = rooms / meret * 100  # rooms per 100 sqm
                if room_density >= 2.5:
                    room_score = 25
                elif room_density >= 2.0:
                    room_score = 22
                elif room_density >= 1.5:
                    room_score = 18
                elif room_density >= 1.2:
                    room_score = 15
                elif room_density >= 1.0:
                    room_score = 12
                else:
                    room_score = 8
                
                # Large house bonus (300+ sqm)
                if meret >= 300:
                    room_score += 3
                    
            else:
                # Apartments: Traditional room density scoring
                room_density = rooms / meret * 100  # rooms per 100 sqm
                if room_density >= 4:
                    room_score = 25
                elif room_density >= 3:
                    room_score = 20
                elif room_density >= 2.5:
                    room_score = 15
                elif room_density >= 2:
                    room_score = 10
                else:
                    room_score = 5
        else:
            room_score = 10  # neutral
        
        # Market confidence bonus (0-15 points) - adjusted for small market segments
        sample_count = insight['market_sample_count']
        if sample_count >= 10:
            confidence_score = 15
        elif sample_count >= 5:
            confidence_score = 12
        elif sample_count >= 3:
            confidence_score = 8  # Still reasonable for houses
        elif sample_count >= 2:
            confidence_score = 5
        else:
            confidence_score = 2
        
        # Condition quality bonus (0-10 points)
        condition_scores = {
            'Kiváló': 10,
            'Jó': 8,
            'Átlagos': 5,
            'Felújítandó': 2,
            'Rossz': 0
        }
        condition_score = condition_scores.get(allapot, 5)
        
        # Size premium for luxury properties (houses >400sqm, apartments >150sqm)
        size_bonus = 0
        if is_house and meret > 400:
            size_bonus = 3
        elif is_apartment and meret > 150:
            size_bonus = 2
        
        total_score = market_score + room_score + confidence_score + condition_score + size_bonus
        return round(min(total_score, 100), 1)  # Cap at 100