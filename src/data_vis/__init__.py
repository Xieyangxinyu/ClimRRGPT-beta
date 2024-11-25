from src.data_vis.wildfire_perimeters import analyze_wildfire_perimeters
from src.data_vis.census import analyze_census_data
from src.data_vis.climrr import *
from functools import partial

def dispatch_analyze_fn(keywords):
    dispatch_dict = {
        'Fire Weather Index (FWI) projections': ClimRRSeasonalProjectionsFWI,
        'Seasonal Temperature Maximum projections': partial(ClimRRSeasonalProjectionsTemperature, "Maximum"),
        'Seasonal Temperature Minimum projections': partial(ClimRRSeasonalProjectionsTemperature, "Minimum"),
        'Annual Temperature Maximum projections': partial(ClimRRAnnualProjectionsTemperature, "Maximum"),
        'Annual Temperature Minimum projections': partial(ClimRRAnnualProjectionsTemperature, "Minimum"),
        'Daily Precipitation Max projections': partial(ClimRRDailyProjectionsPrecipitation, "Max"),
        'Daily Precipitation Mean projections': partial(ClimRRDailyProjectionsPrecipitation, "Mean"),
        'Precipitation projections': ClimRRAnnualProjectionsPrecipitation,
        'Consecutive Dry Days projections': ClimRRAnnualProjectionsCDNP,
        'Wind Speed projections': ClimRRAnnualProjectionsWindSpeed,
        'Cooling Degree Days projections': ClimRRAnnualProjectionsCoolingDegreeDays,
        'Heating Degree Days projections': ClimRRAnnualProjectionsHeatingDegreeDays,
        'Census data': analyze_census_data,
        'Recent Fire Perimeters data': analyze_wildfire_perimeters
    }
    analyze_fn_dict = {}
    for keyword in keywords:
        if 'projections' in keyword:
            analyze_fn_dict[keyword] = dispatch_dict[keyword]().analyze
        else:
            analyze_fn_dict[keyword] = dispatch_dict[keyword]
    return analyze_fn_dict