# Pregnancy Safe Route Application

This application suggests the safest and shortest route for pregnant women to reach a clinic, considering their pregnancy week and risk level.

## Prerequisites

- Python 3.8+
- Dependencies: `fastapi`, `uvicorn`, `geopandas`, `networkx`, `shapely` (installed in `venv`)

## Data Setup

Ensure the following files are in the project directory:
1. `hotosm_npl_roads_lines_geojson.geojson` (Road Network)
2. `bagmati_clinics_scored.geojson` (Clinic Locations)

## Running the Application

1. **Activate the virtual environment**:
   ```powershell
   .\venv\Scripts\activate
   ```

2. **Run the FastAPI Server**:
   ```powershell
   uvicorn app:app --reload
   ```

3. **Open the Web Interface**:
   - Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)

## Features

- **Interactive Map**: Click to set your starting location.
- **Risk Assessment**:
    - **Low Risk**: Finds the shortest path with minor safety considerations.
    - **High Risk / Late Pregnancy (>28 weeks)**: Heavily penalizes bumpy/unpaved roads to ensure safety.
- **Visual Feedback**: Routes are color-coded (Blue=Standard, Green=Safe).

## Notes

- The first time you run the app, it will take a few minutes to load and build the road graph from the large GeoJSON file. Please be patient.
- The routing is currently filtered to the Bagmati Province / Kathmandu area for performance.
