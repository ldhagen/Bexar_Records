"""
This script generates interactive standalone maps for jail bookings and releases.
It utilizes a local Nominatim geocoding service running on http://localhost:8095
to convert inmate addresses into geographic coordinates.
The generated HTML includes dynamic filtering for crimes based on the selected date.
"""

import pandas as pd
import glob
import requests
import folium
from folium.plugins import MarkerCluster
import time
import json

def run_mapping(dataset_type='booking'):
    print(f"Loading {dataset_type} data...")
    if dataset_type == 'booking':
        file_pattern = 'JABookings_*.csv'
        output_file = 'booking_map_standalone.html'
    else:
        file_pattern = 'JAReleases_*.csv'
        output_file = 'release_map_standalone.html'

    files = sorted(glob.glob(file_pattern))
    if not files:
        print("No booking files found.")
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
    print(f"Total records loaded: {len(data)}")

    # Identify Homeless
    if 'Address1' in data.columns:
        data['IsHomeless'] = data['Address1'].astype(str).str.contains('HOMELESS', case=False, na=False)
    else:
        print("Address1 column missing.")
        return

    def geocode_address(address):
        url = "http://localhost:8095/search"
        params = {'q': address, 'format': 'json', 'limit': 1}
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200 and response.json():
                res = response.json()[0]
                return float(res['lat']), float(res['lon'])
        except Exception as e:
            pass
        return None, None

    unique_addresses = data['Address1'].unique()
    print(f"Geocoding {len(unique_addresses)} unique addresses...")

    geo_cache = {}
    for i, addr in enumerate(unique_addresses):
        if addr and "HOMELESS" not in str(addr).upper():
            lat, lon = geocode_address(addr)
            if lat:
                geo_cache[addr] = (lat, lon)
                if len(geo_cache) <= 5: print(f"DEBUG: Geocoded {addr} -> {lat}, {lon}")
        
        if i % 100 == 0:
            print(f"Processed {i}/{len(unique_addresses)} addresses... Cache hits: {len(geo_cache)}")

    print(f"Geocoding complete. Total cache size: {len(geo_cache)}")

    # Map coordinates
    data['latitude'] = data['Address1'].map(lambda x: geo_cache.get(x, (None, None))[0])
    data['longitude'] = data['Address1'].map(lambda x: geo_cache.get(x, (None, None))[1])

    valid_rows = data.dropna(subset=['latitude'])
    print(f"Rows with valid coordinates: {len(valid_rows)}")

    if len(valid_rows) == 0:
        print("WARNING: No valid coordinates found. Map will be blank.")
    
    # Create Map
    m = folium.Map(location=[29.4241, -98.4936], zoom_start=11)
    marker_cluster = MarkerCluster().add_to(m)

    unique_crimes = set()
    unique_dates = set()
    date_to_crimes = {}

    # Escape quotes to prevent JS errors in the map
    def escape_text(text):
        if pd.isna(text): return "N/A"
        return str(text).replace('"', '&quot;').replace("'", "&#39;").replace("`", "&#96;").replace("\n", " ")

    for idx, row in valid_rows.iterrows():
        color = 'red' if row.get('IsHomeless', False) else 'blue'
        
        if dataset_type == 'booking':
            inmate = row.get('InmateFullName', 'Unknown')
            charge_label = "Charge"
            charge = row.get('ChargeOffenseDescription', 'N/A')
            date_str = row.get('ConfineDate', 'N/A')
        else:
            inmate = row.get('InmateName', 'Unknown')
            charge_label = "Offense"
            charge = row.get('OffenseDescription', 'N/A')
            date_str = row.get('ReleaseDate', 'N/A')

        address = row.get('Address1', 'Unknown')
        lat = row['latitude']
        lon = row['longitude']
        
        inmate = escape_text(inmate)
        charge = escape_text(charge)
        address = escape_text(address)
        date_str = escape_text(date_str)
        
        unique_crimes.add(charge)
        unique_dates.add(date_str)

        if date_str not in date_to_crimes:
            date_to_crimes[date_str] = set()
        date_to_crimes[date_str].add(charge)

        popup_html = f"""
        <b>Inmate:</b> {inmate}<br>
        <b>Address:</b> {address}<br>
        <b>{charge_label}:</b> {charge}<br>
        <b>Date:</b> {date_str}<br>
        <a href='https://www.google.com/maps/search/?api=1&query={lat},{lon}' target='_blank'>Open in Google Maps</a>
        <div id="meta_{idx}" data-crime="{charge}" data-date="{date_str}" style="display:none"></div>
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=popup_html,
            tooltip=str(address),
            icon=folium.Icon(color=color)
        ).add_to(marker_cluster)

    # Sort unique values for dropdowns
    sorted_crimes = sorted(list(unique_crimes))
    sorted_dates = sorted(list(unique_dates))

    # Prepare date-to-crimes JSON structure
    # Convert sets to sorted lists for JSON serialization
    date_to_crimes_json = {k: sorted(list(v)) for k, v in date_to_crimes.items()}
    # We also need a list of ALL crimes for the "all" option
    all_crimes_json = sorted_crimes

    # Generate Options for Select
    crime_options = "".join([f'<option value="{c}">{c}</option>' for c in sorted_crimes])
    date_options = "".join([f'<option value="{d}">{d}</option>' for d in sorted_dates])

    # Inject Custom HTML/JS for Filtering
    map_id = m.get_name()
    cluster_id = marker_cluster.get_name()
    
    filter_html = f"""
    <div style="position: fixed; 
                top: 50px; right: 50px; width: 300px; height: auto; 
                z-index:9999; font-size:14px; background-color: white; 
                padding: 10px; border: 2px solid grey; border-radius: 5px;">
        <b>Filter Map</b><br>
        <label>Crime:</label>
        <select id="crime_select" style="width: 100%; margin-bottom: 5px;">
            <option value="all">All</option>
            {crime_options}
        </select>
        <br>
        <label>Date:</label>
        <select id="date_select" style="width: 100%; margin-bottom: 5px;">
            <option value="all">All</option>
            {date_options}
        </select>
    </div>
    """

    filter_script = f"""
    <script>
        var allLayers = [];
        var clusterName = "{cluster_id}";
        var clusterGroup;
        var initAttempts = 0;
        
        var dateToCrimes = {json.dumps(date_to_crimes_json)};
        var allCrimes = {json.dumps(all_crimes_json)};

        // Retry loop to capture layers once the map and clusterer are fully initialized
        var initInterval = setInterval(function() {{
            initAttempts++;
            clusterGroup = window[clusterName];
            
            if (clusterGroup && clusterGroup.getLayers().length > 0) {{
                allLayers = clusterGroup.getLayers();
                console.log("SUCCESS: Captured " + allLayers.length + " layers after " + initAttempts + " attempts.");
                clearInterval(initInterval);
            }} else if (initAttempts > 20) {{
                console.error("FAILED: Could not capture layers after 10 seconds.");
                clearInterval(initInterval);
            }} else {{
                console.log("Waiting for layers... attempt " + initAttempts);
            }}
        }}, 500);
        
        function updateCrimeOptions() {{
            var selDate = document.getElementById('date_select').value;
            var crimeSelect = document.getElementById('crime_select');
            var currentCrime = crimeSelect.value;
            
            var availableCrimes = (selDate === "all") ? allCrimes : (dateToCrimes[selDate] || []);
            
            // Clear existing options
            crimeSelect.innerHTML = '<option value="all">All</option>';
            
            // Add new options
            availableCrimes.forEach(function(crime) {{
                var opt = document.createElement('option');
                opt.value = crime;
                opt.textContent = crime;
                crimeSelect.appendChild(opt);
            }});
            
            // Restore previous selection if possible
            if (availableCrimes.includes(currentCrime)) {{
                crimeSelect.value = currentCrime;
            }} else {{
                crimeSelect.value = "all";
            }}
            
            filterMarkers();
        }}

        function filterMarkers() {{
            if (!clusterGroup || allLayers.length === 0) {{
                console.error("Cluster group not ready or no layers captured.");
                return;
            }}
            
            var selCrime = document.getElementById('crime_select').value;
            var selDate = document.getElementById('date_select').value;
            
            console.log("Filtering: Crime=" + selCrime + ", Date=" + selDate);

            var filtered = allLayers.filter(function(layer) {{
                var popup = layer.getPopup();
                if (!popup) return false;

                var content = popup.getContent();
                var metaDiv = null;

                if (typeof content === 'string') {{
                    var parser = new DOMParser();
                    var doc = parser.parseFromString(content, 'text/html');
                    metaDiv = doc.querySelector('div[id^="meta_"]');
                }} else if (content instanceof Element) {{
                    // Content is a DOM Element (common in Folium)
                    metaDiv = content.querySelector('div[id^="meta_"]');
                }}

                if (!metaDiv) {{
                    console.warn("No metadata found for marker", layer);
                    return true; // Keep safe
                }}
                
                var crime = metaDiv.getAttribute('data-crime');
                var date = metaDiv.getAttribute('data-date');
                
                var crimeMatch = (selCrime === "all") || (crime === selCrime);
                var dateMatch = (selDate === "all") || (date === selDate);
                
                return crimeMatch && dateMatch;
            }});
            
            console.log("Filtered down to " + filtered.length + " markers.");
            clusterGroup.clearLayers();
            clusterGroup.addLayers(filtered);
        }}

        document.getElementById('crime_select').addEventListener('change', filterMarkers);
        document.getElementById('date_select').addEventListener('change', updateCrimeOptions);
    </script>
    """

    m.get_root().html.add_child(folium.Element(filter_html + filter_script))

    m.save(output_file)
    print(f"Map saved to {output_file}")

if __name__ == "__main__":
    run_mapping('booking')
    run_mapping('release')
