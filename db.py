import sqlite3
from typing import Dict, Any

class Database:
    def __init__(self, db_path: str = "businesses.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create businesses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS businesses (
                    place_id TEXT PRIMARY KEY,
                    name TEXT,
                    address TEXT,
                    latitude REAL,
                    longitude REAL,
                    type TEXT,
                    rating REAL,
                    user_ratings_total INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create search_points table to track which grid points we've searched
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_points (
                    latitude REAL,
                    longitude REAL,
                    radius INTEGER,
                    last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (latitude, longitude, radius)
                )
            ''')
            
            conn.commit()

    def insert_business(self, business_data: Dict[str, Any]) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO businesses 
                    (place_id, name, address, latitude, longitude, type, rating, user_ratings_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    business_data.get('place_id'),
                    business_data.get('name'),
                    business_data.get('address'),
                    business_data.get('latitude'),
                    business_data.get('longitude'),
                    business_data.get('type'),
                    business_data.get('rating'),
                    business_data.get('user_ratings_total')
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error inserting business: {e}")
            return False

    def mark_point_searched(self, latitude: float, longitude: float, radius: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO search_points 
                (latitude, longitude, radius, last_searched)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (latitude, longitude, radius))
            conn.commit()

    def is_point_searched(self, latitude: float, longitude: float, radius: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM search_points 
                WHERE latitude = ? AND longitude = ? AND radius = ?
            ''', (latitude, longitude, radius))
            return cursor.fetchone() is not None
