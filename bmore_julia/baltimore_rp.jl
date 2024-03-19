import Pkg
Pkg.activate(@__DIR__)
Pkg.instantiate()

### Determine return levels by fitting GEV distribution to Baltimore tide gauge data
using Random
using Dates
using CSV
using DataFrames
using DataFramesMeta
using Distributions
using Plots
using Measures
using StatsPlots

using Extremes

Random.seed!(1);

##Load Data
filepath = joinpath(dirname(@__DIR__),"flood_inputs","bmore_monthly_mean.csv")

function load_data(fname)
    date_format = DateFormat("yyyy-mm")
    df = @chain fname begin
        CSV.File(; header = true)
        DataFrame
        #rename("MHHW" => "gauge")
        @transform :datetime = DateTime.(:year, :month)
        select(:datetime, :highest, :MSL)
    end
    return df
end

#t_dat = DataFrame(CSV.File(filepath; header = true))
dat = load_data(filepath)

tide_plt = @df dat plot(:datetime, [:highest :MSL], label = ["highest" "MSL"])
yaxis!(tide_plt, "Water Level (meters)")

## Detrend to remove sea-level rise
ma_length = 13
ma_offset = Int(floor(ma_length/2))
moving_average(series, n) = [mean(@view series[i-n:i+n]) for i in n+1:length(series) - n]

dat_ma = DataFrame(datetime=dat.datetime[ma_offset+1:end-ma_offset], residual = dat.highest[ma_offset+1:end-ma_offset] .- moving_average(dat.MSL, ma_offset), MSL = dat.MSL[ma_offset+1:end-ma_offset] .- moving_average(dat.MSL, ma_offset))

tide_plt = @df dat_ma plot(:datetime, [:residual :MSL], label = ["Observations" "De-trended MSL"])
yaxis!(tide_plt, "Water Level (meters)")

##Fit GEV Distributions
#Calculate annual maxima
dat_ma = dropmissing(dat_ma)
dat_annmax = combine(dat_ma -> dat_ma[argmax(dat_ma.residual),:], groupby(DataFramesMeta.transform(dat_ma, :datetime => x->year.(x)), :datetime_function))

tide_hist = @df dat_annmax histogram(:residual)

#Find Parameters
fm = gevfit(dat_annmax, :residual)

params(fm)

diagnosticplots(fm)

dense_plot = histplot(fm)


## Determine Return Levels from GEV 
returnlevel(fm, 100).value[]