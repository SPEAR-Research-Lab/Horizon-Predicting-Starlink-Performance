import sys
import os
from enum import Enum
import math
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(os.path.abspath('..'))
from utils import iso2_to_iso3, filter_df_by_min_measurements


class Metric(Enum):
    """Enum for aggregation metrics"""
    MIN = 'min'
    MAX = 'max'
    STD = 'std'
    MEAN = 'mean'
    MEDIAN = 'median'


def compute_country_metric(
    df: pd.DataFrame, 
    measurement_column: str, 
    metric: Metric,
    country_column='client_country_code'
) -> pd.DataFrame:
    """
    Compute a metric (min, max, std, mean, median) for each country.
    """
    if measurement_column not in df.columns:
        raise ValueError(f"Column '{measurement_column}' not found in dataframe")
    
    grouped = df.groupby(country_column)[measurement_column]
    
    if metric == Metric.MIN:
        result = grouped.min()
    elif metric == Metric.MAX:
        result = grouped.max()
    elif metric == Metric.STD:
        result = grouped.std()
    elif metric == Metric.MEAN:
        result = grouped.mean()
    elif metric == Metric.MEDIAN:
        result = grouped.median()
    else:
        raise ValueError(f"Unknown metric: {metric}")
    
    counts = grouped.count()
    
    result_df = pd.DataFrame({
        'country_code': result.index,
        'metric_value': result.values,
        'count': counts.values
    })
    
    result_df['iso3'] = result_df['country_code'].apply(iso2_to_iso3)
    
    return result_df


def compute_metric_difference(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    measurement_column: str,
    metric: Metric,
    min_measurements=50,
    country_column='client_country_code'
) -> pd.DataFrame:
    """
    Compute the difference in a metric between before and after filtration.
    Only includes countries with at least min_measurements in the after filtration dataset.
    """
    df_after_filtered = filter_df_by_min_measurements(
        df_after, 
        min_measurements=min_measurements,
    )
    
    valid_countries = df_after_filtered[country_column].unique()
    
    df_before_filtered = df_before[df_before[country_column].isin(valid_countries)]
    
    before_metrics = compute_country_metric(df_before_filtered, measurement_column, metric, country_column)
    after_metrics = compute_country_metric(df_after_filtered, measurement_column, metric, country_column)
    
    merged = pd.merge(
        before_metrics,
        after_metrics,
        on='country_code',
        suffixes=('_before', '_after'),
        how='inner'
    )
    
    merged['difference'] = merged['metric_value_after'] - merged['metric_value_before']
    
    merged['percent_change'] = (
        (merged['difference'] / merged['metric_value_before'].abs()) * 100
    ).replace([float('inf'), -float('inf')], 0)
    
    result = merged[[
        'country_code', 
        'iso3_before',
        'metric_value_before', 
        'metric_value_after', 
        'difference',
        'percent_change',
        'count_before',
        'count_after'
    ]].rename(columns={
        'iso3_before': 'iso3',
        'metric_value_before': 'before_value',
        'metric_value_after': 'after_value'
    })
    
    return result


def plot_metric_comparison_map(
    diff_df: pd.DataFrame,
    measurement_name: str,
    colorscale='turbo'
) -> go.Figure:
    """
    Create a choropleth map showing the difference in a metric.
    """
    value_col = 'difference'
    unit = measurement_name.split('(')[-1].rstrip(')')
    
    hover_text = []
    for _, row in diff_df.iterrows():
        text = (
            f"<b>{row['country_code']}</b><br>"
            f"Before: {row['before_value']:.2f}<br>"
            f"After: {row['after_value']:.2f}<br>"
            f"Difference: {row['difference']:.2f}<br>"
            f"Change: {row['percent_change']:.1f}%<br>"
            f"Measurements (before): {row['count_before']:,}<br>"
            f"Measurements (after): {row['count_after']:,}"
        )
        hover_text.append(text)
    
    diff_df['hover_text'] = hover_text
    vmin = math.floor(diff_df['difference'].min() / 10) * 10
    vmax = math.ceil(diff_df['difference'].max() / 10) * 10
    
    fig = go.Figure(data=go.Choropleth(
        locations=diff_df['iso3'],
        z=diff_df[value_col],
        text=diff_df['hover_text'],
        hovertemplate='%{text}<extra></extra>',
        colorscale=colorscale,
        zmin=vmin,
        zmax=vmax,
        autocolorscale=False,
        marker_line_color='black',
        marker_line_width=1,
        colorbar=dict(
            title=dict(
                text=unit + '<br>',
                side='top',
                font=dict(size=20, color='#222222', family='CMU Sans Serif'),
            ),
            x=1.0,
            len=1.0,
            thickness=15,
            y=0.5,
            yanchor='middle',
            titlefont=dict(size=20, color='#222222', family='CMU Sans Serif'),
            tickfont=dict(size=20, color='#222222', family='CMU Sans Serif'),
            ticklen=6,
            tickwidth=2,
        ),
        zmid=0
    ))
    
    fig.update_layout(
        font=dict(size=10, color='#222222', family='CMU Sans Serif'),
        geo=dict(
            showframe=True,
            framecolor='black',
            framewidth=1,
            showcoastlines=True,
            projection_type='equirectangular',
            lataxis=dict(range=[-60, 90])
        ),
        height=250,
        width=640,
        margin=dict(l=0, r=0, t=0, b=0),
        autosize=False
    )
    
    return fig


def plot_before_after_maps(
    diff_df: pd.DataFrame,
    measurement_name: str,
    metric: Metric,
    colorscale='turbo'
 ) -> go.Figure:
    """
    Create side-by-side choropleth maps showing before and after values.
    """
    hover_before = []
    for _, row in diff_df.iterrows():
        text = (
            f"<b>{row['country_code']}</b><br>"
            f"{metric.value.upper()}: {row['before_value']:.2f}<br>"
            f"Measurements: {row['count_before']:,}"
        )
        hover_before.append(text)
    
    hover_after = []
    for _, row in diff_df.iterrows():
        text = (
            f"<b>{row['country_code']}</b><br>"
            f"{metric.value.upper()}: {row['after_value']:.2f}<br>"
            f"Measurements: {row['count_after']:,}"
        )
        hover_after.append(text)
    
    vmin = 0
    vmax = math.ceil(diff_df['before_value'].max() / 10) * 10

    fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'geo'}, {'type': 'geo'}]], horizontal_spacing=0.01)
    fig.add_trace(
        go.Choropleth(
            locations=diff_df['iso3'],
            z=diff_df['before_value'],
            text=hover_before,
            hovertemplate='%{text}<extra></extra>',
            colorscale=colorscale,
            zmin=vmin,
            zmax=vmax,
            marker_line_color='black',
            marker_line_width=1,
            showscale=False
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Choropleth(
            locations=diff_df['iso3'],
            z=diff_df['after_value'],
            text=hover_after,
            hovertemplate='%{text}<extra></extra>',
            colorscale=colorscale,
            zmin=vmin,
            zmax=vmax,
            marker_line_color='black',
            marker_line_width=1,
            colorbar=dict(
                title=dict(
                    text=measurement_name.split("(")[-1].rstrip(")") + '<br>',
                    side='top',
                    font=dict(size=20, color='#222222', family='CMU Sans Serif'),
                ),
                x=1.0,
                len=1.0,
                thickness=15,
                titlefont=dict(size=20, color='#222222', family='CMU Sans Serif'),
                tickfont=dict(size=20, color='#222222', family='CMU Sans Serif'),
                ticklen=6,
                tickwidth=2,
            )
        ),
        row=1, col=2
    )

    fig.update_geos(showframe=True, framecolor='black', framewidth=1,
                    showcoastlines=True, projection_type='equirectangular',
                    lataxis=dict(range=[-60, 90]), row=1, col=1)
    fig.update_geos(showframe=True, framecolor='black', framewidth=1,
                    showcoastlines=True, projection_type='equirectangular',
                    lataxis=dict(range=[-60, 90]), row=1, col=2)

    fig.update_layout(
        font=dict(size=20, color='#222222', family='CMU Sans Serif'),
        height=250,
        width=1200,
        margin=dict(l=0, r=0, t=0, b=0),
        autosize=False
    )

    return fig


def plot_filtering_percentage(
    df_all: pd.DataFrame,
    df_filtered: pd.DataFrame,
    color_scale='turbo'
) -> go.Figure:
    """
    Plot the percentage of records removed by filtering for each country.
    """
    def calculate_percentages(df_all_split: pd.DataFrame, df_filtered_split: pd.DataFrame) -> pd.DataFrame:
        if df_all_split is None or df_all_split.empty:
            raise ValueError("Empty dataframes.")
        
        all_counts = df_all_split.groupby('client_country_code').size().reset_index(name='total')
        filtered_counts = df_filtered_split.groupby('client_country_code').size().reset_index(name='filtered')
        
        merged = all_counts.merge(filtered_counts, on='client_country_code', how='left')
        merged['filtered'] = merged['filtered'].fillna(0)
        merged['percentage_removed'] = (merged['filtered'] / merged['total']) * 100
        merged['iso3'] = merged['client_country_code'].apply(iso2_to_iso3)
        
        return merged
    
    data = calculate_percentages(df_all, df_filtered)

    if data is not None:
        fig = go.Figure()
        fig.add_trace(
            go.Choropleth(
                locations=data['iso3'],
                z=data['percentage_removed'],
                locationmode='ISO-3',
                colorscale=color_scale,
                zmin=0,
                zmax=100,
                showscale=True,
                colorbar=dict(
                    title='%',
                    x=1.0,
                    len=1.0,
                    thickness=15,
                    titlefont=dict(size=20, color='#222222', family='CMU Sans Serif'),
                    tickfont=dict(size=20, color='#222222', family='CMU Sans Serif'),
                    ticklen=6,
                    tickwidth=2,
                ),
                text=data['client_country_code'],
                customdata=data[['filtered', 'total']],
                hovertemplate='<b>%{text}</b><br>Removed: %{z:.1f}%<br>Filtered: %{customdata[0]:,.0f}<br>Total: %{customdata[1]:,.0f}<extra></extra>'
            )
        )
        fig.update_geos(projection_type='equirectangular', lataxis=dict(range=[-60,90]))
        fig.update_layout(
            font=dict(size=20, color='#222222', family='CMU Sans Serif'),
            height=250,
            width=640,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
            autosize=False,
        )
        return fig

    raise ValueError("No data available to plot filtering percentages.")
