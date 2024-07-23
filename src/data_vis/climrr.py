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

    def initialize_data(self):
        df = pd.read_csv(self.path)
        return df[self.values_of_interests + ['Crossmodel']]

    @abstractmethod
    def create_color_scale(self):
        pass

    def get_color(self, value):
        normalized_value = (value - self.min_value) / (self.max_value - self.min_value)
        return mcolors.rgb2hex(self.color_scale(normalized_value))

    def map_comparing_period(self, crossmodels, df, season='spring'):
        periods = self.data_info['periods']
        captions = ["Historical", "Mid-century", "End-century"]
        cols = st.columns(len(periods))
        for i, period in enumerate(periods):
            with cols[i]:
                m = self.get_map(crossmodels, df, period, season)
                st.caption(captions[i])
                st_folium(m, width=450, height=450, key=f"{self.keyword}_{season}_{period}")
        self.add_legend()

    def map_comparing_period_by_choosing_season(self, crossmodels, df):
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
        self.map_comparing_period(crossmodels, df, season)

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
        st.header("Time Period & Seasonal Comparison")
        self.map_comparing_period_by_choosing_season(crossmodels, df)
        self.map_comparing_season_by_choosing_period(crossmodels, df)
        
        st.header(f"{self.keyword} Meta-Analysis")
        mean, std = self.calculate_statistics(df)
        figs = self.create_plots(mean)
        return self.display_results(mean, std, figs)

    def analyze_annual(self, crossmodels, df):
        st.header("Time Period Comparison")
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

class ClimRRSeasonalProjectionsFWI(DataVisualizer):
    def __init__(self):
        super().__init__('Fire Weather Index (FWI) projections')

    def create_color_scale(self):
        # FWI uses a custom color scale, so we'll return None here
        return None

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
        return col3, messages
    
class ClimRRAnnualProjectionsPrecipitation(DataVisualizer):
    def __init__(self):
        super().__init__('Precipitation projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('YlGnBu')

    def get_map(self, crossmodels, df, period, season='spring'):
        columns = [col for col in df.columns if period in col]
        precipitation_df = df[['Crossmodel'] + columns]
        col_name = columns[0]

        precipitation_df_geo = gpd.GeoDataFrame(crossmodels.merge(precipitation_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(precipitation_df_geo, 
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name], 
                                                       aliases=['Crossmodel', 'Precipitation (mm)']),
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
                          cax=ax, orientation='horizontal', label='Precipitation (mm)')
        
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
        
        fig = px.line(table.T, title=f'Total Annual Precipitation Across Time Periods', 
                      labels={'value': 'Precipitation (mm)', 'index': 'Time Period'},
                      color_discrete_sequence=['#FFA500'])

        fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    def display_results(self, mean, std, fig):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write("This chart illustrates the trends in mean annual precipitation across the three time periods.")

        with col1:
            table = pd.DataFrame(mean).T
            table.index = ['Annual']
            std_table = pd.DataFrame(std).T
            std_table.index = ['Annual']
            
            display_table = table.map(lambda x: f"{x:.2f}") + ' (' + std_table.map(lambda x: f"{x:.2f}") + ')'
            
            st.caption("Mean Annual Precipitation (mm) (Std Dev)")
            st.dataframe(display_table, use_container_width=True)
            st.write("This table presents the mean annual precipitation values for each time period, with standard deviations in parentheses.")

        
            st.caption("Precipitation Range")
            st.write(f"Minimum: {self.min_value:.2f} mm")
            st.write(f"Maximum: {self.max_value:.2f} mm")
            st.write("This shows the range of precipitation values in the dataset.")

        messages = self.get_messages(table)
        return col3, messages

class ClimRRAnnualProjectionsCDNP(DataVisualizer):
    def __init__(self):
        super().__init__('Consecutive Dry Days projections')

    def create_color_scale(self):
        return plt.cm.get_cmap('YlOrBr')

    def get_map(self, crossmodels, df, period, season='spring'):
        columns = [col for col in df.columns if period in col]
        cdnp_df = df[['Crossmodel'] + columns]
        col_name = columns[0]

        cdnp_df_geo = gpd.GeoDataFrame(crossmodels.merge(cdnp_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(cdnp_df_geo, 
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name], 
                                                       aliases=['Crossmodel', 'Consecutive Days with No Precipitation']),
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
                          cax=ax, orientation='horizontal', label='Consecutive Days with No Precipitation')
        
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
        
        fig = px.line(table.T, title=f'Mean Annual Consecutive Days with No Precipitation Across Time Periods', 
                      labels={'value': 'Consecutive Days', 'index': 'Time Period'},
                      color_discrete_sequence=['#8B4513'])

        fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    def display_results(self, mean, std, fig):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write("This chart illustrates the trends in mean annual Consecutive Days with No Precipitation across the three time periods.")

        with col1:
            table = pd.DataFrame(mean).T
            table.index = ['Annual']
            std_table = pd.DataFrame(std).T
            std_table.index = ['Annual']
            
            display_table = table.map(lambda x: f"{x:.2f}") + ' (' + std_table.map(lambda x: f"{x:.2f}") + ')'
            
            st.caption("Mean Annual Consecutive Days with No Precipitation (Std Dev)")
            st.dataframe(display_table, use_container_width=True)
            st.write("This table presents the mean annual Consecutive Days with No Precipitation for each time period, with standard deviations in parentheses.")

        
            st.caption("Consecutive Days with No Precipitation Range")
            st.write(f"Minimum: {self.min_value:.2f} days")
            st.write(f"Maximum: {self.max_value:.2f} days")
            st.write("This shows the range of Consecutive Days with No Precipitation in the dataset.")

        messages = self.get_messages(table)
        return col3, messages

class ClimRRAnnualProjectionsWindSpeed(DataVisualizer):
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
        table = pd.DataFrame(mean).T
        table.index = ['Annual']
        
        fig = px.line(table.T, title=f'Mean Annual Wind Speed Across Time Periods', 
                      labels={'value': 'Wind Speed (m/s)', 'index': 'Time Period'},
                      color_discrete_sequence=['#4682B4'])

        fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    def display_results(self, mean, std, fig):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write("This chart illustrates the trends in mean annual Wind Speed across the three time periods.")

        with col1:
            table = pd.DataFrame(mean).T
            table.index = ['Annual']
            std_table = pd.DataFrame(std).T
            std_table.index = ['Annual']
            
            display_table = table.map(lambda x: f"{x:.2f}") + ' (' + std_table.map(lambda x: f"{x:.2f}") + ')'
            
            st.caption("Mean Annual Wind Speed (m/s) (Std Dev)")
            st.dataframe(display_table, use_container_width=True)
            st.write("This table presents the mean annual Wind Speed for each time period, with standard deviations in parentheses.")

            st.caption("Wind Speed Range")
            st.write(f"Minimum: {self.min_value:.2f} m/s")
            st.write(f"Maximum: {self.max_value:.2f} m/s")
            st.write("This shows the range of Wind Speed values in the dataset.")

        messages = self.get_messages(table)
        return col3, messages

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
        return col3, messages

    def analyze(self, crossmodels):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])
        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)
        
        st.header("Time Period Comparison")
        self.map_comparing_period(crossmodels, df)
        
        st.header("Cooling Degree Days Meta-Analysis")
        mean, std = self.calculate_statistics(df)
        fig = self.create_plot(mean)
        self.display_results(mean, std, fig)

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
        return col3, messages

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
    

class ClimRRSeasonalProjectionsTemperature(DataVisualizer):
    def __init__(self, temp_type):
        self.temp_type = temp_type  # 'Maximum' or 'Minimum'
        super().__init__(f'Seasonal Temperature {temp_type} projections')
        self.seasons = ['spring', 'summer', 'autumn', 'winter']

    def create_color_scale(self):
        return plt.cm.get_cmap('RdYlBu_r')  # Red (hot) to Blue (cold) color scale

    def get_map(self, crossmodels, df, period, season='spring'):
        season_columns = [col for col in df.columns if season in col and period in col]
        season_temp_df = df[['Crossmodel'] + season_columns]
        col_name = season_columns[0]

        temp_df_geo = gpd.GeoDataFrame(crossmodels.merge(season_temp_df, left_on='Crossmodel', right_on='Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(temp_df_geo, 
                tooltip=folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name], 
                                                    aliases=['Crossmodel', f'{self.temp_type} Temperature (°F)']),
                style_function=lambda x: {'fillColor': self.get_color(x['properties'][col_name]), 
                                        'color': self.get_color(x['properties'][col_name])})
        )
        return m

    def add_legend(self):
        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)

        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=self.color_scale), 
                          cax=ax, orientation='horizontal', label=f'{self.temp_type} Temperature (°F)')
        
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
        pass

    def create_plots(self, mean):
        table = pd.DataFrame(mean.values.reshape(4, 3), 
                             columns=self.data_info['periods'], 
                             index=self.seasons)
        
        fig1 = px.line(table.T, title=f'Mean {self.temp_type} Temperature Across Seasons and Time Periods', 
                       labels={'value': 'Temperature (°F)', 'index': 'Time Period'},
                       color_discrete_map={'winter': '#2196F3', 'spring': '#4CAF50', 
                                           'summer': '#FFC107', 'autumn': '#FF9800'})
        
        fig2 = px.line(table, title=f'Mean {self.temp_type} Temperature Values Across Seasons and Time Periods',
                       labels={'value': 'Temperature (°F)', 'index': 'Season'},
                       color_discrete_map={'hist': '#4CAF50', 'midc': '#FFC107', 'endc': '#FF9800'})
        
        for fig in [fig1, fig2]:
            fig.update_layout(legend_title_text='', legend=dict(traceorder='normal'),
                              plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        
        return [fig1, fig2]

    def display_results(self, mean, std, figs):
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            for fig in figs:
                st.plotly_chart(fig, use_container_width=True)
            st.write(f"These charts illustrate the trends in mean {self.temp_type} Temperature values across seasons and time periods.")

        with col1:
            table = pd.DataFrame(mean.values.reshape(4, 3), 
                                 columns=self.data_info['periods'], 
                                 index=self.seasons)
            std_table = pd.DataFrame(std.values.reshape(4, 3), 
                                     columns=self.data_info['periods'], 
                                     index=self.seasons)
            
            display_table = table.map(lambda x: f"{x:.2f}") + ' (' + std_table.map(lambda x: f"{x:.2f}") + ')'
            
            st.caption(f"Mean {self.temp_type} Temperature Values (°F) (Std Dev)")
            st.dataframe(display_table, use_container_width=True)
            st.write(f"This table presents the mean {self.temp_type} Temperature values for each season and time period, with standard deviations in parentheses.")
            
            st.caption(f"{self.temp_type} Temperature Range")
            st.write(f"Minimum: {self.min_value:.2f}°F")
            st.write(f"Maximum: {self.max_value:.2f}°F")
            st.write(f"This shows the range of {self.temp_type} Temperature in the dataset.")

        messages = self.get_messages(display_table.transpose())
        return col3, messages

    def analyze(self, crossmodels):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])
        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)
        
        st.header("Time Period & Seasonal Comparison")
        st.write(f"""
            This section allows you to compare {self.temp_type} Temperature values for a specific season across three time periods: 
            historical, mid-century, and end-century. 
            Use the radio buttons below to select a season and observe how temperature is projected to change over time.
        """)
        self.map_comparing_period_by_choosing_season(crossmodels, df)
        st.write("""
            Use the radio buttons to select a time period and observe how temperature varies by season.
            """)
        self.map_comparing_season_by_choosing_period(crossmodels, df)

        st.header(f"{self.temp_type} Temperature Meta-Analysis")
        st.write(f"""
            This section provides a statistical overview of the {self.temp_type} Temperature values across all time periods. 
            It includes line charts showing trends over time and tables with detailed numerical data.
        """)
        
        mean, std = self.calculate_statistics(df)
        figs = self.create_plots(mean)
        return self.display_results(mean, std, figs)

    def calculate_statistics(self, df):
        df = df.drop(columns='Crossmodel')
        return df.mean(), df.std()
    