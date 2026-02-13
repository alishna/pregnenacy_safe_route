import geopandas as gpd
import networkx as nx
import math
import os
import pickle
from shapely.geometry import Point, LineString

class SafeRouter:
    def __init__(self, road_file, clinic_file):
        """
        Initialize the SafeRouter with road network and clinic data.
        """
        self.cache_file = "road_network.pickle"
        
        # Priority: 1. Cached Graph, 2. Preprocessed Subset, 3. Full GeoJSON
        if os.path.exists(self.cache_file):
            print(f"Loading cached graph from {self.cache_file}...")
            try:
                with open(self.cache_file, 'rb') as f:
                    self.G = pickle.load(f)
                print(f"Graph loaded! ({len(self.G.nodes)} nodes)")
                self.roads_gdf = None
            except Exception as e:
                print(f"Cache error: {e}. Rebuilding...")
                self.G = None
        else:
            self.G = None

        if self.G is None:
            subset_file = 'dataset/roads_subset.geojson'
            if os.path.exists(subset_file):
                print(f"Rebuilding graph from optimized subset: {subset_file}")
                self.roads_gdf = gpd.read_file(subset_file)
            else:
                print(f"Loading full road network (Slow): {road_file}")
                # Filter to Kathmandu area anyway
                bbox = (85.2, 27.65, 85.45, 27.8) 
                self.roads_gdf = gpd.read_file(road_file, bbox=bbox)
    
            self.G = self._build_graph()
            
            # Save cache
            print(f"Saving new cache to {self.cache_file}...")
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.G, f)
        
        # Load clinics
        print("Loading clinics...")
        try:
            self.clinics_gdf = gpd.read_file(clinic_file)
        except Exception as e:
            print(f"Warning: Failed to load clinics: {e}. Routing to clinics won't work.")
            self.clinics_gdf = None

    def _build_graph(self):
        """
        Convert GeoDataFrame of lines into a NetworkX MultiGraph.
        """
        G = nx.Graph()
        
        # Iterating with zip is much faster than iterrows
        geoms = self.roads_gdf.geometry
        surfaces = self.roads_gdf.get('surface', ['unknown'] * len(self.roads_gdf))
        highways = self.roads_gdf.get('highway', ['unknown'] * len(self.roads_gdf))
        
        print(f"Building graph from {len(geoms)} segments...")
        
        for geom, surface, highway in zip(geoms, surfaces, highways):
            if geom and geom.geom_type == 'LineString':
                # Determine safety factor
                safety_factor = self._get_safety_factor(surface, highway)
                
                # Add edges between coordinates with rounding to fix connectivity gaps
                coords = [(round(p[0], 6), round(p[1], 6)) for p in geom.coords]
                for i in range(len(coords) - 1):
                    u = coords[i]
                    v = coords[i+1]
                    dist = self._haversine(u[1], u[0], v[1], v[0])
                    G.add_edge(u, v, weight=dist, safety_factor=safety_factor)
        
        print(f"Graph built with {len(G.nodes)} nodes and {len(G.edges)} edges.")
        
        # Filter to largest connected component
        if not nx.is_connected(G):
            print("Graph not connected. Extracting largest connected component...")
            largest_cc = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_cc).copy()
            print(f"Reduced to largest component: {len(G.nodes)} nodes, {len(G.edges)} edges.")
            
        return G

    def _get_safety_factor(self, surface, highway):
        """
        Returns a safety factor multiplier (1.0 = best, higher = worse).
        """
        surface = str(surface).lower()
        highway = str(highway).lower()
        
        # Good surfaces
        if any(s in surface for s in ['paved', 'asphalt', 'concrete', 'bitumen']):
            return 1.0
        
        # Moderate surfaces
        if any(s in surface for s in ['gravel', 'unpaved', 'compacted', 'fine_gravel']):
            return 1.3
        
        # Bad surfaces
        if any(s in surface for s in ['dirt', 'earth', 'ground', 'mud', 'sand']):
            return 1.8
            
        # Fallback based on highway type
        if highway in ['primary', 'secondary', 'trunk', 'motorway']:
            return 1.0
        elif highway in ['residential', 'tertiary']:
            return 1.1
        elif highway in ['track', 'path']:
            return 1.5
            
        return 1.2 # Default unknown

    def _calculate_length(self, geom):
        # Placeholder if pre-calculated length isn't available
        # Ideally rely on projected CRS, but for now using simple assumption or attributes
        return geom.length # This is in degrees if CRS is 4326, which is not meters.
        # We handle segment length in _build_graph using haversine for weight

    def _haversine(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance in meters between two points 
        on the earth (specified in decimal degrees)
        """
        R = 6371000  # Radius of earth in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2)**2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def find_nearest_node(self, lat, lon):
        """Finds the closest node in the graph to the given lat/lon with rounding."""
        if not self.G:
            return None
            
        # Round input to match graph
        lon_r, lat_r = round(lon, 6), round(lat, 6)
            
        node_list = list(self.G.nodes)
        if not node_list:
            return None
        
        # Use simple squared Euclidean distance for speed
        closest_node = min(node_list, key=lambda n: (n[1]-lat_r)**2 + (n[0]-lon_r)**2)
        return closest_node

    def get_safest_route(self, start_lat, start_lon, week, risk_level):
        """
        Finds the safest route to the best hospital among any nearby options.
        
        Logic:
        1. Round input coordinates.
        2. Identify the top 5 spatially-closest clinics.
        3. For each clinic, find its nearest graph node.
        4. Calculate the safest path to each of these nodes.
        5. Return the one with the lowest total weighted cost.
        """
        start_node = self.find_nearest_node(start_lat, start_lon)
        if not start_node:
            return None
            
        if self.clinics_gdf is None or self.clinics_gdf.empty:
            return None
            
        # Build list of (lat, lon, index) for all clinics
        clinic_info = []
        for idx, row in self.clinics_gdf.iterrows():
            geom = row.geometry
            if geom.geom_type == 'Point':
                clinic_info.append((geom.y, geom.x, idx))
            else:
                c = geom.centroid
                clinic_info.append((c.y, c.x, idx))
        
        # Find 5 closest clinics spatially
        # This handles the user requirement: "shortest path even if bumpy" vs "longer safe path"
        # by letting Dijkstra evaluate the actual cost across several candidates.
        scored_clinics = sorted(clinic_info, key=lambda c: (c[0]-start_lat)**2 + (c[1]-start_lon)**2)
        candidates = scored_clinics[:5]
        
        is_high_risk = (risk_level.lower() == 'high') or (week >= 28)
        
        def weight_func(u, v, d):
            base_dist = d.get('weight', 1.0)
            safety = d.get('safety_factor', 1.0)
            penalty = safety ** 2 if is_high_risk else safety
            return base_dist * penalty

        best_result = None
        min_cost = float('inf')

        for target_lat, target_lon, clinic_idx in candidates:
            end_node = self.find_nearest_node(target_lat, target_lon)
            if not end_node:
                continue

            try:
                # Find path and total weight (cost)
                cost, path = nx.single_source_dijkstra(
                    self.G, source=start_node, target=end_node, weight=weight_func
                )
                
                if cost < min_cost:
                    min_cost = cost
                    best_result = (path, clinic_idx, target_lat, target_lon)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        if not best_result:
            return None

        path, clinic_idx, target_lat, target_lon = best_result
        
        # Reconstruct geometry
        path_geom = []
        click_point = (round(start_lon, 6), round(start_lat, 6))
        if click_point != path[0]:
            path_geom.append(LineString([click_point, path[0]]))
        
        total_dist = self._haversine(start_lat, start_lon, path[0][1], path[0][0])
        safe_score = total_dist * 1.0
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            edge_data = self.G.get_edge_data(u, v)
            path_geom.append(LineString([u, v]))
            dist = edge_data.get('weight', 0)
            total_dist += dist
            safe_score += edge_data.get('safety_factor', 1.0) * dist
        
        avg_safety = safe_score / total_dist if total_dist > 0 else 1.0
        
        from shapely.geometry import MultiLineString
        import geopandas as gpd
        route_geojson = gpd.GeoSeries(MultiLineString(path_geom)).__geo_interface__
        
        clinic_row = self.clinics_gdf.loc[clinic_idx]
        clinic_meta = {
            "name": str(clinic_row.get('name', 'Unknown')),
            "amenity": str(clinic_row.get('amenity', '')),
            "addr_city": str(clinic_row.get('addr_city', '')),
            "addr_street": str(clinic_row.get('addr_street', '')),
            "emergency": str(clinic_row.get('emergency', '')),
            "opening_hours": str(clinic_row.get('opening_hours', '')),
            "beds": int(clinic_row.get('beds', 0)) if clinic_row.get('beds') else 0,
            "operator": str(clinic_row.get('operator', '')),
            "lat": target_lat,
            "lon": target_lon,
        }
        
        return {
            "route": route_geojson,
            "distance_meters": round(total_dist, 2),
            "avg_safety_factor": round(avg_safety, 2),
            "is_high_risk": is_high_risk,
            "destination": clinic_meta,
        }
