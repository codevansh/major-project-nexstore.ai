from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.core.database import get_database
from app.services.analytics_service import AnalyticsService


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/overview")
def get_overview(
    db: Database = Depends(get_database),
):
    try:
        service = AnalyticsService(db)
        return service.get_overview()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/sales")
def get_sales_analytics(
    db: Database = Depends(get_database),
):
    try:
        service = AnalyticsService(db)
        return service.get_sales_analytics()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/top-products")
def get_top_products(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    db: Database = Depends(get_database),
):
    try:
        service = AnalyticsService(db)
        return service.get_top_products(
            limit=limit
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/low-stock")
def get_low_stock(
    db: Database = Depends(get_database),
):
    try:
        service = AnalyticsService(db)
        return service.get_low_stock()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/inventory")
def get_inventory_analytics(
    db: Database = Depends(get_database),
):
    try:
        service = AnalyticsService(db)
        return service.get_inventory_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products")
def get_product_analytics(
    db: Database = Depends(get_database),
):
    try:
        service = AnalyticsService(db)
        return service.get_product_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/customers")
def get_customer_analytics(
    db: Database = Depends(get_database),
):
    try:
        service = AnalyticsService(db)
        return service.get_customer_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))