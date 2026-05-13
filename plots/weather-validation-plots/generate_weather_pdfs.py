import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from enum import Enum
from pathlib import Path

import weather_validation_nl
import weather_validation_ro
from constants import feature_to_y_label as _feature_to_y_label, output_dir

feature_to_y_label = {k: v.replace('\\%', '%') for k, v in _feature_to_y_label.items()}

FONT_DIR = Path(__file__).parent.parent / "cmu-sans-serif" / "Sans"
if FONT_DIR.exists():
    import matplotlib.font_manager as fm
    for font_file in FONT_DIR.glob("*.ttf"):
        fm.fontManager.addfont(str(font_file))

rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["CMU Sans Serif"]
plt.rcParams.update({
    "text.usetex": False,
    "font.size": 20,
    "pdf.fonttype": 42,
})

colors = plt.get_cmap("tab10").colors

feature_to_shorthand = {
    'precipitation': 'pp',
    'wind_speed_10m': 'wind',
    'cloud_cover': 'cc',
    'temperature_2m': 'temp'
}


class Country(Enum):
    RO = 'Romania'
    NL = 'Netherlands'


def add_time_vertical_lines_and_ticks(ax, times):
    t_min, t_max = times.min(), times.max()
    start_date = t_min.normalize()
    end_date = t_max.normalize() + pd.Timedelta(days=1)

    tick_times = []
    tick_labels = []
    midnight_times = []
    non_midnight_times = []

    day = start_date
    while day <= end_date:
        for hour in (0, 8, 16):
            t = day + pd.Timedelta(hours=hour)
            if t < t_min - pd.Timedelta(hours=1) or t > t_max + pd.Timedelta(hours=1):
                continue
            tick_times.append(t)
            tick_labels.append(str(hour))
            if hour == 0:
                midnight_times.append(t)
            else:
                non_midnight_times.append(t)
        day += pd.Timedelta(days=1)

    ax.set_xticks(tick_times)
    ax.set_xticklabels(tick_labels, fontsize=18)
    ax.tick_params(axis='x', which='major', length=4, width=0.8, rotation=0)

    day = start_date
    while day <= end_date:
        midday = day + pd.Timedelta(hours=12)
        if midday >= t_min and midday <= t_max:
            day_name = day.strftime('%a')
            ax.text(midday, 1.02, day_name,
                    transform=ax.get_xaxis_transform(),
                    ha='center', va='bottom', fontsize=20)
        day += pd.Timedelta(days=1)

    for t in non_midnight_times:
        ax.axvline(x=t, color='gray', linewidth=0.5, linestyle='-', alpha=0.15)

    for t in midnight_times:
        ax.axvline(x=t, color='gray', linewidth=0.7, linestyle='-', alpha=0.4)


def plot_and_save(merged_df, country_type, station):
    knmi_to_open_meteo_names = {
        'cloud_cover_octa': 'cloud_cover',
        'wind_speed': 'wind_speed_10m',
        'precipitation_total': 'precipitation',
        'temperature': 'temperature_2m'
    }

    for i, (feature, label) in enumerate(feature_to_y_label.items()):
        if country_type == Country.NL:
            knmi_col = next((k for k, v in knmi_to_open_meteo_names.items() if v == feature), None)
            if knmi_col is None or knmi_col not in merged_df.columns or feature not in merged_df.columns:
                continue
            y1 = pd.to_numeric(merged_df[knmi_col], errors='coerce')
            y2 = pd.to_numeric(merged_df[feature], errors='coerce')
            y1 = y1.rolling(window=5, center=True).mean()
            y2 = y2.rolling(window=5, center=True).mean()
        elif country_type == Country.RO:
            station_col = f"{feature}_station"
            om_col = f"{feature}_openmeteo"
            if station_col not in merged_df.columns or om_col not in merged_df.columns:
                continue
            y1 = pd.to_numeric(merged_df[station_col], errors='coerce')
            y2 = pd.to_numeric(merged_df[om_col], errors='coerce')
        else:
            continue

        if y1.dropna().empty and y2.dropna().empty:
            continue

        times = pd.to_datetime(merged_df['datetime'])

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(times, y1, label='Weather station', color=colors[0], linewidth=2, alpha=0.8, linestyle='--')
        ax.plot(times, y2, label='Open-Meteo', color=colors[1], linewidth=2, alpha=0.8, linestyle='-')
        ax.set_ylabel(label)

        if i == 0:
            ax.legend(
                frameon=True, facecolor='white', edgecolor='black',
                framealpha=0.8, loc='upper left',
            )

        add_time_vertical_lines_and_ticks(ax, times)
        fig.tight_layout()

        station_short = station.split(' ')[0].lower()
        out_path = output_dir / f"{feature_to_shorthand[feature]}-{station_short}.pdf"
        fig.savefig(out_path, format="pdf", bbox_inches="tight")
        plt.close()
        print(f"  Saved: {out_path}")


def process_country(country, summary_file, generate_func):
    if not (output_dir / summary_file).exists():
        print(f"Generating {country.value} validation data...")
        generate_func()
    else:
        print(f"{country.value} validation data already exists.")

    summary = pd.read_json(output_dir / summary_file)
    print(f"Found {len(summary)} stations in {country.value}")

    for _, row in summary.iterrows():
        station = row['station']
        merged_path = output_dir / f"{station}_validation.csv"
        if not merged_path.exists():
            print(f"  SKIP {station}: validation CSV not found")
            continue
        merged = pd.read_csv(merged_path)
        merged['datetime'] = pd.to_datetime(merged['datetime'])
        print(f"Plotting station: {station}")
        plot_and_save(merged, country, station)


print("=== Romania ===")
process_country(Country.RO, 'romania_validation_summary.json', weather_validation_ro.main)

print("\n=== Netherlands ===")
process_country(Country.NL, 'netherlands_validation_summary.json', weather_validation_nl.main)

print("\nDone!")
