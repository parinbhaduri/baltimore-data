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

#using Gadfly, Cairo, Fontconfig

#image = PNG("gev_hist_balt.png",6inch,4inch)
#draw(image, dense_plot)

## Determine Return Levels from GEV 
return_periods = collect(range(10,1000,step=10))

return_levels = [returnlevel.(Ref(fm), rp).value[] for rp in return_periods]

using Plots

ret_level_plt = plot(return_periods, return_levels, legend = false)
xaxis!(ret_level_plt, "Return period (yrs^-1)")
yaxis!(ret_level_plt, "Return level (meters)")


##Create histogram to see what bins GEV samples would fill
GEV_d = GeneralizedExtremeValue(location(fm)[1], Extremes.scale(fm)[1], shape(fm)[1])

#Sample from GEV and return flood depth 

function GEV_event(rng;
    d = GEV_d) #input GEV distribution 
    flood_depth = rand(rng, d)
    return flood_depth
end

gev_rng = MersenneTwister(1897)
flood_record = [GEV_event(gev_rng) for _ in 1:1000]
#Group flood depths into regular intervals
round_step(x, step) = round(x / step) * step
#flood_record = round_step.(flood_record, 0.25)

#Define Function to calculate return period from return level
function GEV_rp(z_p, mu = μ, sig = σ, xi = ξ)
    y_p = 1 + (xi * ((z_p - mu)/sig))
    rp = -exp(-y_p^(-1/xi)) + 1
    rp = round(rp, digits = 3)
    return 1/rp
end

#Convert flood intervals to corresponding return periods 
#event_rps = [GEV_rp(record, location(fm)[1], Extremes.scale(fm)[1], shape(fm)[1]) for record in flood_record]
histogram(event_rps; bins = 10:10:1000,xaxis=(:log10, (1, 1000)))

histogram(flood_record; bins = 0:0.25:4)

