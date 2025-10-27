# =============================================================================
#
#                RANDOM WALKING PATH SUGGESTER
#
#  Instructions for Use:
#  1. Fill out the "USER CONFIGURATION" section below with your details.
#  2. Run the script: python random_walker.py
#  3. On the first run, it will download the map for your area (this may take
#     a few minutes). Subsequent runs will be very fast.
#  4. Open the generated text file (e.g., "my_random_walk.txt") to get a
#     Google Maps link for your suggested walk.
#
# =============================================================================

import osmnx as ox
import networkx as nx
import random
import math
import os

# =============================================================================
# ======================== USER CONFIGURATION =================================
# =============================================================================

# 1. SET YOUR LOCATION
# --------------------
# Define the general city or area for your walks.
# This is used for the one-time map download. Make it large enough
# to contain any walk you might want to do.
# Example: "Kolkata, West Bengal, India" or "Manhattan, New York, USA"
PLACE_NAME = "Kolkata, West Bengal, India"

# 2. SET YOUR HOME COORDINATES
# ----------------------------
# This is your exact starting and ending point.
# How to get your coordinates:
#   - Go to maps.google.com on a computer.
#   - Right-click on your exact home location on the map.
#   - Click the coordinates that appear at the top of the menu to copy them.
#   - Paste them here (latitude, longitude).
# Example: (22.5448, 88.3426) # Victoria Memorial, Kolkata
START_LAT_LON = (22.531060, 88.400831)

# 3. SET YOUR DESIRED WALK DISTANCE
# ---------------------------------
# Enter the total distance you want to walk, in kilometers.
TARGET_DISTANCE_KM = 4.0

# 4. (Optional) ADVANCED SETTINGS
# -------------------------------
# Tolerance: How much longer or shorter the suggested path can be.
# 0.1 means the path will be within +/- 10% of your target distance.
DISTANCE_TOLERANCE = 0.15

# Output Filename: The name of the text file that will contain your
# Google Maps link and coordinate list.
OUTPUT_FILENAME = "my_random_walk.txt"

# Map Filename: The script will save the downloaded map data to this file
# to avoid re-downloading. You usually don't need to change this.
# It's created automatically from your PLACE_NAME.
MAP_FILENAME = f"{PLACE_NAME.split(',')[0].lower().replace(' ', '_')}_walk_map.graphml"

# =============================================================================
# =================== END OF CONFIGURATION ====================================
# =============================================================================


# --- Core Program Logic ---

def setup_map_graph(place_name, filepath):
    """Loads map from file if it exists, otherwise downloads and saves it."""
    if os.path.exists(filepath):
        print(f"Map file '{filepath}' found. Loading from disk...")
        graph = ox.load_graphml(filepath=filepath)
        print("Map loaded successfully.")
    else:
        print(f"Map file not found. Downloading map for '{place_name}'...")
        print("This is a one-time download and may take several minutes.")
        graph = ox.graph_from_place(place_name, network_type="walk")
        ox.save_graphml(graph, filepath=filepath)
        print(f"Map downloaded and saved to '{filepath}' for future use.")
    return graph

def get_random_point_in_circle(lat, lon, radius_km):
    """Generates a uniformly random lat/lon point within a circle."""
    R = 6371
    r = radius_km * math.sqrt(random.uniform(0, 1))
    theta = random.uniform(0, 2 * math.pi)
    lat_rad, lon_rad = math.radians(lat), math.radians(lon)
    new_lat_rad = math.asin(math.sin(lat_rad) * math.cos(r / R) +
                          math.cos(lat_rad) * math.sin(r / R) * math.cos(theta))
    new_lon_rad = lon_rad + math.atan2(math.sin(theta) * math.sin(r / R) * math.cos(lat_rad),
                                     math.cos(r / R) - math.sin(lat_rad) * math.sin(new_lat_rad))
    return math.degrees(new_lat_rad), math.degrees(new_lon_rad)

def generate_walk_in_circle(graph, start_node, total_distance_km, tolerance, max_attempts=50):
    """Generates a random walking loop of a given distance."""
    radius_km = total_distance_km / 4
    start_lat, start_lon = graph.nodes[start_node]['y'], graph.nodes[start_node]['x']
    min_dist_m = (total_distance_km * (1 - tolerance)) * 1000
    max_dist_m = (total_distance_km * (1 + tolerance)) * 1000
    
    for i in range(max_attempts):
        print(f"Attempt {i+1}/{max_attempts} to find a suitable path...")
        b_lat, b_lon = get_random_point_in_circle(start_lat, start_lon, radius_km)
        c_lat, c_lon = get_random_point_in_circle(start_lat, start_lon, radius_km)
        
        node_b = ox.nearest_nodes(graph, X=b_lon, Y=b_lat)
        node_c = ox.nearest_nodes(graph, X=c_lon, Y=c_lat)

        if node_b == start_node or node_c == start_node or node_b == node_c: continue
            
        try:
            path_ab = nx.shortest_path(graph, source=start_node, target=node_b, weight='length')
            path_bc = nx.shortest_path(graph, source=node_b, target=node_c, weight='length')
            path_ca = nx.shortest_path(graph, source=node_c, target=start_node, weight='length')
            full_path = path_ab[:-1] + path_bc[:-1] + path_ca
            
            path_length_m = sum(graph.edges[u, v, 0]['length'] for u, v in zip(full_path[:-1], full_path[1:]))

            if min_dist_m <= path_length_m <= max_dist_m:
                print(f"\nSuccess! Found a path of {path_length_m / 1000:.2f} km.")
                return full_path
        except (nx.NetworkXNoPath, KeyError):
            continue
            
    print("\nCould not find a suitable path after all attempts. Try increasing the distance or tolerance.")
    return None

def save_path_for_gmaps(graph, path_nodes, filename):
    """Converts a path of nodes to coordinates and saves them to a text file."""
    max_waypoints_for_url = 23
    if len(path_nodes) > max_waypoints_for_url:
        step = len(path_nodes) // (max_waypoints_for_url - 1)
        url_nodes = path_nodes[::step]
        if url_nodes[-1] != path_nodes[-1]:
             url_nodes.append(path_nodes[-1])
    else:
        url_nodes = path_nodes

    base_url = "https://www.google.com/maps/dir/"
    url_coords = [f"{graph.nodes[node]['y']},{graph.nodes[node]['x']}" for node in url_nodes]
    gmaps_url = base_url + "/".join(url_coords)

    full_coords = [f"{graph.nodes[node]['y']},{graph.nodes[node]['x']}" for node in path_nodes]

    with open(filename, "w") as f:
        f.write("--- Your Random Walk for Google Maps ---\n\n")
        f.write("Option 1: Clickable Link (Best for Phones)\n")
        f.write("Copy this entire link and open it in your phone's browser:\n\n")
        f.write(gmaps_url)
        f.write("\n\n-------------------------------------------------\n\n")
        f.write("Option 2: Full Coordinate List (for other mapping tools)\n\n")
        f.write("\n".join(full_coords))
    
    print(f"Path saved! Check the file '{filename}' for your Google Maps link.")

if __name__ == "__main__":
    # Main execution block
    G = setup_map_graph(PLACE_NAME, MAP_FILENAME)
    
    start_node = ox.nearest_nodes(G, X=START_LAT_LON[1], Y=START_LAT_LON[0])
    
    random_path = generate_walk_in_circle(G, start_node, TARGET_DISTANCE_KM, DISTANCE_TOLERANCE)
    
    if random_path:
        save_path_for_gmaps(G, random_path, OUTPUT_FILENAME)