import geopandas as gpd
import pandas as pd
import numpy as np

geo_filename = 'blck_grp_extract_prj.shp'  # accommodates census geographies in IPUMS/NHGIS and imported as QGIS Geopackage
pop_filename = 'balt_bg_population_2018.csv'  # accommodates census data in IPUMS/NHGIS and imported as csv
pop_fieldname = 'AJWME001'  # from IPUMS/NHGIS metadata
flood_filename = 'bg_perc_100yr_flood.csv'  # FEMA 100-yr flood area data (see pre_"processing/flood_risk_calcs.py")
housing_filename = 'bg_housing_1993.csv'  # housing characteristic data and other information from early 90s (for initialization)
hedonic_filename = 'simple_anova_hedonic_without_flood_bg0418.csv'  # simple ANOVA hedonic regression conducted by Alfred

bg = gpd.read_file('/data_inputs/' + geo_filename)
pop = pd.read_csv('/data_inputs/' + pop_filename)
flood = pd.read_csv('/data_inputs/' + flood_filename)
housing = pd.read_csv('/data_inputs/' + housing_filename)
hedonic = pd.read_csv('/data_inputs/' + hedonic_filename)

# join census/population data to block groups
bg = pd.merge(bg, pop[['GISJOIN', pop_fieldname]], how='left', on='GISJOIN')
bg = pd.merge(bg, flood[['GISJOIN', 'perc_fld_area']], how='left', on='GISJOIN')
bg['perc_fld_area'] = bg['perc_fld_area'].fillna(0)
bg = pd.merge(bg, housing, how='left', on='GISJOIN')

# load table with hedonic regression information for utility function
bg = pd.merge(bg, hedonic[['GISJOIN', 'N_MeanSqfeet', 'N_MeanAge', 'N_MeanNoOfStories','N_MeanFullBathNumber','N_perc_area_flood','residuals']], how='left', on='GISJOIN')

# determine relative cbd proximity and relative flood risk for input to hh utility calcs (JY consider moving into an if statement so only loads with specified utility formulation)
bg['rel_prox_cbd'] = bg['cbddist'].max() + 1 - bg['cbddist']
bg['rel_flood_risk'] = bg['perc_fld_area'].max() + 1 - bg['perc_fld_area']

        # calculate normalized values for cbd proximity and flood risk
bg['prox_cbd_norm'] = bg['rel_prox_cbd'] / bg['rel_prox_cbd'].max()
bg['flood_risk_norm'] = bg['rel_flood_risk'] / bg['rel_flood_risk'].max()

# calculate housing budget based on 1990-1993 data
bg['housing_budget_perc'] = bg['mhi1990'] / bg['salesprice1993']

# replace 0 mhi1990 values with non-zero minimum
non_zero_min = bg[(bg.mhi1990 > 0)].mhi1990.min()
bg.loc[bg['mhi1990'] == 0, 'mhi1990'] = non_zero_min

for index, row in bg.iterrows():  # JY fill in missing sales price and hedonic regression values with nearest neighbor values that have data (this can be pre-processed to save computation time)
    if np.isnan(row['salesprice1993']) or np.isnan(row['N_MeanSqfeet']):
        location = row['geometry']
        bg_subset = bg[(bg.GEOID != row['GEOID']) & (np.isfinite(bg.salesprice1993)) & (np.isfinite(bg.N_MeanSqfeet))]
        polygon_index = bg_subset.distance(location).sort_values().index[0]
        bg.at[index, 'salesprice1993'] = bg_subset.loc[[polygon_index]]['salesprice1993']
        bg.at[index, 'N_MeanSqfeet'] = bg_subset.loc[[polygon_index]]['N_MeanSqfeet']
        bg.at[index, 'N_MeanAge'] = bg_subset.loc[[polygon_index]]['N_MeanAge']
        bg.at[index, 'N_MeanNoOfStories'] = bg_subset.loc[[polygon_index]]['N_MeanNoOfStories']
        bg.at[index, 'N_MeanFullBathNumber'] = bg_subset.loc[[polygon_index]]['N_MeanFullBathNumber']
        bg.at[index, 'N_perc_area_flood'] = bg_subset.loc[[polygon_index]]['N_perc_area_flood']
        bg.at[index, 'residuals'] = bg_subset.loc[[polygon_index]]['residuals']
        bg.at[index, 'salespricesf1993'] = bg_subset.loc[[polygon_index]]['salespricesf1993']

# initialize new price for updating
bg['new_price'] = bg['salesprice1993']

#Save Dataframe to CSV File
bg.to_csv('/model_inputs/bg_baltimore.csv')