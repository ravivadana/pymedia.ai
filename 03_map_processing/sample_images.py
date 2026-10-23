import json
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import contextily as cx

# Paths
JSON_PATH = Path(r"C:\Ravi\Python\2025\Media\assets\india\airports.json")
SHAPEFILE_PATH = Path(r"C:\Ravi\Python\2025\Media\assets\common\maps\ne_10m_admin_1_states_provinces\ne_10m_admin_1_states_provinces.shp")
OUTPUT_DIR = Path("./sample_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load Shapefiles & Reproject to Web Mercator (EPSG:3857 for Tile Basemaps)
world_gdf = gpd.read_file(SHAPEFILE_PATH).to_crs(epsg=3857)

# Separate India and Foreign Neighbor States/Countries
india_gdf = world_gdf[world_gdf['admin'] == 'India'].copy()
india_gdf['color_id'] = np.arange(len(india_gdf))  # Color index per state

neighbors_gdf = world_gdf[world_gdf['admin'] != 'India'].copy()

# 2. Load Airport Data safely
with open(JSON_PATH, "r", encoding="utf-8") as f:
    raw_data = json.load(f)
    if isinstance(raw_data, dict):
        airports = raw_data.get("airports", raw_data.get("data", list(raw_data.values())))
    else:
        airports = raw_data

# 3. Render Satellite Background Frames
for idx, airport in enumerate(airports[:3]):
    fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=150)
    
    # Set outer canvas dark background
    fig.patch.set_facecolor('#040814')
    ax.set_facecolor('#040814')

    # LAYER 1: Draw Neighboring Countries (Semi-transparent overlay to let satellite show through)
    neighbors_gdf.plot(
        ax=ax,
        facecolor='#000000',
        edgecolor='#475569',
        linewidth=0.6,
        alpha=0.40,  # Keeps neighbor land visible without obscuring terrain
        zorder=2
    )

    # LAYER 2: Draw Multi-Colored Indian States (Stylized Semi-Transparent Overlay)
    india_gdf.plot(
        ax=ax,
        column='color_id',
        cmap='tab20',
        edgecolor='#FFFFFF',
        linewidth=0.8,
        alpha=0.45,  # Allows satellite ground textures to shine through state colors
        zorder=3
    )

    # LAYER 3: Calculate & Convert Airport Coordinates to EPSG:3857
    lat = float(airport.get("latitude", 0))
    lon = float(airport.get("longitude", 0))
    
    if lat and lon:
        pt_gdf = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([lon], [lat]),
            crs="EPSG:4326"
        ).to_crs(epsg=3857)
        
        x, y = pt_gdf.geometry.iloc[0].x, pt_gdf.geometry.iloc[0].y

        # Glowing Neon Pin Marker
        ax.scatter(x, y, color='#FF0055', s=1000, alpha=0.35, zorder=4)
        ax.scatter(x, y, color='#FF0055', s=500, alpha=0.60, zorder=5)
        ax.scatter(x, y, color='#FFFFFF', s=180, edgecolor='#000000', linewidth=2.5, zorder=6)

    # Set Map Viewing Limits (Includes Ocean & Surrounding Neighbors)
    minx, miny, maxx, maxy = india_gdf.total_bounds
    ax.set_xlim(minx - 600000, maxx + 600000)
    ax.set_ylim(miny - 500000, maxy + 500000)
    ax.axis('off')

    # LAYER 0: ADD REAL SATELLITE BASEMAP TILES
    # ESRI World Imagery provides realistic satellite land and ocean topography
    cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=1)

    # Information Card Overlay
    name = airport.get('name', airport.get('airport_name', 'Unknown')).upper()
    state_name = airport.get('state', '').upper()
    card_text = f"RANK #{idx + 1}\n{name}\n{state_name}"
    
    ax.text(
        0.5, 0.88, card_text,
        transform=ax.transAxes, fontsize=18, fontweight='bold', color='#FFFFFF',
        ha='center', bbox=dict(boxstyle="round,pad=0.8", facecolor="#080C14", alpha=0.92, edgecolor="#00F2FE", linewidth=1.5)
    )

    out_file = OUTPUT_DIR / f"test_satellite_rank_{idx + 1}.png"
    plt.savefig(out_file, bbox_inches='tight', pad_inches=0.2, facecolor=fig.get_facecolor(), dpi=150)
    plt.close(fig)
    print(f"Saved Satellite Map Frame: {out_file.resolve()}")