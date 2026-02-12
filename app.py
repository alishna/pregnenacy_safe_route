from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from route_engine import SafeRouter
import uvicorn
import os

app = FastAPI(title="Pregnancy Safe Route API")

# Global router instance
router = None

@app.on_event("startup")
async def startup_event():
    global router
    road_file = 'dataset/hotosm_npl_roads_lines_geojson.geojson'
    clinic_file = 'dataset/nepal.geojson'
    
    if os.path.exists(road_file) and os.path.exists(clinic_file):
        print("Initializing Routing Engine... (This may take a minute)")
        router = SafeRouter(road_file, clinic_file)
        print("Routing Engine Ready!")
    else:
        print("Warning: Data files not found. Routing will fail.")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.get("/api/route")
async def get_route(
    lat: float = Query(..., description="Start Latitude"),
    lon: float = Query(..., description="Start Longitude"),
    week: int = Query(..., description="Pregnancy Week"),
    risk: str = Query(..., description="Risk Level (low/high)")
):
    global router
    if not router:
        raise HTTPException(status_code=503, detail="Routing engine not initialized")
    
    try:
        result = router.get_safest_route(lat, lon, week, risk)
        if not result:
            raise HTTPException(status_code=404, detail="No route found")
        return result
    except Exception as e:
        print(f"Error calculating route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
