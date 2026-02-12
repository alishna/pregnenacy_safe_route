from route_engine import SafeRouter
import networkx as nx
import pickle

def analyze_graph():
    print("Loading graph...")
    with open("road_network.pickle", "rb") as f:
        G = pickle.load(f)
    
    print(f"Nodes: {len(G.nodes)}")
    print(f"Edges: {len(G.edges)}")
    
    if nx.is_connected(G):
        print("Graph is fully connected!")
    else:
        print("Graph is NOT connected.")
        components = sorted(nx.connected_components(G), key=len, reverse=True)
        print(f"Number of components: {len(components)}")
        print(f"Largest component size: {len(components[0])}")
        print(f"Second largest: {len(components[1]) if len(components)>1 else 0}")
        
    # Check if clinics are near the largest component
    # (Skipping for now, just want to know if main graph is viable)

if __name__ == "__main__":
    analyze_graph()
