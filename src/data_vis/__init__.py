from src.data_vis.wildfire_perimeters import analyze_wildfire_perimeters
from src.data_vis.census import analyze_census_data
from src.data_vis.climrr import ClimRRSeasonalProjectionsFWI

class DataVisualizerDispatcher():
    def __init__(self):
        self.dispatch_dict = {
            'Fire Weather Index (FWI) projections': ClimRRSeasonalProjectionsFWI
        }

    def dispatch_analyze_fn(self, keywords):
        analyze_fn_dict = {}
        for keyword in keywords:
            analyze_fn_dict[keyword] = self.dispatch_dict[keyword]()
        return analyze_fn_dict