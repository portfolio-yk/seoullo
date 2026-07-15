from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.emotions import router as emotions_router
from app.api.interactions import router as interactions_router
from app.api.maps import router as maps_router
from app.api.places import router as places_router
from app.api.reviews import router as reviews_router
from app.api.tags import router as tags_router
from app.core.config import get_settings
from app.db.session import SessionLocal, init_db
from app.services.seed import seed_dataset

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with SessionLocal() as session:
        # Always run the idempotent loader so newly added category files are
        # discovered without requiring a manual database reset.
        seed_dataset(session, settings.data_directory)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(emotions_router, prefix=settings.api_prefix)
app.include_router(places_router, prefix=settings.api_prefix)
app.include_router(reviews_router, prefix=settings.api_prefix)
app.include_router(interactions_router, prefix=settings.api_prefix)
app.include_router(tags_router, prefix=settings.api_prefix)
app.include_router(maps_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": "Seoullo API", "docs": "/docs", "health": f"{settings.api_prefix}/health"}
