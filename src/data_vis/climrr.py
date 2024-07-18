import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
from abc import abstractmethod
from src.utils import load_config
from src.data_vis.climrr_utils import categorize_fwi, fwi_color, convert_to_dataframe
from src.data_vis.data_visualizer_utils import DataVisualizer
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
import base64

config = load_config('src/data_vis/climrr.yml')

class ClimRRProjections(DataVisualizer):
    def __init__(self, keyword):
        self.keyword = keyword
        self.data_info = config[keyword]
        self.path = self.data_info['path']
        self.values_of_interests = self.data_info['values_of_interests']
        
    def initialize_data(self):
        df = pd.read_csv(self.path)
        df = df[self.values_of_interests + ['Crossmodel']]
        return df
    
    @abstractmethod
    def get_map(self, df, period, season='spring'):
        pass
    
    @abstractmethod
    def add_legend(self):
        pass

    def map_comparing_period(self, crossmodels, df, season='spring'):
        periods = self.data_info['periods']
        captions = ["Historical", "Mid-century", "End-century"]
        cols = st.columns(3)
        for i in range(3):
            with cols[i]:
                m = self.get_map(crossmodels, df, periods[i], season)
                st.caption(captions[i])
                st_folium(m, width=450, height=350, key=f"{self.keyword}_{season}_{periods[i]}")
        self.add_legend()

    def map_comparing_period_by_choosing_season(self, crossmodels, df):
        season = st.radio('Select Season:', ['spring', 'summer', 'autumn', 'winter'], horizontal=True)
        self.map_comparing_period(crossmodels, df, season)
        
    def map_comparing_season_by_choosing_period(self, crossmodels, df):
        period = st.radio('Select Time Period:', self.data_info['periods'], horizontal=True)
        
        seasons = ['spring', 'summer', 'autumn', 'winter']
        cols = st.columns(4)
        for i in range(4):
            with cols[i]:
                m = self.get_map(crossmodels, df, period, seasons[i])
                st.caption(seasons[i])
                st_folium(m, width=350, height=350, key=f"{self.keyword}_{seasons[i]}_{period}_2")
        
        self.add_legend()

    def analyze(self, crossmodels):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])

        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)

        if self.data_info['season']:
            st.header("Time Period & Seasonal Comparison")
            st.write(f"""
                This section allows you to compare {self.keyword} values for a specific season across three time periods: 
                historical, mid-century, and end-century. 
                Use the radio buttons below to select a season and observe how fire risk is projected to change over time.
            """)
            self.map_comparing_period_by_choosing_season(crossmodels, df)
            st.write("""
                Use the radio buttons to select a time period and observe how fire risk varies by season.
                """)
            self.map_comparing_season_by_choosing_period(crossmodels, df)
        else:
            st.header("Time Period Comparison")
            self.map_comparing_period(crossmodels, df)

        st.header(f"{self.keyword} Meta-Analysis")
        st.write(f"""
            This section provides a statistical overview of the {self.keyword} values across all time periods. 
            It includes a line chart showing trends over time and tables with detailed numerical data.
        """)
        
        df = df.drop(columns='Crossmodel')
        mean = df.mean()
        std = df.std()

        if self.data_info['season']:
            mean = mean.values.reshape(4, 3)
            std = std.values.reshape(4, 3)
            table = pd.DataFrame(mean, columns=self.data_info['periods'], index=['spring', 'summer', 'autumn', 'winter'])
            colors = {
                'spring': '#4CAF50',
                'summer': '#FFC107',
                'autumn': '#FF9800',
                'winter': '#2196F3'
            }
            fig = px.line(table.T, title=f'Mean {self.keyword} Across Seasons and Time Periods', 
                        labels={'value': f'{self.keyword}', 'index': 'Time Period'},
                        category_orders={'season': ['spring', 'summer', 'autumn', 'winter']},
                        color_discrete_map=colors)

            fig.update_layout(
                legend_title_text='Season',
                legend=dict(traceorder='normal'),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )

            colors = {
                'Hist': '#4CAF50',
                'Midc': '#FFC107',
                'Endc': '#FF9800'
            }

            fig2 = px.line(table, title='Mean FWI Values Across Seasons and Time Periods',
                            labels={'value': 'FWI Value', 'index': 'Season'},
                            color_discrete_map=colors)
            
            fig2.update_layout(
                legend_title_text='Time Period',
                legend=dict(traceorder='normal'),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )

            return table, std, [fig, fig2]
        else:
            return mean, std
    
class ClimRRSeasonalProjectionsFWI(ClimRRProjections):
    def __init__(self):
        super().__init__('Fire Weather Index (FWI) projections')
        self.df = self.initialize_data()

    @staticmethod
    def add_legend():
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

    def get_map(self, crossmodels, df, period, season = 'spring'):
        season_columns = [col for col in df.columns if season in col and period in col]
        season_fwi_df = df[['Crossmodel'] + season_columns]
        col_name = season_columns[0]
        season_fwi_df['class'] = season_fwi_df[col_name].apply(categorize_fwi)

        fwi_df_geo = gpd.GeoDataFrame(crossmodels.merge(season_fwi_df, left_on = 'Crossmodel', right_on = 'Crossmodel'))

        m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)
        m.add_child(
            folium.features.GeoJson(fwi_df_geo, tooltip = folium.features.GeoJsonTooltip(fields=['Crossmodel', col_name, 'class'], aliases=['Crossmodel', 'FWI', 'class']),
                                    style_function=lambda x: {'fillColor': fwi_color(x['properties'][col_name]), 'color': fwi_color(x['properties'][f'wildfire_{season}_{period}'])})
            )
        return m
    
    def analyze(self, crossmodels):
        table, std, figs = super().analyze(crossmodels)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.plotly_chart(figs[0], use_container_width=True)
            st.write(f"""
            This chart illustrates the trends in mean FWI values for each season across the three time periods. 
            Upward slopes indicate increasing fire risk over time, while the vertical separation between lines 
            shows the difference in fire risk between seasons.
            """)
            st.plotly_chart(figs[1], use_container_width=True)
            st.write(
                """
                    This chart shows the trends in mean FWI values for each time period across the four seasons.
                """)

        categories = table.map(categorize_fwi)
        table = table.map(lambda x: f"{x:.2f}")
        std = pd.DataFrame(std, columns=self.data_info['periods'], index=['spring', 'summer', 'autumn', 'winter']).map(lambda x: f"{x:.2f}")
        table = table + ' (' + std + ')'
        table = table + ' ' + categories

        with col1:
            st.caption("Mean FWI Values (Std Dev)")
            st.dataframe(table, use_container_width=True)
            st.write("""
            This table presents the mean FWI values for each season and time period, with standard deviations in parentheses. 
            Higher values indicate greater fire risk, while larger standard deviations suggest more variability in the data.
            """)

            st.write(table.to_string())

            st.caption("FWI Classification")
            data = {
                'FWI Class': ['Low', 'Medium', 'High', 'Very High', 'Extreme', 'Very Extreme'],
                'FWI Values': ['0-9', '9-21', '21-34', '34-39', '39-53', 'Above 53']
            }
            st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)
            st.write("""
            This table shows the classification of FWI values into risk categories. 
            Use this as a reference to interpret the FWI values in the maps and charts above.
            """)

        return table, col3
        

class ClimRRAnnualProjections(ClimRRProjections):
    def __init__(self):
        super().__init__('Precipitation projections')
        self.df = self.initialize_data()
        self.min_value = self.df[self.values_of_interests].min().min()
        self.max_value = self.df[self.values_of_interests].max().max()
        self.color_scale = self.create_color_scale()

    def create_color_scale(self):
        return plt.cm.get_cmap('YlOrRd')

    def get_color(self, value):
        normalized_value = (value - self.min_value) / (self.max_value - self.min_value)
        return mcolors.rgb2hex(self.color_scale(normalized_value))

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
        import matplotlib.pyplot as plt
        import io
        import base64

        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)

        cmap = self.color_scale
        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        
        cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), 
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

    def analyze(self, crossmodels):
        mean, std = super().analyze(crossmodels)

        table = pd.DataFrame(mean).T
        table.index = ['Annual']
        std = pd.DataFrame(std).T
        std.index = ['Annual']

        fig = px.line(table.T, title=f'Total Annual Precipitation Across Time Periods', 
                        labels={'value': 'Precipitation (mm)', 'index': 'Time Period'},
                        color_discrete_sequence=['#FFA500'])  # Using orange color for the line

        fig.update_layout(
            legend_title_text='',
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write("""
            This chart illustrates the trends in mean annual precipitation across the three time periods. 
            An upward slope indicates increasing precipitation over time, while a downward slope suggests decreasing precipitation.
            """)

        with col1:
            st.caption("Mean Annual Precipitation (mm) (Std Dev)")
            table = table.map(lambda x: f"{x:.2f}")
            std = std.map(lambda x: f"{x:.2f}")
            table = table + ' (' + std + ')'
            st.dataframe(table, use_container_width=True)
            st.write("""
            This table presents the mean annual precipitation values for each time period, with standard deviations in parentheses. 
            Higher values indicate greater precipitation, while larger standard deviations suggest more variability in the data.
            """)

        with col3:
            st.caption("Precipitation Range")
            st.write(f"Minimum: {self.min_value:.2f} mm")
            st.write(f"Maximum: {self.max_value:.2f} mm")
            st.write("""
            This shows the range of precipitation values in the dataset. 
            The color scale in the maps above is based on this range, 
            with yellows representing lower values and dark reds representing higher values.
            """)

        self.add_legend()

        return table, col3

class ClimRRAnnualProjectionsCDNP(ClimRRProjections):
    def __init__(self):
        super().__init__('Consecutive Dry Days projections')
        self.df = self.initialize_data()
        self.min_value = self.df[self.values_of_interests].min().min()
        self.max_value = self.df[self.values_of_interests].max().max()
        self.color_scale = self.create_color_scale()

    def create_color_scale(self):
        return plt.cm.get_cmap('YlOrBr')  # Yellow (fewer days) to Brown (more days)

    def get_color(self, value):
        normalized_value = (value - self.min_value) / (self.max_value - self.min_value)
        return mcolors.rgb2hex(self.color_scale(normalized_value))

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
        import matplotlib.pyplot as plt
        import io
        import base64

        fig, ax = plt.subplots(figsize=(6, 1))
        fig.subplots_adjust(bottom=0.5)

        cmap = self.color_scale
        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        
        cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), 
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

    def analyze(self, crossmodels):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])

        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)

        st.header("Time Period Comparison")
        self.map_comparing_period(crossmodels, df)

        st.header(f"{self.keyword} Meta-Analysis")
        st.write(f"""
            This section provides a statistical overview of the {self.keyword} values across all time periods. 
            It includes a line chart showing trends over time and tables with detailed numerical data.
        """)
        
        df = df.drop(columns='Crossmodel')
        mean = df.mean()
        std = df.std()

        table = pd.DataFrame(mean).T
        table.index = ['Annual']
        std = pd.DataFrame(std).T
        std.index = ['Annual']

        fig = px.line(table.T, title=f'Mean Annual Consecutive Days with No Precipitation Across Time Periods', 
                    labels={'value': 'Consecutive Days', 'index': 'Time Period'},
                    color_discrete_sequence=['#8B4513'])  # Using saddle brown color for the line

        fig.update_layout(
            legend_title_text='',
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write("""
            This chart illustrates the trends in mean annual Consecutive Days with No Precipitation across the three time periods. 
            An upward slope indicates increasing dry spells over time, suggesting a trend towards drier conditions.
            """)

        with col1:
            st.caption("Mean Annual Consecutive Days with No Precipitation (Std Dev)")
            table_display = table.map(lambda x: f"{x:.2f}")
            std_display = std.map(lambda x: f"{x:.2f}")
            table_display = table_display + ' (' + std_display + ')'
            st.dataframe(table_display, use_container_width=True)
            st.write("""
            This table presents the mean annual Consecutive Days with No Precipitation for each time period, with standard deviations in parentheses. 
            Higher values indicate longer dry spells, while larger standard deviations suggest more variability in the data.
            """)

        with col3:
            st.caption("Consecutive Days with No Precipitation Range")
            st.write(f"Minimum: {self.min_value:.2f} days")
            st.write(f"Maximum: {self.max_value:.2f} days")
            st.write("""
            This shows the range of Consecutive Days with No Precipitation in the dataset. 
            The color scale in the maps above is based on this range, 
            with yellows representing fewer consecutive dry days and browns representing more consecutive dry days.
            """)

        self.add_legend()

        return table, std, fig
    

class ClimRRAnnualProjectionsWindSpeed(ClimRRProjections):
    def __init__(self):
        super().__init__('Wind Speed projections')
        self.df = self.initialize_data()
        self.min_value = self.df[self.values_of_interests].min().min()
        self.max_value = self.df[self.values_of_interests].max().max()
        self.color_scale = self.create_color_scale()

    def create_color_scale(self):
        return plt.cm.get_cmap('YlGnBu')  # Yellow (low wind) to Green to Blue (high wind)

    def get_color(self, value):
        normalized_value = (value - self.min_value) / (self.max_value - self.min_value)
        return mcolors.rgb2hex(self.color_scale(normalized_value))

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

        cmap = self.color_scale
        norm = mcolors.Normalize(vmin=self.min_value, vmax=self.max_value)
        
        cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), 
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

    def analyze(self, crossmodels):
        st.title(self.data_info['title'])
        st.write(self.data_info['subtitle'])

        df = convert_to_dataframe(self.df, self.values_of_interests, crossmodels)

        st.header("Time Period Comparison")
        self.map_comparing_period(crossmodels, df)

        st.header(f"{self.keyword} Meta-Analysis")
        st.write(f"""
            This section provides a statistical overview of the {self.keyword} values across all time periods. 
            It includes a line chart showing trends over time and tables with detailed numerical data.
        """)
        
        df = df.drop(columns='Crossmodel')
        mean = df.mean()
        std = df.std()

        table = pd.DataFrame(mean).T
        table.index = ['Annual']
        std = pd.DataFrame(std).T
        std.index = ['Annual']

        fig = px.line(table.T, title=f'Mean Annual Wind Speed Across Time Periods', 
                    labels={'value': 'Wind Speed (m/s)', 'index': 'Time Period'},
                    color_discrete_sequence=['#4682B4'])  # Using steel blue color for the line

        fig.update_layout(
            legend_title_text='',
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.plotly_chart(fig, use_container_width=True)
            st.write("""
            This chart illustrates the trends in mean annual Wind Speed across the three time periods. 
            An upward slope indicates increasing wind speeds over time, while a downward slope suggests decreasing wind speeds.
            """)

        with col1:
            st.caption("Mean Annual Wind Speed (m/s) (Std Dev)")
            table_display = table.map(lambda x: f"{x:.2f}")
            std_display = std.map(lambda x: f"{x:.2f}")
            table_display = table_display + ' (' + std_display + ')'
            st.dataframe(table_display, use_container_width=True)
            st.write("""
            This table presents the mean annual Wind Speed for each time period, with standard deviations in parentheses. 
            Higher values indicate stronger winds, while larger standard deviations suggest more variability in the data.
            """)

        with col3:
            st.caption("Wind Speed Range")
            st.write(f"Minimum: {self.min_value:.2f} m/s")
            st.write(f"Maximum: {self.max_value:.2f} m/s")
            st.write("""
            This shows the range of Wind Speed in the dataset. 
            The color scale in the maps above is based on this range, 
            with yellows representing lower wind speeds and blues representing higher wind speeds.
            """)

        self.add_legend()

        return table, std, fig