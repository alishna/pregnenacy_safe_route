import geopandas as gpd

def inspect_roads():
    print("--- Inspecting hotosm_npl_roads_lines_geojson.geojson ---")
    try:
        # Read only first 100 rows to avoid memory issues
        gdf = gpd.read_file('dataset/hotosm_npl_roads_lines_geojson.geojson', rows=100)
        print("Columns:", gdf.columns.tolist())
        print("First 5 rows:")
        print(gdf[['highway', 'surface', 'name']].head(5).to_string())
        
        # Check for other interesting columns
        print("\nUnique surface types (in first 100):")
        print(gdf['surface'].unique())
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_roads()
