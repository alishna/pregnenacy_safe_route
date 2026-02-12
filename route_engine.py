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
        
        # Try to load cached graph
        if os.path.exists(self.cache_file):
            print(f"Loading cached graph from {self.cache_file}...")
            try:
                with open(self.cache_file, 'rb') as f:
                    self.G = pickle.load(f)
                print(f"Graph loaded from cache! ({len(self.G.nodes)} nodes)")
                self.roads_gdf = None # Not needed if graph is loaded
            except Exception as e:
                print(f"Failed to load cache: {e}. Rebuilding...")
                self.G = None
        else:
            self.G = None

        if self.G is None:
            # Try to load preprocessed subset first
            subset_file = 'roads_subset.geojson'
            if os.path.exists(subset_file):
                print(f"Loading optimized road network from {subset_file}...")
                try:
                    self.roads_gdf = gpd.read_file(subset_file)
                    print(f"Loaded {len(self.roads_gdf)} road segments.")
                except Exception as e:
                    print(f"Error loading subset: {e}. Falling back to full file.")
                    self.roads_gdf = None
            else:
                self.roads_gdf = None
    
            if self.roads_gdf is None:
                print("Loading full road network... this may take a moment.")
                # Filter to Bagmati/Kathmandu region to speed up loading
                bbox = (84.0, 26.8, 86.6, 28.5) 
                try:
                    self.roads_gdf = gpd.read_file(road_file, bbox=bbox)
                    print(f"Loaded {len(self.roads_gdf)} road segments in bbox {bbox}")
                except Exception as e:
                    raise Exception(f"Failed to load road file: {e}")
    
            # Ensure we have a graph
            self.G = self._build_graph()
            
            # Save cache
            print(f"Saving graph to {self.cache_file}...")
            try:
                with open(self.cache_file, 'wb') as f:
                    pickle.dump(self.G, f)
                print("Cache saved.")
            except Exception as e:
                print(f"Warning: Could not save cache: {e}")
        
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
                
                # Add edges between coordinates
                coords = list(geom.coords)
                for i in range(len(coords) - 1):
                    u = coords[i]
                    v = coords[i+1]
                    
                    # Calculate segment length (approximate)
                    # Optimization: Use Haversine only if needed, or pre-calc
                    # For now keep existing logic but in faster loop
                    dist = self._haversine(u[1], u[0], v[1], v[0])
                    
                    G.add_edge(u, v, 
                               weight=dist, 
                               safety_factor=safety_factor)
        
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
        # Simple Euclidean search (slow for large graphs, optimize with k-d tree later)
        # For now, just finding min distance
        node_list = list(self.G.nodes)
        if not node_list:
            return None
        
        # Use simple squared euclidean distance for speed comparison
        closest_node = min(node_list, key=lambda n: (n[1]-lat)**2 + (n[0]-lon)**2)
        return closest_node

    def get_safest_route(self, start_lat, start_lon, week, risk_level):
        """
        Finds the route.
        Risk Logic:
        - High Risk (week > 28 OR risk='high'): Penalize rough roads heavily.
        - Low Risk: Standard weighting (prefer shortest, but avoid terrible roads).
        """
        start_node = self.find_nearest_node(start_lat, start_lon)
        
        # Find nearest clinic (destination)
        # Ideally we iterate through all clinics and find the one with the shortest weighted path
        # For prototype, let's just find the spatially closest clinic and route to it
        if self.clinics_gdf is None or self.clinics_gdf.empty:
            return None
            
        # Convert clinics points to list of coords
        # Handle Points and Polygons (use centroid)
        clinic_coords = []
        for geom in self.clinics_gdf.geometry:
            if geom.geom_type == 'Point':
                clinic_coords.append((geom.y, geom.x))
            else:
                # Use centroid for Polygons
                centroid = geom.centroid
                clinic_coords.append((centroid.y, centroid.x))
        
        # Find closest clinic in straight line (simplification)
        # A better approach: Run Dijkstra from start_node to ALL nodes and check clinic nodes.
        # Or Multi-source Dijkstra.
        target_clinic = min(clinic_coords, key=lambda c: (c[0]-start_lat)**2 + (c[1]-start_lon)**2)
        
        # Find nearest node to target clinic
        end_node = self.find_nearest_node(target_clinic[0], target_clinic[1])

        # Define weight function dynamically or based on attributes
        is_high_risk = (risk_level.lower() == 'high') or (week >= 28)
        
        def weight_func(u, v, d):
            base_dist = d.get('weight', 1.0)
            safety = d.get('safety_factor', 1.0)
            
            if is_high_risk:
                # Exponentially penalize bad roads
                # If safety=1.0 -> weight = dist * 1
                # If safety=1.3 -> weight = dist * 2 (approx)
                # If safety=1.8 -> weight = dist * 5 (approx)
                penalty = safety ** 3 
            else:
                penalty = safety
            
            return base_dist * penalty

        try:
            path = nx.shortest_path(self.G, source=start_node, target=end_node, weight=weight_func)
            
            # Reconstruct geometry
            path_geom = []
            total_dist = 0
            safe_score = 0
            
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                data = self.G.get_edge_data(u, v)
                # Get the edge with min weight if multigraph, simplified here for plain Graph
                edge_data = data # if not multigraph
                
                path_geom.append(LineString([u, v]))
                total_dist += edge_data.get('weight', 0)
                safe_score += edge_data.get('safety_factor', 1.0) * edge_data.get('weight', 0)
            
            avg_safety = safe_score / total_dist if total_dist > 0 else 1.0
            
            from shapely.geometry import MultiLineString
            route_geojson = gpd.GeoSeries(MultiLineString(path_geom)).__geo_interface__
            
            return {
                "route": route_geojson,
                "distance_meters": round(total_dist, 2),
                "avg_safety_factor": round(avg_safety, 2),
                "is_high_risk": is_high_risk
            }
            
        except nx.NetworkXNoPath:
            return None
