from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, posts, alerts, authority, trends, copilot, voice_sos, predictions, evacuation, fake_reports, resource_routes, facilities, incident_chat, missing_persons
from .database import engine, Base, SessionLocal
from .routers.facilities import seed_facilities_if_empty

# Create tables
Base.metadata.create_all(bind=engine)

# Seed initial coastal facilities if empty
db_init = SessionLocal()
try:
    seed_facilities_if_empty(db_init)
finally:
    db_init.close()

app = FastAPI(title="Coastal Threat Alert System API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(alerts.router)
app.include_router(authority.router)
app.include_router(trends.router)
app.include_router(copilot.router)
app.include_router(voice_sos.router)
app.include_router(predictions.router)
app.include_router(evacuation.router)
app.include_router(fake_reports.router)
app.include_router(resource_routes.router)
app.include_router(facilities.router)
app.include_router(incident_chat.router)
app.include_router(missing_persons.router)

# Mount static files (Frontend)
# Serve HTML files from parent directory
import os
from fastapi.responses import FileResponse

frontend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Serve frontend.html as the default index
@app.get("/", response_class=FileResponse)
async def root():
    return os.path.join(frontend_dir, "frontend.html")

# Mount remaining static files
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8001, reload=True)