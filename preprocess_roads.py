import json
import os

def preprocess_and_filter():
    input_file = 'dataset/hotosm_npl_roads_lines_geojson.geojson'
    output_file = 'dataset/roads_subset.geojson'
    
    # Target BBox: Bagmati/Kathmandu area (approximate)
    min_lon, min_lat = 84.0, 26.8
    max_lon, max_lat = 86.6, 28.5
    
    print(f"Reading {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        # Check if it's a huge single-line file or formatted
        first_char = f.read(1)
        f.seek(0)
        
        data = json.load(f) # If it fits in memory, this is fastest. If not, use ijson.
        # Given 600MB, it MIGHT fit on a 16GB RAM machine but risky on 8GB.
        # But previous failures suggest maybe it's too big.
        # Let's try standard load first as simple streaming is hard without ijson.
        
        # If execution reaches here, load succeeded.
        print(f"File loaded. Filtering {len(data['features'])} features...")
        
        filtered_features = []
        for feature in data['features']:
            geom = feature.get('geometry')
            if not geom or geom['type'] != 'LineString':
                continue
            
            coords = geom['coordinates']
            # Simple check: if any point is in bbox
            in_bbox = False
            for lon, lat in coords:
                if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                    in_bbox = True
                    break
            
            if in_bbox:
                filtered_features.append(feature)
        
        print(f"Found {len(filtered_features)} features in target area.")
        
        output_data = {
            "type": "FeatureCollection",
            "name": "roads_subset",
            "crs": data.get("crs"),
            "features": filtered_features
        }
        
        with open(output_file, 'w', encoding='utf-8') as out:
            json.dump(output_data, out)
        
        print(f"Saved to {output_file}")

if __name__ == "__main__":
    try:
        preprocess_and_filter()
    except MemoryError:
        print("MemoryError: File too large for simple JSON load. Would need ijson.")
    except Exception as e:
        print(f"Error: {e}")
