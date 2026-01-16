"""
Debug script for testing geocoding and map generation.
Uses local Nominatim service on http://localhost:8095 for address resolution.
"""

import pandas as pd
import glob
import requests
import folium
from folium.plugins import MarkerCluster

def debug_mapping():
    # Load JABookings
    files = sorted(glob.glob('JABookings_*.csv'))
    if not files:
        print("No JABookings files found.")
        return

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, dtype={'BondAmount': str, 'CaseNumber': str})
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
    
    if not dfs:
        print("No data loaded.")
        return

    data = pd.concat(dfs, ignore_index=True)
    print(f"Total records: {len(data)}")

    # Identify Homeless
    data['IsHomeless'] = data['Address1'].astype(str).str.contains('HOMELESS', case=False, na=False)

    # Test Geocoding Service
    test_address = "600 Soledad St, San Antonio, TX 78205"
    print(f"\nTesting Geocoding Service with: {test_address}")
    url = "http://localhost:8095/search"
    params = {'q': test_address, 'format': 'json', 'limit': 1}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.text}")
        else:
            print("Service returned non-200 status.")
    except Exception as e:
        print(f"Service Connection Failed: {e}")
        return

    # Check Address Data
    print("\nChecking Address Data:")
    unique_addresses = data['Address1'].unique()
    print(f"Total Unique Addresses: {len(unique_addresses)}")
    print("First 5 Unique Addresses:")
    print(unique_addresses[:5])

    # Attempt Geocoding a small sample
    print("\nAttempting to geocode first 5 valid addresses...")
    
    def geocode_address(address):
        try:
            params['q'] = address
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200 and response.json():
                res = response.json()[0]
                return float(res['lat']), float(res['lon'])
        except:
            pass
        return None, None

    success_count = 0
    for addr in unique_addresses[:5]:
        if addr and "HOMELESS" not in str(addr).upper():
            lat, lon = geocode_address(addr)
            print(f"Address: {addr} -> Lat: {lat}, Lon: {lon}")
            if lat: success_count += 1
    
    print(f"\nSuccessfully geocoded {success_count}/5 sample addresses.")

if __name__ == "__main__":
    debug_mapping()
