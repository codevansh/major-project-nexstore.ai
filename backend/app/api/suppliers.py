from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.core.database import get_database
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
)
from app.services.supplier_service import (
    create_supplier,
    get_supplier,
    get_suppliers,
    update_supplier,
    delete_supplier,
)


router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
)


def serialize_supplier(supplier: dict) -> dict:
    return {
        "id": str(supplier["_id"]),
        "name": supplier["name"],
        "phone": supplier.get("contact", {}).get("phone"),
        "email": supplier.get("contact", {}).get("email"),
        "address": supplier.get("address"),
        "status": supplier.get("status", "active"),
        "total_purchases": supplier.get(
            "purchase_summary", {}
        ).get("total_purchases", 0),
        "total_purchase_value": supplier.get(
            "purchase_summary", {}
        ).get("total_purchase_value", 0.0),
    }


@router.post("",response_model=SupplierResponse)
def create_supplier_api(
    supplier: SupplierCreate,
    db: Database = Depends(get_database),
):
    existing = db.suppliers.find_one({
        "contact.phone": supplier.phone
    })

    if supplier.phone and existing:
        raise HTTPException(
            status_code=400,
            detail="Supplier with this phone number already exists",
        )

    document = create_supplier(
        db=db,
        name=supplier.name,
        phone=supplier.phone,
        email=supplier.email,
        address=supplier.address,
    )

    return serialize_supplier(document)


@router.get("",response_model=list[SupplierResponse])
def list_suppliers(
    db: Database = Depends(get_database),
):
    suppliers = get_suppliers(db)

    return [
        serialize_supplier(supplier)
        for supplier in suppliers
    ]


@router.get(
    "/{supplier_id}",response_model=SupplierResponse)
def get_supplier_api(
    supplier_id: str,
    db: Database = Depends(get_database),
):
    supplier = get_supplier(
        db=db,
        supplier_id=supplier_id,
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    return serialize_supplier(supplier)


@router.put(
    "/{supplier_id}",response_model=SupplierResponse)
def update_supplier_api(
    supplier_id: str,
    supplier: SupplierUpdate,
    db: Database = Depends(get_database),
):
    updates = supplier.model_dump(
        exclude_unset=True
    )

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    updated = update_supplier(
        db=db,
        supplier_id=supplier_id,
        updates=updates,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    return serialize_supplier(updated)


@router.delete("/{supplier_id}")
def delete_supplier_api(
    supplier_id: str,
    db: Database = Depends(get_database),
):
    deleted = delete_supplier(
        db=db,
        supplier_id=supplier_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    return {
        "success": True,
        "message": "Supplier deleted successfully",
    }