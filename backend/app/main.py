from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import (
    initialize_database,
    test_database_connection,
)

from app.api.products import router as products_router
from app.api.inventory import router as inventory_router
from app.api.customers import router as customers_router
from app.api.sales import router as sales_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "NextStore AI - Intelligent Retail Management "
        "and Multi-Agent Decision Support System"
    ),
    lifespan=lifespan,
)

app.include_router(products_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(sales_router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
def health_check():
    database_status = test_database_connection()

    return {
        "status": "healthy" if database_status else "degraded",
        "database": ("connected" if database_status else "disconnected"),
    }
