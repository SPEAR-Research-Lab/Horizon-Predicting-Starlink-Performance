from typing import Optional, Set, Tuple, TypedDict, Literal, Dict
import pandas as pd
import plotly.graph_objects as go
from plotly.graph_objs._figure import Figure
from plotly.subplots import make_subplots
from utils import Aggregation, iso2_to_iso3, rgb_to_hex
import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
import pycountry
import math


class OrbitParams(TypedDict):
    coords: NDArray[np.float64]
    num_sats: int
    linestyle: Literal["dot", "dash", "dashdot", "longdashdot"]

OrbitToParams = Dict[float, OrbitParams]


def _aggregate_data(df: pd.DataFrame, feature: str, aggregation: Aggregation) -> pd.DataFrame:
    if aggregation == Aggregation.MEDIAN:
        return df.groupby('client_country_code')[feature].median().reset_index()
    elif aggregation == Aggregation.MEAN:
        return df.groupby('client_country_code')[feature].mean().reset_index()
    elif aggregation == Aggregation.MIN:
        return df.groupby('client_country_code')[feature].min().reset_index()
    elif aggregation == Aggregation.MAX:
        return df.groupby('client_country_code')[feature].max().reset_index()
    elif aggregation == Aggregation.COUNT:
        return df.groupby('client_country_code')[feature].count().reset_index()
    elif aggregation == Aggregation.NONE:
        return df
    else:
        raise ValueError(f"Unsupported aggregation: {aggregation}")


def get_unit_from_feature(feature: str) -> str:
    unit = feature.split('_')[-1]
    if 'mb' in unit or 'kb' in unit or 'gb' in unit:
        unit = unit.capitalize()
    return unit


def plot_feature(
    df: pd.DataFrame,
    feature: str,
    unit: Optional[str] = None,
    country_col = 'client_country_code',
    aggregation = Aggregation.MEDIAN,
    tick_step = 50,
    color_scale = 'turbo',
    width=640,
    height=250
) -> Figure:
    """
    Create a choropleth map for the specified feature aggregated by country.
    """
    agg_df = _aggregate_data(df, feature, aggregation)
    agg_df['iso3'] = agg_df[country_col].apply(iso2_to_iso3)

    max_value = agg_df[feature].max()
    
    max_value_rounded = int(np.ceil(max_value / tick_step) * tick_step)
    tick_vals = list(range(tick_step, max_value_rounded + 1, tick_step))

    fig = go.Figure(
        go.Choropleth(
            locations=agg_df['iso3'],
            z=agg_df[feature],
            locationmode='ISO-3',
            colorscale=color_scale,
            zmin=0,
            zmax=max_value_rounded,
            zauto=False,
            colorbar=dict(
                title= unit if unit else get_unit_from_feature(feature),
                x=1.0,
                len=1.0,
                thickness=15,
                titlefont=dict(size=20, color='#222222', family='CMU Sans Serif'),
                tickfont=dict(size=20, color='#222222', family='CMU Sans Serif'),
                ticklen=6,
                tickwidth=2,
                tickvals=tick_vals,
                ticktext=[str(v) for v in tick_vals],
            ),
            text=agg_df[country_col],
            hovertemplate='<b>%{text}</b><br>%{z:.2f} ' + get_unit_from_feature(feature) + '<extra></extra>'
        )
    )

    fig.update_geos(
        showframe=True,
        framecolor='black',
        framewidth=1,
        showcoastlines=True,
        projection_type='equirectangular',
        lataxis=dict(range=[-60, 90]),
    )
    fig.update_layout(
        font=dict(size=20, color='#222222', family='CMU Sans Serif'),
        height=height,
        width=width,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        autosize=False,
    )

    return fig


def plot_three_datasets(
    df_all: pd.DataFrame,
    df_filtered: pd.DataFrame,
    df_after: pd.DataFrame,
    feature: str,
    color_scale='turbo',
    aggregation=Aggregation.MEDIAN,
) -> Figure:
    """
    Create a single side-by-side choropleth with three panels: All, Filtered, After.
    Shared colorscale computed from `df_all`. Colorbar only shown on the rightmost panel.
    """
    all_agg = _aggregate_data(df_all, feature, aggregation)
    filtered_agg = _aggregate_data(df_filtered, feature, aggregation)
    after_agg = _aggregate_data(df_after, feature, aggregation)

    all_agg.columns = ['country', 'value']
    filtered_agg.columns = ['country', 'value']
    after_agg.columns = ['country', 'value']

    all_agg['iso3'] = all_agg['country'].apply(iso2_to_iso3)
    filtered_agg['iso3'] = filtered_agg['country'].apply(iso2_to_iso3)
    after_agg['iso3'] = after_agg['country'].apply(iso2_to_iso3)

    min_value = 0
    max_value = all_agg['value'].max()

    fig = make_subplots(rows=1, cols=3, specs=[[{'type': 'choropleth'}, {'type': 'choropleth'}, {'type': 'choropleth'}]], horizontal_spacing=0.01)
    fig.add_trace(
        go.Choropleth(
            locations=all_agg['iso3'],
            z=all_agg['value'],
            locationmode='ISO-3',
            colorscale=color_scale,
            zmin=min_value,
            zmax=max_value,
            showscale=False,
            text=all_agg['country'],
            hovertemplate='<b>%{text}</b><br>' + f'{aggregation.value.capitalize()}: %{{z:.2f}}<extra></extra>'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Choropleth(
            locations=filtered_agg['iso3'],
            z=filtered_agg['value'],
            locationmode='ISO-3',
            colorscale=color_scale,
            zmin=min_value,
            zmax=max_value,
            showscale=False,
            text=filtered_agg['country'],
            hovertemplate='<b>%{text}</b><br>' + f'{aggregation.value.capitalize()}: %{{z:.2f}}<extra></extra>'
        ),
        row=1, col=2
    )

    fig.add_trace(
        go.Choropleth(
            locations=after_agg['iso3'],
            z=after_agg['value'],
            locationmode='ISO-3',
            colorscale=color_scale,
            zmin=min_value,
            zmax=max_value,
            showscale=True,
            colorbar=dict(
                title=get_unit_from_feature(feature),
                x=1.0,
                len=1.0,
                thickness=15,
                titlefont=dict(size=20, color='#222222', family='CMU Sans Serif'),
                tickfont=dict(size=20, color='#222222', family='CMU Sans Serif'),
                ticklen=6,
                tickwidth=2,
            ),
            text=after_agg['country'],
            hovertemplate='<b>%{text}</b><br>' + f'{aggregation.value.capitalize()}: %{{z:.2f}}<extra></extra>'
        ),
        row=1, col=3
    )

    for col in (1, 2, 3):
        fig.update_geos(
            showframe=True,
            framecolor='black',
            framewidth=1,
            showcoastlines=True,
            projection_type='equirectangular',
            lataxis=dict(range=[-60, 90]),
            row=1, col=col
        )

    fig.update_layout(
        font=dict(size=20, color='#222222', family='CMU Sans Serif'),
        height=250,
        width=1750,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        autosize=False,
    )

    return fig


def plot_filtering_percentage(
    df_all: pd.DataFrame,
    df_filtered: pd.DataFrame,
    color_scale='turbo'
) -> Figure:
    """
    Plot the percentage of records removed by filtering for each country, split by terrestrial and Starlink.
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


def vertical_longitude(lat, lat0=-40, lon0=-140):
    """
    Calculate longitude that makes a point appear vertically below (lat0, lon0)
    on an equirectangular map where x = lon * cos(lat).
    """
    lat_rad = math.radians(lat)
    lat0_rad = math.radians(lat0)
    
    # Handle edge case: at poles (lat = ±90°), cos(lat) = 0
    cos_lat = math.cos(lat_rad)
    if abs(cos_lat) < 1e-10:
        raise ValueError(
            f"Cannot calculate aligned longitude at latitude {lat}° "
            "(too close to pole where cos(lat) ≈ 0)"
        )
    
    # Calculate aligned longitude using the equirectangular projection formula
    cos_lat0 = math.cos(lat0_rad)
    lon = lon0 * cos_lat0 / cos_lat
    
    # Normalize to [-180, 180] range
    lon = ((lon + 180) % 360) - 180
    
    return lon


def plot_starlink_infrastructure_map(
        islands_manual_plot: Set[Tuple[float, float]],
        pop_df: pd.DataFrame,
        gs_df: pd.DataFrame,
        orbit_to_params: OrbitToParams,
        starlink_countries: list[str]
    ) -> Figure:
    colors = [rgb_to_hex(color) for color in plt.get_cmap("tab10").colors]  # type: ignore
    fig = go.Figure()

    # Manual islands
    fig.add_trace(
        go.Scattergeo(
            lat=[p[0] for p in islands_manual_plot],
            lon=[p[1] for p in islands_manual_plot],
            mode="markers",
            marker=dict(
                size=1,
                color="black"
            ),
            showlegend=False
        )
    )

    
    # Ground stations
    fig.add_trace(
        go.Scattergeo(
            lon=gs_df['lon'],
            lat=gs_df['lat'],
            text=gs_df['name'],
            mode='markers',
            marker=dict(size=5, color='brown', symbol='square-open'),
            showlegend=False
        )
    )
    # Ground stations (legend only, bigger)
    fig.add_trace(
        go.Scattergeo(
            lon=[None],
            lat=[None],
            mode='markers',
            marker=dict(size=8, color='brown', symbol='square-open'),
            name='GS'
        )
    )
    
    # Points of presence (map only)
    fig.add_trace(
        go.Scattergeo(
            lon=pop_df['lon'],
            lat=pop_df['lat'],
            text=pop_df['name'],
            mode='markers',
            marker=dict(size=5, color='blue', symbol='circle'),
            showlegend=False
        )
    )
    # Points of presence (legend only, bigger)
    fig.add_trace(
        go.Scattergeo(
            lon=[None],
            lat=[None],
            mode='markers',
            marker=dict(size=8, color='blue', symbol='circle'),
            name='PoP'
        )
    )

    # Countries with Starlink availability
    z_values = []
    locations = []
    starlink_country_codes = [iso2_to_iso3(country) for country in starlink_countries]
    for country in pycountry.countries:
        alpha_3 = country.alpha_3 # type: ignore
        locations.append(alpha_3)
        if alpha_3 in starlink_country_codes:
            z_values.append(1)
        else:
            z_values.append(0)

    fig.add_trace(
        go.Choropleth(
            locations=locations,
            z=z_values,
            colorscale=[[0, 'white'], [1, 'lightgrey']],
            showscale=False,
            marker_line_color="black",
            marker_line_width=0.5,
            name='Starlink Coverage'
        )
    )

    for i, (inc, params) in enumerate(orbit_to_params.items()):
        fig.add_trace(
            go.Scattergeo(
                lon=params['coords'][:, 1],
                lat=params['coords'][:, 0],
                mode='lines',
                line=dict(color=colors[i % len(colors)], width=2),
                showlegend=False
            )
        )

        min_lat = params['coords'][:, 0].min()
        max_lat = params['coords'][:, 0].max()
        fig.add_trace(
            go.Scattergeo(
                lon=np.linspace(-180, 180, 360),
                lat=np.full(360, min_lat),
                mode='lines',
                line=dict(color=colors[i % len(colors)], width=1.5, dash=params['linestyle']),
                showlegend=False
            )
        )
        fig.add_trace(
            go.Scattergeo(
                lon=np.linspace(-180, 180, 360),
                lat=np.full(360, max_lat),
                mode='lines',
                line=dict(
                    color=colors[i % len(colors)],
                    width=1.5,
                    dash=params['linestyle']
                ),
                name=f"Orbit {inc}°"
            )
        )


        fig.add_trace(
            go.Scattergeo(
                lon=[12 if params['num_sats'] >= 1000 else 17],
                lat=[min_lat + 5],
                mode="text",
                text=[f"{params['num_sats']}  sats"],
                textfont=dict(color=colors[i % len(colors)], size=20, family="CMU Sans Serif"),
                textposition="middle right",
                showlegend=False
            )
        )
        fig.add_trace(
            go.Scattergeo(
                lon=[28.8],
                lat=[min_lat + 5],
                mode="text",
                text=["﹢"],
                textfont=dict(color=colors[i % len(colors)], size=20, family="CMU Sans Serif"),
                textposition="middle right",
                showlegend=False
            )
        )
        
    fig.update_geos(
        projection_type='equirectangular',
        lataxis=dict(range=[-90, 90]),
        framecolor="#000000",
    )
    fig.update_layout(
        font=dict(size=20, color='#222222', family='CMU Sans Serif'),
        height=370,
        width=740,
        margin=dict(l=0, r=0, t=0, b=0),
        autosize=False,
        legend=dict(
            x=0,
            y=0,
            xanchor='left',
            yanchor='bottom',
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#222222',
            borderwidth=1
        )
    )

    return fig
