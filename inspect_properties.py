import json

def find_properties(filepath):
    print(f"--- Inspecting properties of {filepath} ---")
    with open(filepath, 'r', encoding='utf-8') as f:
        buffer = ""
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            buffer += chunk
            # Look for properties object
            prop_idx = buffer.find('"properties":')
            if prop_idx != -1:
                # found it, try to extract the object
                start = buffer.find('{', prop_idx)
                if start != -1:
                    
                    # try to find matching closing brace
                    brace_count = 0
                    for i in range(start, len(buffer)):
                        if buffer[i] == '{':
                            brace_count += 1
                        elif buffer[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # Found the end
                                prop_str = buffer[start:i+1]
                                try:
                                    props = json.loads(prop_str)
                                    print(json.dumps(props, indent=2))
                                    return
                                except:
                                    pass
    print("Could not find properties or file too short")

find_properties('dataset/hotosm_npl_roads_lines_geojson.geojson')
find_properties('dataset/nepal.geojson')
