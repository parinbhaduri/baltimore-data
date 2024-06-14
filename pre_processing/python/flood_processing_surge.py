## import necessary packages
import os
from os.path import join
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import rioxarray as rx

FO = Path().absolute()

## Import baltimore block group geometries as geodataframe
balt_bg = gpd.read_file(join(FO, "model_inputs", "bg_baltimore.csv"), 
                        GEOM_POSSIBLE_NAMES="geometry",
                        KEEP_GEOM_COLUMNS="NO")

balt_bg = balt_bg.set_crs('epsg:3857')
balt_bg = balt_bg.to_crs('epsg:4269')


## Read in surge data and convert to csv
directory = join(FO, "raw_data", "flood_inputs", "FastFlood", "Base")

#Extract surge level and create dataframe from first file
file_0 = os.listdir(directory)[0]
surge_name = ""
surge_name = surge_name.join([*file_0.split('_')[2]][0:3])
surge_name = str(int(surge_name)/100)

ras = rx.open_rasterio(os.path.join(directory, file_0))
band = ras[0]
x, y, extent = band.x.values, band.y.values, band.values
x, y = np.meshgrid(x, y)
x, y, extent = x.flatten(), y.flatten(), extent.flatten()

#Convert to point geometries 
surge_depths = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_xy(x, y, crs=band.rio.crs))
surge_depths[surge_name] = extent

# Repeat for remaining files and add to surge_depths
band_dict = {}
for filename in os.listdir(directory)[1:]:
    if filename.endswith(".tif"):
        raster = rx.open_rasterio(os.path.join(directory, filename))
        #get first band of raster
        band = raster[0]
        extent = band.values.flatten()

        #Extract return level from filename
        surge_name = ""
        surge_name = surge_name.join([*filename.split('_')[2]][0:3])
        surge_name = str(int(surge_name)/100)
        ##add to list
        band_dict[surge_name] = extent
    else:
        continue

band_df = pd.DataFrame.from_dict(band_dict)
surge_depths = pd.concat([surge_depths, band_df], axis = 1)

#join centroid geometries with block group geometries
bg_flood_area = gpd.sjoin(balt_bg[["fid_1","GISJOIN","GEOID","geometry"]], surge_depths)

#determine whether max flood depth occurrence within each block group
bg_flood_max = bg_flood_area.drop('geometry', axis = 1).groupby('GISJOIN', as_index = False).max()

#Rejoin block group geometries
#balt_flood = balt_bg[["GISJOIN","geometry"]].merge(bg_flood_max, on='GISJOIN')

balt_flood = bg_flood_max.drop('index_right', axis = 1)
#Reorder columns so that surge level columns are in ascending order 
surge_cols = [float(x) for x in balt_flood.columns[3:]]
surge_cols.sort()
new_cols = ['GISJOIN'] + ['GEOID'] + ['fid_1'] + [str(x) for x in surge_cols]
balt_flood = balt_flood[new_cols]

#save dataframe to csv
balt_flood.to_csv(join(FO, 'model_inputs','surge_baltimore_base.csv'))










### Repeat with Levee Files
directory = join(FO, "raw_data", "flood_inputs", "FastFlood", "Levee")

#Extract surge level and create dataframe from first file
file_0 = os.listdir(directory)[0]
surge_name = ""
surge_name = surge_name.join([*file_0.split('_')[2]][0:3])
surge_name = str(int(surge_name)/100)

ras = rx.open_rasterio(os.path.join(directory, file_0))
band = ras[0]
x, y, extent = band.x.values, band.y.values, band.values
x, y = np.meshgrid(x, y)
x, y, extent = x.flatten(), y.flatten(), extent.flatten()

#Convert to point geometries 
surge_depths = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_xy(x, y, crs=band.rio.crs))
surge_depths[surge_name] = extent

# Repeat for remaining files and add to surge_depths
band_dict = {}
for filename in os.listdir(directory)[1:]:
    if filename.endswith(".tif"):
        raster = rx.open_rasterio(os.path.join(directory, filename))
        #get first band of raster
        band = raster[0]
        extent = band.values.flatten()

        #Extract return level from filename
        surge_name = ""
        surge_name = surge_name.join([*filename.split('_')[2]][0:3])
        surge_name = str(int(surge_name)/100)
        ##add to list
        band_dict[surge_name] = extent
    else:
        continue

band_df = pd.DataFrame.from_dict(band_dict)
surge_depths = pd.concat([surge_depths, band_df], axis = 1)

#join centroid geometries with block group geometries
bg_flood_area = gpd.sjoin(balt_bg[["fid_1","GISJOIN","GEOID","geometry"]], surge_depths)

#determine whether max flood depth occurrence within each block group
bg_flood_max = bg_flood_area.drop('geometry', axis = 1).groupby('GISJOIN', as_index = False).max()

#Rejoin block group geometries
#balt_flood = balt_bg[["GISJOIN","geometry"]].merge(bg_flood_max, on='GISJOIN')

balt_flood = bg_flood_max.drop('index_right', axis = 1)
#Reorder columns so that surge level columns are in ascending order 
surge_cols = [float(x) for x in balt_flood.columns[3:]]
surge_cols.sort()
new_cols = ['GISJOIN'] + ['GEOID'] + ['fid_1'] + [str(x) for x in surge_cols]
balt_flood = balt_flood[new_cols]

#save dataframe to csv
balt_flood.to_csv(join(FO, 'model_inputs','surge_baltimore_levee.csv'))