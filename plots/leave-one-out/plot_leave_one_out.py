import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import rcParams
from matplotlib.ticker import MaxNLocator
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

FONT_DIR = ROOT.parent / "cmu-sans-serif" / "Sans"
for font_file in FONT_DIR.glob("*.ttf"):
    fm.fontManager.addfont(str(font_file))

rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["CMU Sans Serif"]
plt.rcParams.update({
    "text.usetex": False,
    "font.size": 20,
    "pdf.fonttype": 42,
})

EVAL_START = "2025-11-24"
EVAL_END = "2025-11-30"
FULL_HOURS = pd.date_range(
    EVAL_START,
    pd.Timestamp(EVAL_END) + pd.Timedelta(hours=23),
    freq='h', tz='UTC',
)

colors = plt.get_cmap("tab10").colors
window_size = 5


def load_hourly(csv_path):
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    if 'noberlin' in df.columns:
        df = df.rename(columns={'noberlin': 'nocity'})
    df['timestamp'] = df['timestamp'].dt.floor('h')
    df = df.groupby('timestamp')[['gt', 'full', 'nocity']].mean().reset_index()
    df = df.set_index('timestamp').reindex(FULL_HOURS).reset_index()
    df = df.rename(columns={'index': 'timestamp'})
    return df


def midnight_positions():
    return [day * 24 for day in range(8)]


def eight_hour_positions():
    midnights = set(midnight_positions())
    all_pos, non_midnight = [], []
    for day in range(7):
        for h in (0, 8, 16):
            pos = day * 24 + h
            all_pos.append(pos)
            if pos not in midnights:
                non_midnight.append(pos)
    all_pos.append(7 * 24)
    return all_pos, non_midnight


def setup_xticks(ax):
    all_8h, non_midnight = eight_hour_positions()

    hour_labels = []
    for day in range(7):
        for h in (0, 8, 16):
            hour_labels.append(str(h))
    hour_labels.append('0')

    ax.set_xticks(all_8h)
    ax.set_xticklabels(hour_labels, fontsize=18)
    ax.tick_params(axis='x', which='major', length=4, width=0.8)

    for day_offset in range(7):
        ts = pd.Timestamp(EVAL_START, tz='UTC') + pd.Timedelta(days=day_offset)
        mid_x = day_offset * 24 + 12
        ax.text(mid_x, 1.02, ts.strftime('%a'), transform=ax.get_xaxis_transform(),
                ha='center', va='bottom', fontsize=20)

    for p in non_midnight:
        ax.axvline(x=p, color='gray', linewidth=0.5, linestyle='-', alpha=0.15)

    for mp in midnight_positions():
        ax.axvline(x=mp, color='gray', linewidth=0.7, linestyle='-', alpha=0.4)


CITIES = [
    {
        "key": "berlin", "label": "Berlin",
        "lat_csv": DATA_DIR / "berlin_hourly_latency.csv",
        "tput_csv": DATA_DIR / "berlin_hourly_throughput.csv",
    },
    {
        "key": "santiago", "label": "Santiago",
        "lat_csv": DATA_DIR / "santiago_hourly_latency.csv",
        "tput_csv": DATA_DIR / "santiago_hourly_throughput.csv",
    },
    {
        "key": "yangon", "label": "Yangon",
        "lat_csv": DATA_DIR / "yangon_hourly_latency.csv",
        "tput_csv": DATA_DIR / "yangon_hourly_throughput.csv",
    },
]

for city in CITIES:
    key = city['key']
    label = city['label']
    print(f"Processing {label}...")

    try:
        df_lat = load_hourly(city['lat_csv'])
        df_tput = load_hourly(city['tput_csv'])
    except FileNotFoundError as e:
        print(f"  SKIP {label}: {e}")
        continue

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(df_lat))
    y_gt = df_lat['gt'].interpolate().rolling(window=window_size, center=True, min_periods=1).mean()
    y_full = df_lat['full'].rolling(window=window_size, center=True, min_periods=1).mean()
    y_nocity = df_lat['nocity'].rolling(window=window_size, center=True, min_periods=1).mean()

    ax.plot(x, y_gt, '-', color=colors[0], linewidth=2, label='Ground Truth')
    ax.plot(x, y_full, '--', color=colors[1], linewidth=2, label='Full Model')
    ax.plot(x, y_nocity, ':', color=colors[2], linewidth=2.5, label=f'No-{label} Model')

    ax.set_ylabel('ms')
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=False))
    setup_xticks(ax)

    plt.tight_layout()
    out_lat = ROOT / f'{key}_latency'
    plt.savefig(f'{out_lat}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{out_lat}.pdf', bbox_inches='tight', format='pdf')
    plt.close()
    print(f"  Saved: {out_lat}.png/pdf")

    fig, ax = plt.subplots(figsize=(10, 5))
    x2 = np.arange(len(df_tput))
    y_gt2 = df_tput['gt'].interpolate().rolling(window=window_size, center=True, min_periods=1).mean()
    y_full2 = df_tput['full'].rolling(window=window_size, center=True, min_periods=1).mean()
    y_nocity2 = df_tput['nocity'].rolling(window=window_size, center=True, min_periods=1).mean()

    ax.plot(x2, y_gt2, '-', color=colors[0], linewidth=2, label='Ground Truth')
    ax.plot(x2, y_full2, '--', color=colors[1], linewidth=2, label='Full Model')
    ax.plot(x2, y_nocity2, ':', color=colors[2], linewidth=2.5, label=f'No-{label} Model')

    ax.set_ylabel('Mbps')
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=False))
    setup_xticks(ax)

    ax.legend(
        frameon=True, facecolor='white', edgecolor='black', framealpha=0.9,
        loc='upper right', fontsize=14, handlelength=1.5, handletextpad=0.5, borderpad=0.4,
    )

    plt.tight_layout()
    out_tput = ROOT / f'{key}_throughput'
    plt.savefig(f'{out_tput}.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{out_tput}.pdf', bbox_inches='tight', format='pdf')
    plt.close()
    print(f"  Saved: {out_tput}.png/pdf")

print("\nDone!")
