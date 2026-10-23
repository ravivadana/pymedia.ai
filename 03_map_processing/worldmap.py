import geopandas as gpd
import matplotlib.pyplot as plt
import tkinter as tk
import os
import numpy as np
from matplotlib.path import Path
import matplotlib.patches as patches
from PIL import Image

class WorldMapPlotterFlags:
    def __init__(self, shapefile_path, flags_directory, countries=None, show_flags=True, show_labels=True):
        self.shapefile_path = shapefile_path
        self.flags_directory = flags_directory
        self.show_flags = show_flags
        self.show_labels = show_labels

        # Load world shapefile
        self.world = gpd.read_file(self.shapefile_path)

        # Convert full world to Web Mercator for background boundaries
        self.world_merc = self.world.to_crs(epsg=3857)

        # Map input list names to match the Natural Earth shapefile NAME field
        self.shapefile_name_map = {
            "united states": "united states of america",
            "congo dr": "Dem. Rep. Congo",
            "ir iran": "Iran",
            "turkiye": "turkey",
            "czechia": "czech rep."
        }

        if countries:
            # Clean and map incoming names to shapefile standards
            clean_input_names = []
            for c in countries:
                name_lower = c.lower().strip()
                mapped_name = self.shapefile_name_map.get(name_lower, name_lower)
                clean_input_names.append(mapped_name)
            
            # Filter shapefile matching the list (case-insensitive check against 'NAME')
            matched_countries = self.world[self.world['NAME'].str.lower().isin(clean_input_names)]
            self.selected_countries = matched_countries.to_crs(epsg=3857)
        else:
            # Fallback: Compute area and select top 10 countries by area
            world_equal_area = self.world.to_crs(epsg=6933)
            world_equal_area['area'] = world_equal_area.geometry.area
            top10_equal_area = world_equal_area.nlargest(10, 'area').reset_index(drop=True)
            self.selected_countries = top10_equal_area.to_crs(epsg=3857)

    def _get_flag_path(self, country_name):
        """Finds flag file matching patterns while prioritizing literal names with spaces."""
        flag_name_map = {
            "United States of America": "United States",
            "Dem. Rep. Congo": "Congo DR",
            "Iran": "IR Iran",
            "Turkey": "Türkiye",
            "Czech Rep.": "Czechia"
        }
        
        display_name = flag_name_map.get(country_name, country_name)

        filename_with_spaces = f"{display_name}_flag.png"
        path_spaces = os.path.join(self.flags_directory, filename_with_spaces)
        if os.path.exists(path_spaces):
            return path_spaces

        filename_with_underscores = f"{display_name.replace(' ', '_')}_flag.png"
        path_underscores = os.path.join(self.flags_directory, filename_with_underscores)
        if os.path.exists(path_underscores):
            return path_underscores
            
        if os.path.exists(self.flags_directory):
            target_clean = display_name.lower().replace(" ", "").replace("_", "")
            for file in os.listdir(self.flags_directory):
                file_clean = file.lower().replace(" ", "").replace("_", "").replace("flag.png", "")
                if file_clean == target_clean or file_clean == target_clean + "flag":
                    return os.path.join(self.flags_directory, file)
                    
        return None

    def _fill_country_with_flag(self, ax, geom, flag_path):
        """Clips the flag image to the exact polygon boundary of the country and adds an outline."""
        try:
            img = Image.open(flag_path)
            xmin, ymin, xmax, ymax = geom.bounds
            
            im = ax.imshow(img, extent=[xmin, xmax, ymin, ymax], origin='upper', aspect='auto')
            
            if geom.geom_type == 'Polygon':
                geoms = [geom]
            else:
                geoms = list(geom.geoms)
                
            verts = []
            codes = []
            for g in geoms:
                ext_coords = np.array(g.exterior.coords)
                verts.extend(ext_coords)
                codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ext_coords) - 2) + [Path.CLOSEPOLY])
                for interior in g.interiors:
                    int_coords = np.array(interior.coords)
                    verts.extend(int_coords)
                    codes.extend([Path.MOVETO] + [Path.LINETO] * (len(int_coords) - 2) + [Path.CLOSEPOLY])
            
            path = Path(verts, codes)
            
            # Create mask patch to clip the flag image
            patch = patches.PathPatch(path, facecolor='none', edgecolor='none', transform=ax.transData)
            ax.add_patch(patch)
            im.set_clip_path(patch)

            # Draw a dark outline over the flag
            outline_patch = patches.PathPatch(path, facecolor='none', edgecolor='#333333', linewidth=0.6, transform=ax.transData)
            ax.add_patch(outline_patch)
            
        except Exception as e:
            print(f"Error filling flag from {flag_path}: {e}")

    def _get_screen_size(self):
        """Safely fetch screen dimensions."""
        root = tk.Tk()
        root.withdraw()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.quit()
        return width, height

    def create_map(self):
        screen_width, screen_height = self._get_screen_size()

        fig, ax = plt.subplots(figsize=(screen_width/100, screen_height/100), dpi=100)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        ax.set_axis_off()

        # Plot full world gray background boundaries
        self.world_merc.boundary.plot(ax=ax, color="gainsboro", linewidth=0.4)

        # Fill selected countries with their flags
        if self.show_flags:
            for i, row in self.selected_countries.iterrows():
                country_name = row.NAME
                flag_path = self._get_flag_path(country_name)

                if flag_path:
                    self._fill_country_with_flag(ax, row.geometry, flag_path)
                else:
                    print(f"Warning: Flag image not found for {country_name}")

        # Add country name labels
        if self.show_labels:
            # Map shapefile names back to clean display labels if preferred
            display_name_map = {
                "United States of America": "United States",
                "Dem. Rep. Congo": "Congo DR",
                "Iran": "Iran",
                "Turkey": "Türkiye",
                "Czech Rep.": "Czechia"
            }
            
            for i, row in self.selected_countries.iterrows():
                geom = row.geometry
                # Find a stable visual center inside the country boundary
                x, y = geom.representative_point().coords[0]
                
                label_text = display_name_map.get(row.NAME, row.NAME)
                
                # Render label with a minor shadow/outline effect for readability on busy flags
                ax.text(
                    x, y, label_text, fontsize=10, fontweight='bold',
                    color='black', ha='center', va='center',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2')
                )

        # Set world extent (shifted upward)
        ax.set_xlim(-20026376, 20026376)
        ax.set_ylim(-7018754, 13018754)

        plt.show()


if __name__ == "__main__":
    shapefile_path = "C:/Ravi/Python/2025/Media/assets/common/maps/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"
    flags_directory = r"C:\Ravi\Python\2025\Media\assets\common\images\countries_flags"

    my_countries = [
        "Algeria", "Argentina", "Australia", "Austria", "Belgium", "Bosnia and Herzegovina",
        "Brazil", "Cabo Verde", "Canada", "Colombia", "Congo DR", "Costa Rica", "Croatia",
        "Curaçao", "Czechia", "Ecuador", "Egypt", "England", "France", "Germany", "Ghana",
        "Haiti", "Iran", "Iraq", "Japan", "Jordan", "Mexico", "Morocco", "Netherlands",
        "New Zealand", "Norway", "Panama", "Paraguay", "Portugal", "Qatar", "Saudi Arabia",
        "Scotland", "Senegal", "South Africa", "South Korea", "Spain", "Sweden", "Switzerland",
        "Tunisia", "Türkiye", "United States", "Uruguay", "Uzbekistan"
    ]

    # Initialize and run
    plotter = WorldMapPlotterFlags(shapefile_path, flags_directory, countries=my_countries, show_flags=True, show_labels=True)
    plotter.create_map()