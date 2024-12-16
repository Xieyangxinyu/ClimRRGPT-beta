from abc import ABC, abstractmethod
import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
import base64
from src.utils import load_config
from src.data_vis.climrr_utils import convert_to_dataframe, categorize_fwi, fwi_color
import plotly.io as pio
import contextily as ctx

config = load_config('src/data_vis/climrr.yml')

class DataVisualizer(ABC):
    def __init__(self, keyword):
        self.keyword = keyword
        self.data_info = config[keyword]
        self.path = self.data_info['path']
        self.values_of_interests = self.data_info['values_of_interests']
        self.df = self.initialize_data()
        self.min_value = self.df[self.values_of_interests].min().min()
        self.max_value = self.df[self.values_of_interests].max().max()
        self.color_scale = self.create_color_scale()
        # save visual data for multimodal analysis
        self.plots = []

    def initialize_data(self):
        df = pd.read_csv(self.path)
        return df[self.values_of_interests + ['Crossmodel']]

    @abstractmethod
    def create_color_scale(self):
        pass

    def get_color(self, value):
        normalized_value = (value - self.min_value) / (self.max_value - self.min_value)
        return mcolors.rgb2hex(self.color_scale(normalized_value))

    def map_comparing_period(self, crossmodels, df, season='spring', scenario='45', add_legend=True):
        periods = self.data_info['periods']
        captions = ["Historical", "Mid-century", "End-century"]
        cols = st.columns(len(periods))
        for i, period in enumerate(periods):
            with cols[i]:
                m = self.get_map(crossmodels, df, period, season)
                st.caption(captions[i])
                st_folium(m, width=450, height=450, key=f"{self.keyword}_{season}_{period}_{scenario}")
        if add_legend:
            self.add_legend()

    def map_comparing_period_by_choosing_season(self, crossmodels, df, scenario='45', add_legend=True):
        custom_css = """
            <style>
            div[role="radiogroup"] label:nth-child(1) span {color: #4CAF50;}  /* spring */
            div[role="radiogroup"] label:nth-child(2) span {color: #FFC107;}  /* summer */
            div[role="radiogroup"] label:nth-child(3) span {color: #FF9800;}  /* autumn */
            div[role="radiogroup"] label:nth-child(4) span {color: #2196F3;}  /* winter */
            </style>
        """

        # Inject custom CSS
        st.markdown(custom_css, unsafe_allow_html=True)
        season = st.radio('Select Season:', ['spring', 'summer', 'autumn', 'winter'], horizontal=True, key = f"{self.keyword}_season")
        self.map_comparing_period(crossmodels, df, season, scenario=scenario, add_legend=add_legend)

    def map_comparing_season_by_choosing_period(self, crossmodels, df):
        period = st.radio('Select Time Period:', self.data_info['periods'], horizontal=True, key = f"{self.keyword}_period")
        seasons = ['spring', 'summer', 'autumn', 'winter']
        cols = st.columns(4, gap="small")
        for i, season in enumerate(seasons):
            with cols[i]:
                m = self.get_map(crossmodels, df, period, season)
                st.caption(season)
                st_folium(m, width=350, height=450, key=f"{self.keyword}_{season}_{period}_2")
        self.add_legend()

    def analyze(self, crossmodels):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])
        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)
        
        if self.data_info.get('season', False):
            return self.analyze_seasonal(crossmodels, df)
        else:
            return self.analyze_annual(crossmodels, df)
        

    def analyze_seasonal(self, crossmodels, df):
        climate_scenarios = False
        if sum(df.columns.str.contains('45')) > 0 and sum(df.columns.str.contains('85')) > 0:
            climate_scenarios = True

        if climate_scenarios:
            st.header("Time Period Comparison")
            columns_45 = [col for col in df.columns if '45' in col]
            st.header("RCP 4.5 Scenario")
            self.map_comparing_period_by_choosing_season(crossmodels, df[['Crossmodel', 'hist'] + columns_45], scenario='45', add_legend=False)
            st.header("RCP 8.5 Scenario")
            self.map_comparing_period_by_choosing_season(crossmodels, df.drop(columns=columns_45), scenario='85')

        else:   
            st.header("Time Period & Seasonal Comparison")
            self.map_comparing_period_by_choosing_season(crossmodels, df)
            self.map_comparing_season_by_choosing_period(crossmodels, df)
        
        # remove 'projections' from the keyword
        title = self.keyword.replace(' projections', '')
        st.header(f"{title} Meta-Analysis")
        mean, std = self.calculate_statistics(df)
        figs = self.create_plots(mean)
        return self.display_results(mean, std, figs)

    def analyze_annual(self, crossmodels, df):
        # check if there are two climate scenarios in the df.columns
        climate_scenarios = False
        if sum(df.columns.str.contains('45')) > 0 and sum(df.columns.str.contains('85')) > 0:
            climate_scenarios = True
        
        st.header("Time Period Comparison")

        if climate_scenarios:
            columns_45 = [col for col in df.columns if '45' in col]
            st.header("RCP 4.5 Scenario")
            self.map_comparing_period(crossmodels, df[['Crossmodel', 'hist'] + columns_45], scenario='45', add_legend=False)
            st.header("RCP 8.5 Scenario")
            self.map_comparing_period(crossmodels, df.drop(columns=columns_45), scenario='85')
        else:
            self.map_comparing_period(crossmodels, df)
        st.header(f"{self.keyword} Meta-Analysis")
        mean, std = self.calculate_statistics(df)
        fig = self.create_plot(mean)
        return self.display_results(mean, std, fig)

    def calculate_statistics(self, df):
        df = df.drop(columns='Crossmodel')
        return df.mean(), df.std()

    @abstractmethod
    def get_map(self, crossmodels, df, period, season):
        pass

    @abstractmethod
    def add_legend(self):
        pass

    def create_plots(self, mean):
        pass

    def create_plot(self, mean):
        pass

    @abstractmethod
    def display_results(self, mean, std, figs):
        pass

    def get_messages(self, table):
        table = pd.DataFrame(table)
        prompt = self.data_info['prompt'].format(table_markdown = table.to_markdown(), table_json = table.to_json())
        messages = [{'role': 'system', 'content': "You are a helpful assistant that interprets climate data and relates it to specific user goals."},
                     {'role': 'user', 'content': prompt}]
        return messages

    def get_coding_messages(self, table):
        table = pd.DataFrame(table)
        prompt = self.data_info['coding_prompt'].format(table_markdown = table.to_markdown())
        messages = [{'role': 'system', 'content': "You are a helpful assistant that interprets climate data and relates it to specific user goals."},
                     {'role': 'user', 'content': prompt}]
        return messages

    def plots_to_base64(self):
        plots = []
        for plot in self.plots:
            # Convert the plot to an image in memory.
            image_bytes = pio.to_image(plot, format='png')

            # Encode these bytes in base64
            base64_bytes = base64.b64encode(image_bytes)
            base64_string = base64_bytes.decode('utf8')
            plots.append(base64_string)
        self.plots = plots


class ClimRRSeasonalProjectionsFWI(DataVisualizer):
    def __init__(self):
        super().__init__('Fire Weather Index (FWI) projections')

    def create_color_scale(self):
        # FWI uses a custom color scale, so we'll return None here
        return None

    @staticmethod
    def fwi_color_plt(value):
        fwi_class_colors = {
            'Low': (1.0, 1.0, 0.0, 0.5),  # Yellow with 50% transparency
            'Medium': (1.0, 0.8, 0.0, 0.5),  # Orange with 50% transparency
            'High': (1.0, 0.6, 0.0, 0.5),  # Darker orange with 50% transparency
            'Very High': (1.0, 0.4, 0.0, 0.5),  # Even darker orange with 50% transparency
            'Extreme': (1.0, 0.2, 0.0, 0.5),  # Red with 50% transparency
            'Very Extreme': (1.0, 0.0, 0.0, 0.5)  # Dark red with 50% transparency
        }
        return fwi_class_colors[categorize_fwi(value)]

    def get_map(self, crossmodels, df, period, season='spring'):
        season_columns = [col for col in df.columns if season in col and period in col]
        season_fwi_df = df[['Crossmodel'] + season_columns]
        col_name = season_columns[0]
        season_fwi_df.loc[:, 'class'] = season_fwi_df[col_name].apply(categorize_fwi)

        fwi_df_geo = gpd.GeoDataFrame(crossmodels.merge(season_fwi_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(fwi_df_geo,
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name, 'class'], aliases=['Crossmodel', 'FWI', 'class']),
                style_function=lambda x: {'fillColor': fwi_color(x['properties'][col_name]),
                                          'color': fwi_color(x['properties'][col_name])})
        )

        # fwi_df_geo['color'] = fwi_df_geo[col_name].apply(self.fwi_color_plt)
        # fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        #
        # # set alpha channels from 0.5 to 1 for all colors in fwi_df_geo['color']
        # color4llava = fwi_df_geo['color'].apply(lambda x: (x[0], x[1], x[2], 1.0))
        # # increase color contrast
        # color4llava = color4llava.apply(lambda x: (x[0] * 0.8, x[1] * 0.8, x[2] * 0.8, x[3]))
        # fwi_df_geo.plot(
        #     ax=ax,
        #     color=color4llava,  # Use the computed colors
        #     edgecolor='black',  # Outline color for the polygons
        #     legend=True  # Optional: Add a legend if needed
        # )
        #
        # # optionally, add background map
        # # ctx.add_basemap(ax, crs=fwi_df_geo.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
        #
        # # capitalize the first letter of the season
        # ax.set_title('FWI Map ' + period.capitalize() + ' ' + season.capitalize())
        # fig.savefig('spatial_plots/fwi_map_' + period + '_' + season + '.png', dpi=300, bbox_inches='tight')
        return m

    def add_legend(self):
        """Adds a custom legend with colors for FWI to a Folium map."""
        legend_html = """
        <div style="
                    bottom: 5px; left: 5px; width: auto; height: 50px; 
                    border:1px solid grey; z-index:9999; font-size:12px;
                    background: white; opacity: 0.9; padding: 2px; color: black; display: flex; align-items: center;justify-content: center;">
        <i style="background:rgb(255, 255, 0, 0.5); width: 24px; height: 24px;"></i> &nbsp; Low &nbsp;|&nbsp;
        <i style="background:rgb(255, 204, 0, 0.5); width: 24px; height: 24px;"></i> &nbsp; Medium &nbsp;|&nbsp;
        <i style="background:rgb(255, 153, 0, 0.5); width: 24px; height: 24px;"></i> &nbsp; High &nbsp;|&nbsp;
        <i style="background:rgb(255, 102, 0, 0.5); width: 24px; height: 24px;"></i> &nbsp; Very High &nbsp;|&nbsp;
        <i style="background:rgb(255, 51, 0, 0.5); width: 24px; height: 24px;"></i> &nbsp; Extreme &nbsp;|&nbsp;
        <i style="background:rgb(255, 0, 0, 0.5); width: 24px; height: 24px;"></i> &nbsp; Very Extreme
        </div>
        """
        # write in the middle of the page
        st.write(legend_html, unsafe_allow_html=True)

    def create_plot(self, mean):
        pass

    def create_plots(self, mean):
        table = pd.DataFrame(mean.values.reshape(4, 3), 
                             columns=self.data_info['periods'], 
                             index=['spring', 'summer', 'autumn', 'winter'])
        
        fig1 = px.line(table.T, title='Mean FWI Across Seasons and Time Periods', 
                       labels={'value': 'FWI', 'index': 'Time Period'},
                       color_discrete_map={'spring': '#4CAF50', 'summer': '#FFC107', 
                                           'autumn': '#FF9800', 'winter': '#2196F3'})
        
        fig2 = px.line(table, title='Mean FWI Values Across Seasons and Time Periods',
                       labels={'value': 'FWI Value', 'index': 'Season'},
                       color_discrete_map={'Hist': '#4CAF50', 'Midc': '#FFC107', 'Endc': '#FF9800'})
        
        for fig in [fig1, fig2]:
            fig.update_layout(legend_title_text='', legend=dict(traceorder='normal'),
                              plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')

        self.plots = [fig1, fig2]
        self.plots_to_base64()
        return [fig1, fig2]

    def display_results(self, mean, std, figs):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            for fig in figs:
                st.plotly_chart(fig, use_container_width=True)
            st.write("These charts illustrate the trends in mean FWI values across seasons and time periods.")

        with col1:
            table = pd.DataFrame(mean.values.reshape(4, 3), 
                                 columns=self.data_info['periods'], 
                                 index=['spring', 'summer', 'autumn', 'winter'])
            std_table = pd.DataFrame(std.values.reshape(4, 3), 
                                     columns=self.data_info['periods'], 
                                     index=['spring', 'summer', 'autumn', 'winter'])
            
            display_table = table.map(lambda x: f"{x:.2f}") + ' (' + std_table.map(lambda x: f"{x:.2f}") + ')'
            
            st.caption("Mean FWI Values (Std Dev)")
            st.dataframe(display_table, use_container_width=True)
            st.write("This table presents the mean FWI values for each season and time period, with standard deviations in parentheses.")
            
            st.caption("FWI Classification")
            data = {
                'FWI Class': ['Low', 'Medium', 'High', 'Very High', 'Extreme', 'Very Extreme'],
                'FWI Values': ['0-9', '9-21', '21-34', '34-39', '39-53', 'Above 53']
            }
            st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)
            st.write("This table shows the classification of FWI values into risk categories.")    
            display_table = display_table + ' ' + table.map(categorize_fwi)

        messages = self.get_messages(display_table.transpose())
        code_messages = self.get_coding_messages(display_table.transpose())
        return col3, messages, code_messages, self.plots


class ClimRRAnnualClimateScenarios(DataVisualizer):
    def __init__(self, keyword):
        super().__init__(keyword)

    def get_map(self, crossmodels, df, period, season = 'spring', label = 'Consecutive Days with No Precipitation'):
        columns = [col for col in df.columns if period in col]
        cdnp_df = df[['Crossmodel'] + columns]
        col_name = columns[0]

        cdnp_df_geo = gpd.GeoDataFrame(crossmodels.merge(cdnp_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(cdnp_df_geo, 
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name], 
                                                       aliases=['Crossmodel', label]),
                style_function=lambda x: {'fillColor': self.get_color(x['properties'][col_name]), 
                                          'color': 'black', 
                                          'weight': 1, 
                                          'fillOpacity': 0.7})
        )
        return m

    def add_legend(self, lable='Consecutive Days with No Precipitation'):
        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)

        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=self.color_scale), 
                          cax=ax, orientation='horizontal', label=lable)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        
        data = base64.b64encode(buf.getbuffer()).decode("utf8")
        
        legend_html = f"""
        <div style="text-align:center;">
            <img src="data:image/png;base64,{data}" style="max-width:100%">
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)
    

    def create_plot(self, mean, col_label, label_with_metric, title):
        mean = mean.reset_index()
        # Convert the Series to a DataFrame and rename columns
        mean.columns = ['Time Period', col_label]

        # Add a Scenario column based on the 'Time Period' values
        def determine_scenario(period):
            if '45' in period:
                return 'RCP 4.5'
            elif '85' in period:
                return 'RCP 8.5'
            else:
                return 'Historical'

        mean['Scenario'] = mean['Time Period'].apply(determine_scenario)

        # Clean up the Time Period names for better display
        mean['Time Period'] = mean['Time Period'].replace({
            'hist': 'Historical',
            'rcp45_midc': 'Mid-Century',
            'rcp85_midc': 'Mid-Century',
            'rcp45_endc': 'End-Century',
            'rcp85_endc': 'End-Century'
        })

        # Duplicate the historical data for both scenarios to show as the starting point
        historical_row = mean[mean['Scenario'] == 'Historical']
        historical_row_45 = historical_row.copy()
        historical_row_85 = historical_row.copy()

        historical_row_45['Scenario'] = 'RCP 4.5'
        historical_row_85['Scenario'] = 'RCP 8.5'

        # Combine historical data with the scenarios
        mean = pd.concat([historical_row_45, historical_row_85, mean[mean['Scenario'] != 'Historical']])

        # Explicitly set the order of the x-axis (Time Period)
        time_order = ['Historical', 'Mid-Century', 'End-Century']
        mean['Time Period'] = pd.Categorical(mean['Time Period'], categories=time_order, ordered=True)

        # Create the line plot
        fig = px.line(
            mean,
            x='Time Period',
            y=col_label,
            color='Scenario',
            title=f'{title} Across Time Periods',
            labels={col_label: label_with_metric, 'Time Period': 'Time Period'},
            color_discrete_map={'Historical': '#000000', 'RCP 4.5': '#FFA500', 'RCP 8.5': '#1f77b4'}
        )

        # Update layout for better visualization
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title='Time Period',
            yaxis_title=label_with_metric,
            xaxis=dict(tickangle=-45)  # Rotate x-axis labels for better readability
        )

        return fig
    
    def display_results(self, mean, std, fig, label, label_with_metric, metric):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write(f"This chart illustrates the trends in {label} across the three time periods.")

        with col1:
            table = pd.DataFrame(mean).T
            table.index = ['Annual']
            std_table = pd.DataFrame(std).T
            std_table.index = ['Annual']

            # Separate the historical data
            table_hist = table.loc[:, table.columns.str.contains('hist')]
            std_table_hist = std_table.loc[:, std_table.columns.str.contains('hist')]

            # Create separate tables for RCP 4.5 and RCP 8.5
            table_45 = pd.concat([table_hist, table.loc[:, table.columns.str.contains('45')]], axis=1)
            table_85 = pd.concat([table_hist, table.loc[:, table.columns.str.contains('85')]], axis=1)

            std_table_45 = pd.concat([std_table_hist, std_table.loc[:, std_table.columns.str.contains('45')]], axis=1)
            std_table_85 = pd.concat([std_table_hist, std_table.loc[:, std_table.columns.str.contains('85')]], axis=1)

            # Format the display tables
            display_table_45 = table_45.map(lambda x: f"{x:.2f}") + ' (' + std_table_45.map(lambda x: f"{x:.2f}") + ')'
            display_table_85 = table_85.map(lambda x: f"{x:.2f}") + ' (' + std_table_85.map(lambda x: f"{x:.2f}") + ')'

            # Display the tables using Streamlit
            st.caption(f"{label_with_metric} (Std Dev) - RCP 4.5")
            st.dataframe(display_table_45, use_container_width=True)

            st.caption(f"{label_with_metric} (Std Dev) - RCP 8.5")
            st.dataframe(display_table_85, use_container_width=True)

            st.write(f"These tables present the {label} values for each time period and scenario, with standard deviations in parentheses.")

            st.caption(f"{label_with_metric} Range")
            st.write(f"Minimum: {self.min_value:.2f} {metric}")
            st.write(f"Maximum: {self.max_value:.2f} {metric}")
            st.write(f"This shows the range of {label} values in the dataset.")

        messages = self.get_messages(table)

        return col3, messages, self.plots
    
    
class ClimRRAnnualProjectionsPrecipitation(ClimRRAnnualClimateScenarios):
    def __init__(self):
        super().__init__('Precipitation projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('YlGnBu')

    def get_map(self, crossmodels, df, period, season='spring'):
        return super().get_map(crossmodels, df, period, label='Precipitation (mm)')

    def add_legend(self):
        return super().add_legend(lable='Precipitation (mm)')

    def create_plot(self, mean, col_label='Precipitation', label_with_metric='Precipitation (mm)', title='Total Annual Precipitation'):
        return super().create_plot(mean, col_label, label_with_metric, title)

    def display_results(self, mean, std, fig):
        return super().display_results(mean, std, fig, 'total annual precipitation', 'Total Annual Precipitation (mm)', 'mm')

class ClimRRAnnualProjectionsTemperature(ClimRRAnnualClimateScenarios):
    def __init__(self, temp_type):
        self.temp_type = temp_type
        super().__init__(f'Annual Temperature {temp_type} projections')
    
    def create_color_scale(self):
        return plt.cm.get_cmap('RdYlBu_r') # Red (hot) to Blue (cold) color scale
    
    def get_map(self, crossmodels, df, period, season='spring'):
        return super().get_map(crossmodels, df, period, label=f'{self.temp_type} Temperature (°F)')
    
    def add_legend(self):
        return super().add_legend(lable=f'{self.temp_type} Temperature (°F)')
    
    def create_plot(self, mean):
        return super().create_plot(mean, f'{self.temp_type} Temperature', f'{self.temp_type} Temperature (°F)', f'Mean {self.temp_type} Temperature')
    
    def display_results(self, mean, std, fig):
        return super().display_results(mean, std, fig, f'mean {self.temp_type} temperature', f'Mean {self.temp_type} Temperature (°F)', '°F')
        
class ClimRRAnnualProjectionsCDNP(ClimRRAnnualClimateScenarios):
    def __init__(self):
        super().__init__('Consecutive Dry Days projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('YlOrBr')

    def get_map(self, crossmodels, df, period, season='spring'):
        return super().get_map(crossmodels, df, period, label='Consecutive Days with No Precipitation')

    def add_legend(self, lable='Consecutive Days with No Precipitation'):
        return super().add_legend(lable)
    
    def create_plot(self, mean):
        return super().create_plot(mean, 'Consecutive Days with No Precipitation', 'Consecutive Days with No Precipitation', 'Consecutive Days with No Precipitation')

    def display_results(self, mean, std, fig):
        return super().display_results(mean, std, fig, 'consecutive dry days', 'Consecutive Dry Days', 'days')


class ClimRRAnnualProjectionsWindSpeed(ClimRRAnnualClimateScenarios):
    def __init__(self):
        super().__init__('Wind Speed projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('YlGnBu')

    def get_map(self, crossmodels, df, period, season='spring'):
        columns = [col for col in df.columns if period in col]
        windspeed_df = df[['Crossmodel'] + columns]
        col_name = columns[0]

        windspeed_df_geo = gpd.GeoDataFrame(crossmodels.merge(windspeed_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(windspeed_df_geo, 
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name], 
                                                       aliases=['Crossmodel', 'Wind Speed (m/s)']),
                style_function=lambda x: {'fillColor': self.get_color(x['properties'][col_name]), 
                                          'color': 'black', 
                                          'weight': 1, 
                                          'fillOpacity': 0.7})
        )
        return m

    def add_legend(self):
        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)

        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=self.color_scale), 
                          cax=ax, orientation='horizontal', label='Wind Speed (m/s)')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        
        data = base64.b64encode(buf.getbuffer()).decode("utf8")
        
        legend_html = f"""
        <div style="text-align:center;">
            <img src="data:image/png;base64,{data}" style="max-width:100%">
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)

    def create_plot(self, mean):
        return super().create_plot(mean, 'Wind Speed', 'Wind Speed (m/s)', 'Mean Annual Wind Speed')

    def display_results(self, mean, std, fig):
        return super().display_results(mean, std, fig, 'mean annual wind speed', 'Mean Annual Wind Speed (m/s)', 'm/s')


class ClimRRAnnualProjectionsCoolingDegreeDays(DataVisualizer):
    def __init__(self):
        super().__init__('Cooling Degree Days projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('YlOrRd')  # Yellow to Orange to Red color scale

    def get_map(self, crossmodels, df, period, season='spring'):
        # For CDD, we don't use seasons, so we ignore the season parameter
        columns = [col for col in df.columns if period in col]
        cdd_df = df[['Crossmodel'] + columns]
        col_name = columns[0]

        cdd_df_geo = gpd.GeoDataFrame(crossmodels.merge(cdd_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(cdd_df_geo, 
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name], 
                                                    aliases=['Crossmodel', 'Cooling Degree Days']),
                style_function=lambda x: {'fillColor': self.get_color(x['properties'][col_name]), 
                                        'color': 'black', 
                                        'weight': 1, 
                                        'fillOpacity': 0.7})
        )
        return m

    def add_legend(self):
        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)

        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=self.color_scale), 
                          cax=ax, orientation='horizontal', label='Cooling Degree Days')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        
        data = base64.b64encode(buf.getbuffer()).decode("utf8")
        
        legend_html = f"""
        <div style="text-align:center;">
            <img src="data:image/png;base64,{data}" style="max-width:100%">
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)

    def create_plot(self, mean):
        table = pd.DataFrame(mean).T
        table.index = ['Annual']
        
        fig = px.bar(table.T, title='Cooling Degree Days Comparison', 
                     labels={'value': 'Cooling Degree Days', 'index': 'Time Period'},
                     color_discrete_sequence=['#FFA500', '#FF4500'])  # Orange for historical, Red-Orange for future

        fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        self.plots = [fig]
        self.plots_to_base64()
        return fig

    def display_results(self, mean, std, fig):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write("This chart compares Cooling Degree Days between historical data and mid-century projections.")

        with col1:
            table = pd.DataFrame(mean).T
            table.index = ['Annual']
            std_table = pd.DataFrame(std).T
            std_table.index = ['Annual']
            
            display_table = table.map(lambda x: f"{x:.2f}") + ' (' + std_table.map(lambda x: f"{x:.2f}") + ')'
            
            st.caption("Mean Annual Cooling Degree Days (Std Dev)")
            st.dataframe(display_table, use_container_width=True)
            st.write("This table presents the mean annual Cooling Degree Days for historical and mid-century periods, with standard deviations in parentheses.")

            st.caption("Cooling Degree Days Range")
            st.write(f"Minimum: {self.min_value:.2f}")
            st.write(f"Maximum: {self.max_value:.2f}")
            st.write("This shows the range of Cooling Degree Days in the dataset.")
        
        messages = self.get_messages(table)
        return col3, messages, self.plots

    def analyze(self, crossmodels):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])
        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)
        
        st.header("Time Period Comparison")
        self.map_comparing_period(crossmodels, df)
        
        st.header("Cooling Degree Days Meta-Analysis")
        mean, std = self.calculate_statistics(df)
        fig = self.create_plot(mean)
        return self.display_results(mean, std, fig)

    def calculate_statistics(self, df):
        df = df.drop(columns='Crossmodel')
        return df.mean(), df.std()


class ClimRRAnnualProjectionsHeatingDegreeDays(DataVisualizer):
    def __init__(self):
        super().__init__('Heating Degree Days projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('YlGnBu')  # Yellow to Green to Blue color scale

    def get_map(self, crossmodels, df, period, season='spring'):
        # For HDD, we don't use seasons, so we ignore the season parameter
        columns = [col for col in df.columns if period in col]
        hdd_df = df[['Crossmodel'] + columns]
        col_name = columns[0]

        hdd_df_geo = gpd.GeoDataFrame(crossmodels.merge(hdd_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(hdd_df_geo, 
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name], 
                                                    aliases=['Crossmodel', 'Heating Degree Days']),
                style_function=lambda x: {'fillColor': self.get_color(x['properties'][col_name]), 
                                        'color': 'black', 
                                        'weight': 1, 
                                        'fillOpacity': 0.7})
        )
        return m

    def add_legend(self):
        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)

        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=self.color_scale), 
                          cax=ax, orientation='horizontal', label='Heating Degree Days')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        
        data = base64.b64encode(buf.getbuffer()).decode("utf8")
        
        legend_html = f"""
        <div style="text-align:center;">
            <img src="data:image/png;base64,{data}" style="max-width:100%">
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)

    def create_plot(self, mean):
        table = pd.DataFrame(mean).T
        table.index = ['Annual']
        
        fig = px.bar(table.T, title='Heating Degree Days Comparison',
                        labels={'value': 'Heating Degree Days', 'index': 'Time Period'},
                        color_discrete_sequence=['#4682B4', '#4682B4'])

        fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        self.plots = [fig]
        self.plots_to_base64()
        return fig

    def display_results(self, mean, std, fig):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write("This chart illustrates the trend in Heating Degree Days across the time periods.")

        with col1:
            table = pd.DataFrame(mean).T
            table.index = ['Annual']
            std_table = pd.DataFrame(std).T
            std_table.index = ['Annual']
            
            display_table = table.map(lambda x: f"{x:.2f}") + ' (' + std_table.map(lambda x: f"{x:.2f}") + ')'
            
            st.caption("Mean Annual Heating Degree Days (Std Dev)")
            st.dataframe(display_table, use_container_width=True)
            st.write("This table presents the mean annual Heating Degree Days for each time period, with standard deviations in parentheses.")

            st.caption("Heating Degree Days Range")
            st.write(f"Minimum: {self.min_value:.2f}")
            st.write(f"Maximum: {self.max_value:.2f}")
            st.write("This shows the range of Heating Degree Days in the dataset.")

        messages = self.get_messages(table)
        return col3, messages, self.plots

    def analyze(self, crossmodels):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])
        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)
        
        st.header("Time Period Comparison")
        self.map_comparing_period(crossmodels, df)
        
        st.header("Heating Degree Days Meta-Analysis")
        mean, std = self.calculate_statistics(df)
        fig = self.create_plot(mean)
        return self.display_results(mean, std, fig)

    def calculate_statistics(self, df):
        df = df.drop(columns='Crossmodel')
        return df.mean(), df.std()


class ClimRRSeasonalProjections(DataVisualizer):
    def __init__(self, keyword):
        super().__init__(keyword)
        self.seasons = ['spring', 'summer', 'autumn', 'winter']

    @abstractmethod
    def create_color_scale(self):
        pass

    def get_map(self, crossmodels, df, period, season='spring', label=None):
        season_columns = [col for col in df.columns if season in col and period in col]
        season_temp_df = df[['Crossmodel'] + season_columns]
        col_name = season_columns[0]

        temp_df_geo = gpd.GeoDataFrame(crossmodels.merge(season_temp_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(temp_df_geo, 
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name], 
                                                    aliases=['Crossmodel', label]),
                style_function=lambda x: {'fillColor': self.get_color(x['properties'][col_name]), 
                                        'color': self.get_color(x['properties'][col_name])})
        )
        return m
    
    def add_legend(self, label):
        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)

        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=self.color_scale), 
                          cax=ax, orientation='horizontal', label=label)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        
        data = base64.b64encode(buf.getbuffer()).decode("utf8")
        
        legend_html = f"""
        <div style="text-align:center;">
            <img src="data:image/png;base64,{data}" style="max-width:100%">
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)

    def create_plots(self, mean, title, label):
        table = pd.DataFrame(mean.values.reshape(4, 3), 
                             columns=self.data_info['periods'], 
                             index=self.seasons)
        
        fig1 = px.line(table.T, title=f'{title} Across Seasons and Time Periods', 
                       labels={'value': label, 'index': 'Time Period'},
                       color_discrete_map={'spring': '#4CAF50', 'summer': '#FFC107', 
                                           'autumn': '#FF9800', 'winter': '#2196F3'})
        
        fig2 = px.line(table, title=f'{title} Values Across Seasons and Time Periods',
                       labels={'value': label, 'index': 'Season'},
                       color_discrete_map={'hist': '#4CAF50', 'midc': '#FFC107', 'endc': '#FF9800'})
        
        for fig in [fig1, fig2]:
            fig.update_layout(legend_title_text='', legend=dict(traceorder='normal'),
                              plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')

        self.plots = [fig1, fig2]
        self.plots_to_base64()
        return [fig1, fig2]
        
    def display_results(self, mean, std, figs, title, label, metric):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            for fig in figs:
                st.plotly_chart(fig, use_container_width=True)
            st.write(f"These charts illustrate the trends in {title} values across seasons and time periods.")

        with col1:
            table = pd.DataFrame(mean.values.reshape(4, 3), 
                                 columns=self.data_info['periods'], 
                                 index=self.seasons)
            std_table = pd.DataFrame(std.values.reshape(4, 3), 
                                     columns=self.data_info['periods'], 
                                     index=self.seasons)
            
            display_table = table.map(lambda x: f"{x:.2f}") + ' (' + std_table.map(lambda x: f"{x:.2f}") + ')'
            
            st.caption(f"{title} Values (Std Dev)")
            st.dataframe(display_table, use_container_width=True)
            st.write(f"This table presents the mean {title} values for each season and time period, with standard deviations in parentheses.")
            
            st.caption(f"{label} Range")
            st.write(f"Minimum: {self.min_value:.2f} {metric}")
            st.write(f"Maximum: {self.max_value:.2f} {metric}")
            st.write(f"This shows the range of {label} values in the dataset.")

        messages = self.get_messages(display_table.transpose())
        return col3, messages, self.plots
    

    def calculate_statistics(self, df):
        df = df.drop(columns='Crossmodel')
        return df.mean(), df.std()
    
    def analyze(self, crossmodels, label):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])
        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)

        st.header("Time Period & Seasonal Comparison")
        st.write(f"""
            This section allows you to compare {label} values for a specific season across three time periods:
            historical, mid-century, and end-century.
            Use the radio buttons below to select a season and observe how {label} is projected to change over time.
        """)
        self.map_comparing_period_by_choosing_season(crossmodels, df, add_legend=False)
        st.write(f"""
            Use the radio buttons to select a time period and observe how {label} varies by season.
            """)
        self.map_comparing_season_by_choosing_period(crossmodels, df)
        
        st.header(f"{label} Meta-Analysis")
        st.write(f"""
            This section provides a statistical overview of the {label} values across all time periods.
            It includes line charts showing trends over time and tables with detailed numerical data.
        """)

        mean, std = self.calculate_statistics(df)
        figs = self.create_plots(mean)
        return self.display_results(mean, std, figs)



class ClimRRSeasonalProjectionsTemperature(ClimRRSeasonalProjections):
    def __init__(self, temp_type):
        self.temp_type = temp_type  # 'Maximum' or 'Minimum'
        super().__init__(f'Seasonal Temperature {temp_type} projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('RdYlBu_r')  # Red (hot) to Blue (cold) color scale

    def get_map(self, crossmodels, df, period, season='spring'):
        return super().get_map(crossmodels, df, period, label=f'{self.temp_type} Temperature (°F)')

    def add_legend(self):
        return super().add_legend(f'{self.temp_type} Temperature (°F)')

    def create_plots(self, mean):
        return super().create_plots(mean, f'Mean {self.temp_type} Temperature', f'Temperature (°F)')

    def display_results(self, mean, std, figs):
        return super().display_results(mean, std, figs, f'Mean {self.temp_type} Temperature', f'{self.temp_type} Temperature', '°F')

    def analyze(self, crossmodels):
        return super().analyze(crossmodels, f'{self.temp_type} Temperature')

class ClimRRDailyProjectionsPrecipitation(ClimRRSeasonalProjections):
    def __init__(self, agg_type):
        self.agg_type = agg_type  # 'Mean' or 'Max'
        super().__init__(f'Daily Precipitation {agg_type} projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('YlGnBu')

    def get_map(self, crossmodels, df, period, season='spring'):
        return super().get_map(crossmodels, df, period, label=f'{self.agg_type} Daily Precipitation (mm)')

    def add_legend(self):
        return super().add_legend(f'{self.agg_type} Daily Precipitation (mm)')

    def create_plots(self, mean):
        return super().create_plots(mean, f'Average {self.agg_type} Daily Precipitation', f'Daily Precipitation (mm)')

    def display_results(self, mean, std, figs):
        return super().display_results(mean, std, figs, f'Average {self.agg_type} Daily Precipitation', f'{self.agg_type} Daily Precipitation', 'mm')

    def analyze(self, crossmodels):
        return super().analyze(crossmodels, f'{self.agg_type} Daily Precipitation')
    

class ClimRRAnnualProjectionsHeatIndex(ClimRRAnnualClimateScenarios):
    def __init__(self):
        super().__init__('Heat Index projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('RdYlBu_r')  # Red (hot) to Blue (cold) color scale
    
    def analyze_annual(self, crossmodels, df):
        # check if there are two climate scenarios in the df.columns
        
        st.header("Time Period Comparison")

        columns_daily = [col for col in df.columns if 'DayMax' in col]
        st.header("Summer Daily Max Heat Index")
        self.map_comparing_period(crossmodels, df[['Crossmodel'] + columns_daily], scenario='daily', add_legend=False)
        st.header("Summer Seasonal Max Heat Index")
        columns_seasonal = [col for col in df.columns if 'SeaMax' in col]
        self.map_comparing_period(crossmodels, df[['Crossmodel'] + columns_seasonal], scenario='seasonal')
        st.header("# of Summer Days Above Threshold")
        threshold = st.radio("Select a threshold (in °F) for the number of summer days above", ['95', '105', '115', '125'], horizontal=True)
        columns_daily = [col for col in df.columns if f'Day{threshold}' in col]
        self.map_comparing_period(crossmodels, df[['Crossmodel'] + columns_daily], scenario='daily', add_legend=False)
        
        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)
        max_value = df[columns_daily].max().max()

        norm = mcolors.Normalize(vmin=0, vmax=max_value)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=self.color_scale), 
                          cax=ax, orientation='horizontal', label='# of Summer Days Above Threshold')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        
        data = base64.b64encode(buf.getbuffer()).decode("utf8")
        
        legend_html = f"""
        <div style="text-align:center;">
            <img src="data:image/png;base64,{data}" style="max-width:100%">
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)


        st.header(f"{self.keyword} Meta-Analysis")
        mean, std = self.calculate_statistics(df)
        fig = self.create_plot(mean)
        return self.display_results(mean, std, fig)

    def get_map(self, crossmodels, df, period, season='spring'):
        if 'DayMax' in df.columns:
            return super().get_map(crossmodels, df, period, season, label='Summer Daily Max Heat Index')
        elif 'SeaMax' in df.columns:
            return super().get_map(crossmodels, df, period, season, label='Summer Seasonal Max Heat Index')
        else:
            return super().get_map(crossmodels, df, period, season, label='# of Summer Days Above Threshold')
    
    def add_legend(self, lable='Heat Index'):
        return super().add_legend(lable)
    
    def create_plot(self, mean, col_label='Heat Index', label_with_metric='Heat Index', title='Mean Heat Index'):
        mean = mean.reset_index()

        mean.columns = ['Time Period', col_label]

        # Add a Scenario column based on the 'Time Period' values
        def determine_scenario(period):
            if 'DayMax' in period:
                return 'Daily'
            elif 'SeaMax' in period:
                return 'Seasonal'
            
        def determine_period(period):
            if 'HIS' in period:
                return 'Historical'
            elif 'M85' in period:
                return 'Mid-Century'
            elif 'E85' in period:
                return 'End-Century'
            
        def determine_threshold(period):
            if 'Day95' in period:
                return '# of summer days above 95 F'
            elif 'Day105' in period:
                return '# of summer days above 105 F'
            elif 'Day115' in period:
                return '# of summer days above 115 F'
            else:
                return '# of summer days above 125 F'

        mean_max = mean[mean['Time Period'].str.contains('Max')]
        mean_above = mean.drop(mean_max.index)
        mean_above.columns = ['Time Period', '# of Summer Days Above Threshold']
        
        mean_max['Scenario'] = mean_max['Time Period'].apply(determine_scenario)
        mean_above['Threshold'] = mean_above['Time Period'].apply(determine_threshold)

        mean_max['Time Period'] = mean_max['Time Period'].apply(determine_period)
        mean_above['Time Period'] = mean_above['Time Period'].apply(determine_period)        

        # Explicitly set the order of the x-axis (Time Period)
        time_order = ['Historical', 'Mid-Century', 'End-Century']
        mean_max['Time Period'] = pd.Categorical(mean_max['Time Period'], categories=time_order, ordered=True)
        mean_above['Time Period'] = pd.Categorical(mean_above['Time Period'], categories=time_order, ordered=True)

        # Create the line plot
        fig = px.line(
            # only keep the rows with 'Max' in the 'Time Period' column
            mean_max,
            x='Time Period',
            y=col_label,
            color='Scenario',
            title=f'{title} Across Time Periods',
            labels={col_label: label_with_metric, 'Time Period': 'Time Period'},
            color_discrete_map={'Historical': '#000000', 'Daily': '#FFA500', 'Seasonal': '#FF0000'}
        )

        # Update layout for better visualization
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title='Time Period',
            yaxis_title=label_with_metric,
            xaxis=dict(tickangle=-45)  # Rotate x-axis labels for better readability
        )

        fig2 = px.bar(
            mean_above,
            x='Time Period',
            y='# of Summer Days Above Threshold',
            color='Threshold',
            title=f'{title} Across Time Periods',
            labels={'# of Summer Days Above Threshold': '# of Summer Days Above Threshold', 'Time Period': 'Time Period'},
            barmode='overlay',
            color_discrete_map={
                '# of summer days above 95 F': '#FFA500',
                '# of summer days above 105 F': '#FF4500',
                '# of summer days above 115 F': '#FF0000',
                '# of summer days above 125 F': '#8B0000'
            }
        )

        # Update layout for better visualization
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title='Time Period',
            yaxis_title=label_with_metric,
            xaxis=dict(tickangle=-45)  # Rotate x-axis labels for better readability
        )

        return [fig, fig2]
    
    def display_results_helper(self, table, std_table, scenarios, indices):
        display_tables = []
        for scenario in scenarios:
            table_scenario = table.loc[:, table.columns.str.contains(scenario)]
            std_table_scenario = std_table.loc[:, std_table.columns.str.contains(scenario)]
            display_table_scenario = table_scenario.map(lambda x: f"{x:.2f}") + ' (' + std_table_scenario.map(lambda x: f"{x:.2f}") + ')'
            display_table_scenario.columns = ['Historical', 'Mid-Century', 'End-Century']
            display_tables.append(display_table_scenario)
        
        final_display_table = pd.concat(display_tables, axis=0)
        final_display_table.index = indices
        return final_display_table

    
    def display_results(self, mean, std, figs, label = 'Heat Index', label_with_metric = 'Heat Index', metric = ''):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            for fig in figs:
                st.plotly_chart(fig, use_container_width=True)
            st.write(f"This chart illustrates the trends in {label} across the three time periods.")

        with col1:
            table = pd.DataFrame(mean).T
            std_table = pd.DataFrame(std).T

            display_table_heat_index = self.display_results_helper(table, std_table, ['DayMax', 'SeaMax'], ['Daily Max', 'Seasonal Max'])

            # Display the tables using Streamlit
            st.caption(f"{label_with_metric} (Std Dev) - Summer Max Heat Index")
            st.dataframe(display_table_heat_index, use_container_width=True)

            st.write(f"These tables present the {label} values for each time period and scenario, with standard deviations in parentheses.")

            st.caption(f"{label_with_metric} Range")
            st.write(f"Minimum: {self.min_value:.2f} {metric}")
            st.write(f"Maximum: {self.max_value:.2f} {metric}")
            st.write(f"This shows the range of {label} values in the dataset.")

            display_table_days_above = self.display_results_helper(table, std_table, ['Day95', 'Day105', 'Day115', 'Day125'], ['95 F', '105 F', '115 F', '125 F'])
            st.caption(f"Number of Summer Days Above Threshold")
            st.dataframe(display_table_days_above, use_container_width=True)

            
        messages = self.get_messages(table)
        return col3, messages, self.plots
