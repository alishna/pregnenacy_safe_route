import geopandas as gpd

clinic_file = 'dataset/nepal.geojson'
gdf = gpd.read_file(clinic_file)
bounds = gdf.total_bounds
print(f"Clinic Bounds: {bounds}")
# Add buffer
buffer = 0.5 # degrees
bbox = (bounds[0]-buffer, bounds[1]-buffer, bounds[2]+buffer, bounds[3]+buffer)
print(f"Buffered BBox: {bbox}")
