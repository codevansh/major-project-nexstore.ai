from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.core.database import get_database
from app.schemas.inventory import (
    InventoryCreate,
    InventoryResponse,
    InventoryUpdate,
)
from app.services.inventory_service import InventoryService

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


def get_inventory_service(
    db: Database = Depends(get_database),
) -> InventoryService:

    return InventoryService(db)


def calculate_stock_status(
    available: int,
    reorder_level: int,
) -> str:

    if available <= 0:
        return "out_of_stock"

    if available <= reorder_level:
        return "low_stock"

    return "in_stock"


def serialize_inventory(
    inventory: dict,
) -> dict:

    available = inventory["stock"]["available"]

    reorder_level = inventory["thresholds"]["reorder_level"]

    return {
        "id": str(inventory["_id"]),
        "product_id": inventory["product_id"],
        "store_id": inventory["store_id"],
        "available": available,
        "reserved": inventory["stock"]["reserved"],
        "damaged": inventory["stock"]["damaged"],
        "reorder_level": reorder_level,
        "reorder_quantity": inventory["reorder"]["recommended_quantity"],
        "stock_status": calculate_stock_status(
            available,
            reorder_level,
        ),
    }


@router.post("",response_model=InventoryResponse,status_code=201)
def create_inventory(
    inventory: InventoryCreate,
    service: InventoryService = Depends(get_inventory_service),
):

    try:
        inventory_id = service.create_inventory(inventory)
    except Exception as exc:
        if "duplicate key" in str(exc).lower():
            raise HTTPException(
                status_code=409,
                detail=("Inventory already exists " "for this product and store."),
            )
        raise HTTPException(
            status_code=500,
            detail="Unable to create inventory.",
        ) from exc

    created_inventory = service.get_inventory(inventory_id)

    return serialize_inventory(created_inventory)


@router.get("", response_model=list[InventoryResponse])
def get_inventory(
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    service: InventoryService = Depends(get_inventory_service),
):

    inventory = service.get_all_inventory(
        skip=skip,
        limit=limit,
    )

    return [serialize_inventory(item) for item in inventory]


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory_item(
    inventory_id: str,
    service: InventoryService = Depends(get_inventory_service),
):

    inventory = service.get_inventory(inventory_id)

    if inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Inventory record not found.",
        )

    return serialize_inventory(inventory)


@router.get("/product/{product_id}", response_model=InventoryResponse)
def get_product_inventory(
    product_id: str,
    store_id: str,
    service: InventoryService = Depends(get_inventory_service),
):

    inventory = service.get_inventory_by_product(
        product_id,
        store_id,
    )

    if inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Inventory record not found.",
        )

    return serialize_inventory(inventory)


@router.patch("/{inventory_id}",response_model=InventoryResponse)
def update_inventory(
    inventory_id: str,
    inventory: InventoryUpdate,
    service: InventoryService = Depends(get_inventory_service),
):

    updated_inventory = service.update_inventory(
        inventory_id,
        inventory,
    )

    if updated_inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Inventory record not found.",
        )

    return serialize_inventory(updated_inventory)


@router.delete("/{inventory_id}")
def delete_inventory(
    inventory_id: str,
    service: InventoryService = Depends(get_inventory_service),
):

    deleted = service.delete_inventory(inventory_id)

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Inventory record not found.",
        )

    return {
        "message": ("Inventory deleted successfully."),
        "inventory_id": inventory_id,
    }
