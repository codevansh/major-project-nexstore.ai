from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.core.database import get_database
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


def get_product_service(
    db: Database = Depends(get_database),
) -> ProductService:

    return ProductService(db)


def serialize_product(product: dict) -> dict:
    return {
        "id": str(product["_id"]),
        "barcode": product["barcode"],
        "sku": product["sku"],
        "name": product["name"],
        "category": product["category"],
        "brand": product["brand"],
        "cost_price": product["pricing"]["cost"],
        "selling_price": product["pricing"]["selling"],
        "description": product.get("description"),
        "attributes": product.get("attributes", {}),
        "status": product.get("status", "active"),
    }


@router.post(
    "",
    response_model=ProductResponse,
    status_code=201,
)
def create_product(
    product: ProductCreate,
    service: ProductService = Depends(get_product_service),
):

    try:
        product_id = service.create_product(product)

    except Exception as exc:
        if "duplicate key" in str(exc).lower():
            raise HTTPException(
                status_code=409,
                detail="A product with this SKU already exists.",
            )

        raise HTTPException(
            status_code=500,
            detail="Unable to create product.",
        ) from exc

    created_product = service.get_product(product_id)

    return serialize_product(created_product)


@router.get(
    "",
    response_model=list[ProductResponse],
)
def get_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: ProductService = Depends(get_product_service),
):

    products = service.get_products(
        skip=skip,
        limit=limit,
    )

    return [serialize_product(product) for product in products]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
):

    product = service.get_product(product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    return serialize_product(product)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    product: ProductUpdate,
    service: ProductService = Depends(get_product_service),
):

    updated_product = service.update_product(
        product_id,
        product,
    )

    if updated_product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    return serialize_product(updated_product)


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
):

    deleted = service.delete_product(product_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    return {
        "message": "Product deleted successfully.",
        "product_id": product_id,
    }
