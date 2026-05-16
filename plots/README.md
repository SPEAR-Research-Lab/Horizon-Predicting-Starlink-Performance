# Starlink Network Performance Analysis & Visualization

A comprehensive research project for analyzing and visualizing network performance metrics from Starlink. This project processes data from multiple measurement platforms (Cloudflare AIM, M-Lab NDT7) and generates interactive visualizations to compare network performance across countries and identify the impact of data quality filtering techniques.

> **Note:** The notebooks contain interactive Plotly visualizations that don't render on GitHub. Clone the repository and run the notebooks locally with Jupyter to view all interactive plots.

## Project Overview

This repository contains the following analysis modules:

1. **Anomaly Filtration Analysis** (`anomaly-filtration-plots/`) - Evaluates the impact of anomaly detection and filtration on Starlink performance metrics
2. **Client-Server Filtering Analysis** (`map-plots/`) - Geographic performance visualization and client-server filtering comparisons
3. **Distribution Comparison (JSD)** (`statistical-analysis-plots/`) - Investigates and compares statistical distributions between NDT7 and Cloudflare datasets
4. **Weather Validation** (`weather-validation-plots/`) - Weather correlation analysis and PLS-derived index validation
5. **Leave-One-Out Analysis** (`leave-one-out/`) - Feature importance via leave-one-out evaluation

## Getting Started

### Prerequisites

- Python 3.13+
- Jupyter Notebook or JupyterLab
- LaTeX (required for some plots that generate publication-quality figures)

### Installation

**Set up data files:**
   
   The data files used in this project are too large to commit to the repository. You can either generate them using the scripts in the `data-collection` directory or prepare your own CSV data files and place them in the appropriate directories:
   
   - `anomaly-filtration-plots/data/`
   - `map-plots/data/`
   - `statistical-analysis-plots/data/`
   - `weather-validation-plots/data/`
   - `leave-one-out/data/`

**To generate data files automatically:**
   
   Run the data generation script from the root directory:
   ```bash
   python data-collection/scripts/data_for_plots.py
   ```
   
   This will generate some of the data-files required by the Statistical Analysis and Map Plots. The other files are generated after anomaly filtration or training.