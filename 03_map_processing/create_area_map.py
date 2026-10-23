import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import LineString
import matplotlib.cm as cm
import tkinter as tk
import json

class WorldMapPlotterTop10:
    def __init__(self, shapefile_path, short_names_path, show_labels=True, tiny_country_area=5e10):
        self.shapefile_path = shapefile_path
        self.short_names_path = short_names_path
        self.show_labels = show_labels
        self.tiny_country_area = tiny_country_area

        # Load world shapefile
        self.world = gpd.read_file(self.shapefile_path)

        # Load short names
        with open(self.short_names_path, "r") as f:
            self.short_names = json.load(f)

        # Compute area in equal-area projection
        world_equal_area = self.world.to_crs(epsg=6933)  # World Cylindrical Equal Area
        world_equal_area['area'] = world_equal_area.geometry.area

        # Select top 10 countries by area
        self.top10_equal_area = world_equal_area.nlargest(10, 'area').reset_index(drop=True)

        # Convert top 10 to Web Mercator for plotting
        self.top10 = self.top10_equal_area.to_crs(epsg=3857)

        # Convert full world to Web Mercator for plotting
        self.world_merc = self.world.to_crs(epsg=3857)

        # Generate vertical lines
        self.lines_gdf = self._generate_vertical_lines()

    def _generate_vertical_lines(self):
        """Generate vertical timezone lines every 15 degrees with distinct colors."""
        lines = []
        longitudes = range(-180, 181, 15)
        cmap = cm.get_cmap('hsv', len(longitudes))
        colors = []

        for i, lon in enumerate(longitudes):
            lines.append(LineString([(lon, -90), (lon, 90)]))
            colors.append(cmap(i))

        lines_gdf = gpd.GeoDataFrame({'geometry': lines, 'color': colors}, crs="EPSG:4326")
        return lines_gdf.to_crs(epsg=3857)

    def create_map(self):
        # Full screen size
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()

        fig, ax = plt.subplots(figsize=(screen_width/100, screen_height/100), dpi=100)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        ax.set_axis_off()

        # Plot world boundaries
        self.world_merc.boundary.plot(ax=ax, color="lightgray", linewidth=0.5)

        # Plot vertical lines
        for row in self.lines_gdf.itertuples():
            ax.plot(*row.geometry.xy, color=row.color, linewidth=0.5, alpha=0.7)

        # Color map for top 10 labels
        label_cmap = cm.get_cmap('tab10', 10)

        # Add labels for top 10 countries
        if self.show_labels:
            for i, row in self.top10.iterrows():
                geom = row.geometry
                x, y = geom.representative_point().coords[0]

                # Automatic offset for tiny countries
                if geom.area < self.tiny_country_area:
                    dx = min((geom.bounds[2] - geom.bounds[0]) * 2, 5e5)  # max 500 km
                    dy = min((geom.bounds[3] - geom.bounds[1]) * 2, 5e5)
                    x += dx
                    y += dy

                # Get short name, fallback to full name
                short_name = self.short_names.get(row.NAME, row.NAME)
                label_text = f"{i+1}. {short_name}"

                # Label color from cmap
                label_color = label_cmap(i)

                ax.text(
                    x, y, label_text, fontsize=14, fontweight='bold',
                    color=label_color, ha='center', va='center'
                )

        # Add basemap
        ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery)

        # Set world extent
        ax.set_xlim(-20026376, 20026376)
        ax.set_ylim(-10018754, 10018754)

        plt.show()


if __name__ == "__main__":
    shapefile_path = "C:/Ravi/Python/2025/Media/assets/common/maps/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"
    short_names_path = "C:/Ravi/Python/2025/Media/assets/common/data/countries_abbreviations.json"

    plotter = WorldMapPlotterTop10(shapefile_path, short_names_path, show_labels=True)
    plotter.create_map()
