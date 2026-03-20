# Starlink Network Performance Analysis & Visualization

A comprehensive research project for analyzing and visualizing network performance metrics from Starlink and terrestrial ISPs. This project processes data from multiple measurement platforms (Cloudflare AIM, M-Lab NDT7) and generates interactive visualizations to compare network performance across countries and identify the impact of data quality filtering techniques.

> **Note:** The notebooks contain interactive Plotly visualizations that don't render on GitHub. Clone the repository and run the notebooks locally with Jupyter to view all interactive plots.

## Project Overview

This repository contains three main analysis modules:

1. **Anomaly Filtration Analysis** - Evaluates the impact of anomaly detection and filtration on Starlink performance metrics
2. **Client-Server Filtering Analysis** - Compares network performance before and after applying geographic/distance-based filtering
3. **Distribution Comparison (JSD)** - Investigates and compares statistical distributions between NDT7 and Cloudflare datasets

## Getting Started

### Prerequisites

- Python 3.11+
- Jupyter Notebook or JupyterLab
- Virtual environment (recommended)

### Installation

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/TUD-BScResearchProject-6079/plots-generation.git
   cd plots-generation
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Set up data files:**
   
   The data files used in this project are too large to commit to the repository. You will need to prepare and place your own CSV data files in the appropriate directories:
   
   - `anomaly-filtration-plots/data/`
   - `map-plots/data/`
   - `jsd-plots/data/`

   The data required and how to obtain it is described in each individual Jupyter Notebook.