from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pymongo.database import Database

from app.core.database import get_database

from app.schemas.sale import (
    BarcodeScanRequest,
    SaleCheckoutRequest,
    SaleResponse,
)

from app.services.sale_service import (
    SalesService,
)

router = APIRouter(
    prefix="/sales",
    tags=["Sales"],
)


def get_sales_service(
    db: Database = Depends(get_database),
) -> SalesService:

    return SalesService(db)


def serialize_sale(
    sale: dict,
) -> dict:

    totals = sale.get("totals", {})
    payment = sale.get("payment", {})
    items = []

    for item in sale.get("items", []):
        items.append(
            {
                "product_id": item["product_id"],
                "barcode": item["barcode"],
                "name": item["name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "subtotal": item["subtotal"],
            }
        )

    return {
        "id": str(sale["_id"]),
        "invoice_number": sale["invoice_number"],
        "store_id": sale["store_id"],
        "customer_id": sale.get("customer_id"),
        "items": items,
        "subtotal": totals.get("subtotal", 0),
        "discount": totals.get("discount", 0),
        "total": totals.get("total", 0),
        "payment_method": payment.get("method", "cash"),
        "status": sale.get("status", "completed"),
    }


# BARCODE SCAN
@router.post("/scan")
def scan_barcode(
    request: BarcodeScanRequest,
    service: SalesService = Depends(get_sales_service),
):

    result = service.scan_barcode(request)

    if not result["success"]:
        if result["reason"] == ("product_not_found"):
            raise HTTPException(
                status_code=404,
                detail="Product barcode not found.",
            )

        if result["reason"] == ("inventory_not_found"):
            raise HTTPException(
                status_code=404,
                detail="Inventory not found for this product and store.",
            )

    return result


# CHECKOUT
@router.post(
    "/checkout",
    response_model=SaleResponse,
    status_code=201,
)
def checkout(
    request: SaleCheckoutRequest,
    service: SalesService = Depends(get_sales_service),
):
    try:
        sale = service.checkout(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if sale is None:
        raise HTTPException(
            status_code=500,
            detail="Sale could not be created.",
        )

    return serialize_sale(sale)


# GET SALES
@router.get(
    "",
    response_model=list[SaleResponse],
)
def get_sales(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: SalesService = Depends(get_sales_service),
):
    sales = service.get_sales(skip=skip, limit=limit)
    return [serialize_sale(sale) for sale in sales]


# GET SALE
@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
)
def get_sale(
    sale_id: str,
    service: SalesService = Depends(get_sales_service),
):
    sale = service.get_sale(sale_id)

    if sale is None:
        raise HTTPException(
            status_code=404,
            detail="Sale not found.",
        )

    return serialize_sale(sale)
