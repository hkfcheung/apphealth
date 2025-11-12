"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import HTTPException
from contextlib import asynccontextmanager
import logging
import json
import os

from app.config import settings
from app.database import init_db, engine, Session
from app.api import sites, state, admin, intelligence, sql_query
from app.polling import polling_scheduler
from app.models import Site

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    if settings.log_format != "json"
    else None,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Status Dashboard...")

    # Initialize database
    init_db()

    # Load seed data if database is empty
    await load_seed_data()

    # Start polling scheduler
    polling_scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down Status Dashboard...")
    polling_scheduler.stop()


async def load_seed_data():
    """Load seed configuration if database is empty."""
    with Session(engine) as session:
        existing_sites = session.exec(session.query(Site)).first()
        if existing_sites:
            logger.info("Database already contains sites, skipping seed data")
            return

    logger.info("Loading seed data...")
    try:
        with open("seed_config.json", "r") as f:
            seed_data = json.load(f)

        with Session(engine) as session:
            for site_data in seed_data.get("sites", []):
                site = Site(**site_data)
                session.add(site)
            session.commit()

        logger.info(f"Loaded {len(seed_data.get('sites', []))} sites from seed data")
    except FileNotFoundError:
        logger.warning("seed_config.json not found, skipping seed data")
    except Exception as e:
        logger.error(f"Error loading seed data: {e}")


# Create FastAPI app
app = FastAPI(
    title="Status Dashboard API",
    description="API for monitoring service status pages",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sites.router, prefix=settings.api_prefix)
app.include_router(state.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(intelligence.router, prefix=settings.api_prefix)
app.include_router(sql_query.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Status Dashboard API",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scheduler_running": polling_scheduler.is_running,
    }


@app.get("/api/downdetector/charts/{filename}")
async def get_downdetector_chart(filename: str):
    """Serve DownDetector chart screenshot."""
    charts_dir = "/data/downdetector_charts"
    filepath = os.path.join(charts_dir, filename)

    # Security: prevent directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Chart not found")

    return FileResponse(
        filepath,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
