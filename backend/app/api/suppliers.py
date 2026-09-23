<<<<<<< HEAD
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

=======
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from app.services.supplier_service import SupplierService

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


def get_supplier_service(db: Database = Depends(get_database)) -> SupplierService:
    return SupplierService(db)


def serialize_supplier(supplier: dict) -> dict:
    contact = supplier.get("contact", {})
    summary = supplier.get("purchase_summary", {})
    return {
        "id": str(supplier["_id"]),
        "name": supplier["name"],
        "phone": contact.get("phone"),
        "email": contact.get("email"),
        "address": supplier.get("address"),
        "status": supplier.get("status", "active"),
        "purchase_summary": {
            "total_purchases": summary.get("total_purchases", 0),
            "total_purchase_value": summary.get("total_purchase_value", 0.0),
        },
        "created_at": supplier["created_at"],
        "updated_at": supplier["updated_at"],
    }


@router.post("", response_model=SupplierResponse, status_code=201)
def create_supplier(
    supplier: SupplierCreate,
    service: SupplierService = Depends(get_supplier_service),
):
    try:
        supplier_id = service.create_supplier(supplier)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="A supplier with this email already exists.",
        ) from exc

    return serialize_supplier(service.get_supplier(supplier_id))


@router.get("", response_model=list[SupplierResponse])
def get_suppliers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: SupplierService = Depends(get_supplier_service),
):
    return [
        serialize_supplier(supplier)
        for supplier in service.get_suppliers(skip=skip, limit=limit)
    ]


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: str,
    service: SupplierService = Depends(get_supplier_service),
):
    supplier = service.get_supplier(supplier_id)
    if supplier is None or supplier.get("status") != "active":
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return serialize_supplier(supplier)


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: str,
    supplier: SupplierUpdate,
    service: SupplierService = Depends(get_supplier_service),
):
    try:
        updated = service.update_supplier(supplier_id, supplier)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="A supplier with this email already exists.",
        ) from exc

    if updated is None or updated.get("status") != "active":
        raise HTTPException(status_code=404, detail="Supplier not found.")
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)
    return serialize_supplier(updated)


@router.delete("/{supplier_id}")
<<<<<<< HEAD
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
=======
def delete_supplier(
    supplier_id: str,
    service: SupplierService = Depends(get_supplier_service),
):
    if not service.deactivate_supplier(supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return {"message": "Supplier deactivated successfully.", "supplier_id": supplier_id}
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)
