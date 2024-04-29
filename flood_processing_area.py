## import necessary packages
import os
import geopandas as gpd
import pandas as pd
import numpy as np
import rioxarray as rx

## Import baltimore block group geometries as geodataframe
balt_bg = gpd.read_file("model_inputs/bg_baltimore.csv", 
                        GEOM_POSSIBLE_NAMES="geometry",
                        KEEP_GEOM_COLUMNS="NO")
balt_bg = balt_bg.set_crs('epsg:3857')

#To Albers contiguous equal area
balt_bg = balt_bg.to_crs("ESRI:102003")

#Calculate BG area
balt_bg["area"] = balt_bg["geometry"].area

## Read in surge data and convert to csv
directory = "flood_inputs/FastFlood/Base"

## Extract surge level and pixel area from first file. 
file_0 = os.listdir(directory)[0]
surge_name = ""
surge_name = surge_name.join([*file_0.split('_')[2]][0:3])
surge_name = str(int(surge_name)/100)

ras = rx.open_rasterio(os.path.join(directory, file_0)).rio.reproject("ESRI:102003")

band = ras[0]
x, y, extent = band.x.values, band.y.values, band.values
x, y = np.meshgrid(x, y)
x, y, extent = x.flatten(), y.flatten(), extent.flatten()

#Convert to point geometries 
surge_area = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_xy(x, y, crs=band.rio.crs))
extent[extent > 0] = 1
surge_area[surge_name] = extent

#Get pixel area
#find pixel resolution of image and save x,y dimensions
pixelSizeX, pixelSizeY = ras.rio.resolution()
#Multiply pixel dimensions to get area of one pixel
pixel_area = abs(pixelSizeX * pixelSizeY)

# Repeat for remaining files and add to surge_depths. Create dataframe of surge depths
band_dict = {}
for filename in os.listdir(directory)[1:]:
    if filename.endswith(".tif"):
        raster = rx.open_rasterio(os.path.join(directory, filename)).rio.reproject("ESRI:102003")
        #get first band of raster
        band = raster[0]
        extent = band.values.flatten()
        extent[extent > 0] = 1

        #Extract return level from filename
        surge_name = ""
        surge_name = surge_name.join([*filename.split('_')[2]][0:3])
        surge_name = str(int(surge_name)/100)
        ##add to list
        band_dict[surge_name] = extent
    else:
        continue

band_df = pd.DataFrame.from_dict(band_dict)
surge_area = pd.concat([surge_area, band_df], axis = 1)

#join centroid geometries with block group geometries
bg_flood = gpd.sjoin(balt_bg[["GISJOIN","geometry"]], surge_area, how = 'left')

#count number of non zero surge depth pixels present in each block group
bg_flood_area = bg_flood.drop('geometry', axis = 1).groupby('GISJOIN', as_index = False).agg(lambda x: x.ne(0).sum())
bg_flood_area = bg_flood_area.drop('index_right', axis = 1)
#Rejoin block group area and fid_1
balt_flood = balt_bg[["GISJOIN","fid_1", "area"]].merge(bg_flood_area, on='GISJOIN')

#Multiply counts by pixel area. Divide flood area by BG area to get proportion of BG inundated
balt_flood.loc[:,~balt_flood.columns.isin(['GISJOIN', 'fid_1', 'area'])] = (balt_flood.loc[:,~balt_flood.columns.isin(['GISJOIN', 'fid_1', 'area'])] * pixel_area).div(balt_flood['area'], axis=0)


#Reorder columns so that surge level columns are in ascending order 
surge_cols = [float(x) for x in balt_flood.columns[3:]]
surge_cols.sort()
new_cols = ['GISJOIN'] + ['fid_1'] + ['area'] + [str(x) for x in surge_cols]
balt_flood = balt_flood[new_cols]

#save dataframe to csv
balt_flood.to_csv('model_inputs/surge_area_baltimore_base.csv')