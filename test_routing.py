from route_engine import SafeRouter
import geopandas as gpd

def test_engine():
    road_file = 'dataset/hotosm_npl_roads_lines_geojson.geojson'
    clinic_file = 'dataset/nepal.geojson'
    
    print("Initializing Router...")
    router = SafeRouter(road_file, clinic_file)
    
    # Pick a random node from the graph as start point
    if not router.G.nodes:
        print("Graph is empty!")
        return

    start_node = list(router.G.nodes)[0]
    start_lat, start_lon = start_node[1], start_node[0] # Node is (x, y) = (lon, lat)
    
    print(f"Testing route from {start_lat}, {start_lon}")
    
    # Low Risk
    print("\n--- Low Risk Route ---")
    route_low = router.get_safest_route(start_lat, start_lon, week=10, risk_level='low')
    if route_low:
        print(f"Distance: {route_low['distance_meters']}m")
        print(f"Avg Safety Factor: {route_low['avg_safety_factor']}")
    else:
        print("No route found for low risk.")

    # High Risk
    print("\n--- High Risk Route ---")
    route_high = router.get_safest_route(start_lat, start_lon, week=32, risk_level='high')
    if route_high:
        print(f"Distance: {route_high['distance_meters']}m")
        print(f"Avg Safety Factor: {route_high['avg_safety_factor']}")
    else:
        print("No route found for high risk.")

if __name__ == "__main__":
    test_engine()
