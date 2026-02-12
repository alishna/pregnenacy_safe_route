import json

def inspect_geojson_json(filepath):
    print(f"--- Inspecting {filepath} ---")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if 'features' in data and len(data['features']) > 0:
            print(f"Total features: {len(data['features'])}")
            print("First feature properties:")
            print(json.dumps(data['features'][0]['properties'], indent=2))
        else:
            print("No features found or invalid GeoJSON structure.")
            
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

inspect_geojson_json('dataset/hotosm_npl_roads_lines_geojson.geojson')
inspect_geojson_json('dataset/nepal.geojson')
