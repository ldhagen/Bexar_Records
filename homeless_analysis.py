import pandas as pd
import glob
import os

def analyze_homelessness():
    # File patterns
    booking_files = sorted(glob.glob('JABookings_*.csv'))
    release_files = sorted(glob.glob('JAReleases_*.csv'))

    print(f"Found {len(booking_files)} booking files and {len(release_files)} release files.")

    # Load Bookings
    bookings_dfs = []
    for f in booking_files:
        try:
            df = pd.read_csv(f)
            df['SourceFile'] = os.path.basename(f)
            bookings_dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
    
    if bookings_dfs:
        bookings = pd.concat(bookings_dfs, ignore_index=True)
    else:
        bookings = pd.DataFrame()

    # Load Releases
    releases_dfs = []
    for f in release_files:
        try:
            df = pd.read_csv(f)
            df['SourceFile'] = os.path.basename(f)
            releases_dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if releases_dfs:
        releases = pd.concat(releases_dfs, ignore_index=True)
    else:
        releases = pd.DataFrame()

    print(f"Total Booking Records: {len(bookings)}")
    print(f"Total Release Records: {len(releases)}")

    # Analysis Function
    def identify_homeless(df, name_col='InmateFullName'):
        if 'Address1' not in df.columns:
            return pd.DataFrame()
        
        # Filter for 'HOMELESS' in Address1 (case insensitive)
        # Also check for NaNs just in case
        homeless_mask = df['Address1'].astype(str).str.contains('HOMELESS', case=False, na=False)
        homeless_df = df[homeless_mask].copy()
        
        # Extract Zip Codes
        # Looking for 5 digits at the end or near the end of the string
        homeless_df['ZipCode'] = homeless_df['Address1'].astype(str).str.extract(r'(\d{5})')
        
        return homeless_df

    # Analyze Bookings
    if not bookings.empty:
        homeless_bookings = identify_homeless(bookings, 'InmateFullName')
        unique_homeless_bookings = homeless_bookings['SONumber'].nunique()
        total_unique_bookings = bookings['SONumber'].nunique()
        
        print("\n--- Bookings Analysis ---")
        print(f"Homeless Records: {len(homeless_bookings)}")
        print(f"Unique Homeless Individuals (by SONumber): {unique_homeless_bookings}")
        print(f"Percentage of Unique Individuals Identifying as Homeless: {unique_homeless_bookings / total_unique_bookings * 100:.2f}%" if total_unique_bookings > 0 else "N/A")
        
        # Top addresses for homeless
        print("\nCommon 'Homeless' Address Variations:")
        print(homeless_bookings['Address1'].value_counts().head(5))

        # Zip Code Analysis for Homeless
        print("\nTop Zip Codes for Homeless Bookings:")
        print(homeless_bookings['ZipCode'].value_counts().head(10))

    # Analyze Releases
    if not releases.empty:
        homeless_releases = identify_homeless(releases, 'InmateName')
        unique_homeless_releases = homeless_releases['SONumber'].nunique()
        total_unique_releases = releases['SONumber'].nunique()

        print("\n--- Releases Analysis ---")
        print(f"Homeless Records: {len(homeless_releases)}")
        print(f"Unique Homeless Individuals (by SONumber): {unique_homeless_releases}")
        print(f"Percentage of Unique Individuals Identifying as Homeless: {unique_homeless_releases / total_unique_releases * 100:.2f}%" if total_unique_releases > 0 else "N/A")
        
        # Zip Code Analysis for Homeless Releases
        print("\nTop Zip Codes for Homeless Releases:")
        print(homeless_releases['ZipCode'].value_counts().head(10))

if __name__ == "__main__":
    analyze_homelessness()
