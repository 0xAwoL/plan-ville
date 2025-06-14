Had nothing to do this evening so i decided to map all businesses in my city using google places API.
Google api provides some cool info about local businesses.

## How it works
The system creates a grid of 100m × 100m rectangles across the city center, then searches for businesses within a 100m radius from each grid point. To ensure no businesses are missed, the grid points are spaced 200m apart, creating overlapping search areas that cover every spot in the city.

Before starting the search, the system calculates and displays based on this:
- [Google Places API Pricing](https://developers.google.com/maps/billing-and-pricing/pricing#places-pricing)
- [Places API Nearby Search Documentation](https://developers.google.com/maps/documentation/places/web-service/nearby-search#fieldmask)

## Setup
1. provide you google api project key into .env
2. create venv `python -m venv venv`
3. `source venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python main.py`






