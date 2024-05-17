###Aggregate ddf damage files to block group scale###
from os.path import join
from pathlib import Path
import pandas as pd

FO = Path().absolute()
fd_bg = pd.read_parquet(join(FO, 'model_inputs','ddfs','base_df.pqt')).set_index('fd_id')
ens_agg_df = pd.read_parquet(join(FO, 'model_inputs','ddfs','ensemble_agg.pqt'))

#join two dataframe on fd_id
ens_agg_df = ens_agg_df.join(fd_bg[['bg_id']])
#Group on block group. Combine through summation
ens_agg_df = ens_agg_df.groupby('bg_id').sum()

#Save to csv file
ens_agg_df.to_csv(join(FO, 'model_inputs','ddfs','ens_agg_bg.csv'))