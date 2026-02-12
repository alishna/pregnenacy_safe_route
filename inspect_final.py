import json

def inspect_data():
    # Inspect clinics (small file)
    print("--- Inspecting bagmati_clinics_scored.geojson ---")
    try:
        with open('dataset/bagmati_clinics_scored.geojson', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'features' in data and len(data['features']) > 0:
                print("First clinic properties:")
                print(json.dumps(data['features'][0]['properties'], indent=2))
            else:
                print("No features in clinics file")
    except Exception as e:
        print(f"Error reading clinics: {e}")

    # Inspect roads (large file) - read raw chars
    print("\n--- Inspecting hotosm_npl_roads_lines_geojson.geojson (Head) ---")
    try:
        with open('dataset/hotosm_npl_roads_lines_geojson.geojson', 'r', encoding='utf-8') as f:
            content = f.read(5000)
            print(content)
    except Exception as e:
        print(f"Error reading roads: {e}")

if __name__ == "__main__":
    inspect_data()
