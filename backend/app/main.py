from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import revenue, annotation, product
from app.core.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: dijalankan saat startup dan shutdown app.
    Berguna untuk warmup connection, cleanup resource, dll.
    """
    # Startup
    print(f" Starting {settings.app_name}")
    print(f" Debug mode {settings.debug}")
    print(f" Docs: http://localhost:8000/docs")

    yield

    print(" Shutting down, closing database connection...")
    await engine.dispose()

app = FastAPI(
    title=settings.app_name,
    description="Dashboard API for monitoring",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(revenue.router)
app.include_router(annotation.router)
app.include_router(product.router)

@app.get("/", tags=["health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "0.1.0"
    }