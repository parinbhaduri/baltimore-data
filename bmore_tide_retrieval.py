from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

import async_retriever as ar


station_id = "8574680"
start = pd.to_datetime("1902-01-01")
end = pd.to_datetime("2023-12-01")

url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

kwd = {
    "params": {
        "product": "monthly_mean",
        "application": "parin_cornell",
        "begin_date": f'{start.strftime("%Y%m%d")}',
        "end_date": f'{end.strftime("%Y%m%d")}',
        "datum": "MSL",
        "station": f"{station_id}",
        "time_zone": "GMT",
        "units": "metric",
        "format": "json",
    }
}

resp = ar.retrieve([url], "json", request_kwds=[kwd])
wl = pd.DataFrame.from_dict(resp[0]["data"])
wl.attrs = resp[0]["metadata"]

wl.to_csv('flood_inputs/bmore_monthly_mean.csv')