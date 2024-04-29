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
filepath = joinpath(dirname(@__DIR__),"flood_inputs","NOAA_WL","bmore_monthly_mean.csv")

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

#tide_plt = @df dat plot(:datetime, [:highest :MSL], label = ["highest" "MSL"])
#yaxis!(tide_plt, "Water Level (meters)")

## Detrend to remove sea-level rise
ma_length = 13
ma_offset = Int(floor(ma_length/2))
moving_average(series, n) = [mean(@view series[i-n:i+n]) for i in n+1:length(series) - n]

dat_ma = DataFrame(datetime=dat.datetime[ma_offset+1:end-ma_offset], residual = dat.highest[ma_offset+1:end-ma_offset] .- moving_average(dat.MSL, ma_offset), MSL = dat.MSL[ma_offset+1:end-ma_offset] .- moving_average(dat.MSL, ma_offset))

#tide_plt = @df dat_ma plot(:datetime, [:residual :MSL], label = ["Observations" "De-trended MSL"])
#yaxis!(tide_plt, "Water Level (meters)")

##Fit GEV Distributions
#Calculate annual maxima
dat_ma = dropmissing(dat_ma)
dat_annmax = combine(dat_ma -> dat_ma[argmax(dat_ma.residual),:], groupby(DataFramesMeta.transform(dat_ma, :datetime => x->year.(x)), :datetime_function))

#tide_hist = @df dat_annmax histogram(:residual)

#save tide maxima to dataframe
CSV.write(joinpath(pwd(),"model_inputs/balt_tide.csv"), dat_annmax)

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

ret_level_plt = plot(return_periods, return_levels, xticks = 0:100:1000, yticks = 0:0.25:4, lw = 2.5, legend = false, dpi = 300)
xaxis!(ret_level_plt, "Return period (years)")
yaxis!(ret_level_plt, "Return level (meters)")

savefig(ret_level_plt, "ret_level_plt.png")

##Create histogram to see what bins GEV samples would fill
GEV_d = GeneralizedExtremeValue(location(fm)[1], Extremes.scale(fm)[1], shape(fm)[1])

#Sample from GEV and return flood depth 
function GEV_event(rng;
    d = GEV_d) #input GEV distribution 
    flood_depth = rand(rng, d)
    return flood_depth
end

#Group flood depths into regular intervals
round_step(x, step) = round(x / step) * step

#Define Function to calculate return period from return level
function GEV_rp(z_p, mu = μ, sig = σ, xi = ξ)
    y_p = 1 + (xi * ((z_p - mu)/sig))
    rp = -exp(-y_p^(-1/xi)) + 1
    rp = round(rp, digits = 3)
    return 1/rp
end

gev_rng = MersenneTwister(1897)
flood_record = [GEV_event(gev_rng) for _ in 1:1000]
# Sea Level Rise
#high scenario of SL change projection for 2031 is 0.28m and 2.57m for 2130 (NOAA)
high_slr = repeat([0.022 * i for i in 1:50], 20)
slr_record = flood_record .+ high_slr

#Count number of occurences of each surge event  
surge_freq = hcat([[i, count(==(i), round_step.(flood_record,0.25))] for i in unique(round_step.(flood_record,0.25))]...)
surge_freq_slr = hcat([[i, count(==(i), round_step.(slr_record,0.25))] for i in unique(round_step.(slr_record,0.25))]...)

surge_interval = bar(surge_freq[1,:], surge_freq[2,:], alpha = 0.5, label = "Surge", legend = :outerright, dpi = 300)
bar!(surge_freq_slr[1,:], surge_freq_slr[2,:], alpha = 0.5, label = "Surge w/ SLR")
#title!("Surge Frequencies at 0.25m intervals")
#savefig(surge_interval, "surge_interval.png")

xaxis!(surge_interval, "Surge Level (meters)")
yaxis!(surge_interval, "Frequency")
vline!([returnlevel(fm, 100).value[]], lw = 2.5, label = "100-Year Event")
vline!([2.804], lw = 2.5, label = "Sea Wall Height")
#title!("Surge Frequencies at 0.25m intervals")

savefig(surge_interval, "surge_interval.png")
