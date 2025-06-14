import os 
import sqlite3
import db
import requests
import math
from typing import List, Dict, Any
import asyncio
import time
import numpy as np
from dotenv import load_dotenv
from datetime import datetime, timedelta
from checkpoint import CheckpointManager

load_dotenv()

class RateLimiter:
    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.calls = []
    
    async def acquire(self):
        now = datetime.now()

        # Filter out API calls older than 1 minute to maintain a rolling window of recent calls (rate limits)
        self.calls = [call for call in self.calls if now - call < timedelta(minutes=1)]
        
        if len(self.calls) >= self.calls_per_minute:
            wait_time = 60 - (now - self.calls[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.calls = [call for call in self.calls if now - call < timedelta(minutes=1)]
        
        self.calls.append(now)

class FindBusiness:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        
        self.db = db.Database()
        self.search_radius = 100  
        self.grid_spacing = 200  
        self.rate_limiter = RateLimiter(300)
        self.checkpoint_manager = CheckpointManager()
        
    def create_grid(self, center_lat: float, center_lng: float, city_radius_km: float) -> List[Dict[str, float]]:
        lat_degree = city_radius_km / 111.32
        lng_degree = city_radius_km / (111.32 * math.cos(math.radians(center_lat)))
        
        grid_points = []
        lat_step = self.grid_spacing / 111320
        lng_step = self.grid_spacing / (111320 * math.cos(math.radians(center_lat)))
        
        for lat in np.arange(center_lat - lat_degree, center_lat + lat_degree, lat_step):
            for lng in np.arange(center_lng - lng_degree, center_lng + lng_degree, lng_step):
                grid_points.append({"latitude": lat, "longitude": lng})
        
        return grid_points

    async def request_business_data(self, location: str, radius: int, page_token: str = None) -> Dict[str, Any]:
        await self.rate_limiter.acquire()
        
        base_url = "https://places.googleapis.com/v1/places:searchNearby"
        params = {
            "location": location,
            "radius": radius,
            "key": self.api_key,
            "fields": "displayName,location,primaryType,rating"
        }
        
        if page_token:
            params["pageToken"] = page_token
            
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return None

    def process_business_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not data or "places" not in data:
            return []
            
        processed_businesses = []
        for place in data["places"]:
            business = {
                "place_id": place.get("id"),
                "name": place.get("displayName", {}).get("text"),
                "address": place.get("formattedAddress"),
                "latitude": place.get("location", {}).get("latitude"),
                "longitude": place.get("location", {}).get("longitude"),
                "type": place.get("primaryType"),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("userRatingCount")
            }
            processed_businesses.append(business)
            
        return processed_businesses

    async def search_location(self, latitude: float, longitude: float):
        point = {"latitude": latitude, "longitude": longitude}
        
        # Skip if already processed
        if self.checkpoint_manager.is_point_processed(point):
            return
            
        if self.db.is_point_searched(latitude, longitude, self.search_radius):
            self.checkpoint_manager.mark_point_processed(point)
            return
            
        location = f"{latitude},{longitude}"
        page_token = None
        
        try:
            while True:
                data = await self.request_business_data(location, self.search_radius, page_token)
                if not data:
                    break
                    
                businesses = self.process_business_data(data)
                for business in businesses:
                    self.db.insert_business(business)
                    
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
                    
                await asyncio.sleep(2)
                
            self.db.mark_point_searched(latitude, longitude, self.search_radius)
            self.checkpoint_manager.mark_point_processed(point)
            
        except Exception as e:
            print(f"Error processing location {latitude},{longitude}: {e}")
            raise

    async def map_city(self, center_lat: float, center_lng: float, city_radius_km: float):
        grid_points = self.create_grid(center_lat, center_lng, city_radius_km)
        total_points = len(grid_points)
        processed_points = len(self.checkpoint_manager.processed_points)
        
        print(f"Starting search with {total_points - processed_points} points remaining")
        
        batch_size = 50
        
        for i in range(self.checkpoint_manager.current_batch, len(grid_points), batch_size):
            try:
                batch = grid_points[i:i + batch_size]
                tasks = [self.search_location(point["latitude"], point["longitude"]) for point in batch]
                await asyncio.gather(*tasks)
                
                # Save checkpoint after each successful batch
                self.checkpoint_manager.save_checkpoint(i + batch_size, 
                    [p for p in grid_points[:i + batch_size] if self.checkpoint_manager.is_point_processed(p)])
                
                if i + batch_size < len(grid_points):
                    await asyncio.sleep(1)
                    
                # Report progress
                progress = (i + batch_size) / total_points * 100
                print(f"Progress: {progress:.1f}% ({i + batch_size}/{total_points} points)")
                
            except Exception as e:
                print(f"Error processing batch {i}: {e}")
                self.checkpoint_manager.save_checkpoint(i, 
                    [p for p in grid_points[:i] if self.checkpoint_manager.is_point_processed(p)])
                raise

    def calculate_grid_info(self, center_lat: float, center_lng: float, city_radius_km: float) -> Dict[str, Any]:
        grid_points = self.create_grid(center_lat, center_lng, city_radius_km)
        num_points = len(grid_points)
        
        # Calculate remaining points
        remaining_points = num_points - len(self.checkpoint_manager.processed_points)
        
        estimated_api_calls = remaining_points * 1.5
        estimated_cost = (estimated_api_calls / 1000) * 17
        
        return {
            "total_grid_points": num_points,
            "processed_points": len(self.checkpoint_manager.processed_points),
            "remaining_points": remaining_points,
            "estimated_api_calls": int(estimated_api_calls),
            "estimated_cost_usd": round(estimated_cost, 2)
        }

if __name__ == "__main__":
    # New York City coordinates 
    CITY_LAT = 40.7831
    CITY_LNG = -73.9712
    CITY_RADIUS_KM = 5
    
    finder = FindBusiness()
    grid_info = finder.calculate_grid_info(CITY_LAT, CITY_LNG, CITY_RADIUS_KM)
    
    print("\nGrid Search Information:")
    print(f"Total grid points: {grid_info['total_grid_points']}")
    print(f"Already processed: {grid_info['processed_points']}")
    print(f"Remaining points: {grid_info['remaining_points']}")
    print(f"Estimated API calls: {grid_info['estimated_api_calls']}")
    print(f"Estimated cost: ${grid_info['estimated_cost_usd']}")
    
    response = input("\nDo you want to proceed with the search? (yes/no): ")
    if response.lower() == 'yes':
        try:
            asyncio.run(finder.map_city(CITY_LAT, CITY_LNG, CITY_RADIUS_KM))
            print("Search completed successfully!")
        except Exception as e:
            print(f"Search interrupted: {e}")
            print("You can resume the search later from the last checkpoint.")
    else:
        print("Search cancelled.")

        
