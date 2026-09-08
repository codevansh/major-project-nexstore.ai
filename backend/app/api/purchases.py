from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pymongo.database import Database

from app.core.database import get_database

from app.schemas.purchase import (
    PurchaseCreate,
    PurchaseResponse,
)

from app.services.purchase_service import (
    PurchaseService,
)


router = APIRouter(
    prefix="/purchases",
    tags=["Purchases"],
)


def get_purchase_service(
    db: Database = Depends(
        get_database
    ),
) -> PurchaseService:

    return PurchaseService(db)


def serialize_purchase(
    purchase: dict,
) -> dict:

    totals = purchase.get(
        "totals",
        {}
    )

    return {
        "id": str(
            purchase["_id"]
        ),

        "invoice_number":
            purchase[
                "invoice_number"
            ],

        "supplier_id":
            purchase[
                "supplier_id"
            ],

        "store_id":
            purchase[
                "store_id"
            ],

        "items":
            purchase.get(
                "items",
                []
            ),

        "subtotal":
            totals.get(
                "subtotal",
                0
            ),

        "discount":
            totals.get(
                "discount",
                0
            ),

        "tax":
            totals.get(
                "tax",
                0
            ),

        "total":
            totals.get(
                "total",
                0
            ),

        "status":
            purchase.get(
                "status",
                "received"
            ),
    }


@router.post("",response_model=PurchaseResponse,status_code=201)
def create_purchase(
    purchase: PurchaseCreate,
    service: PurchaseService = Depends(
        get_purchase_service
    ),
):

    try:
        result = service.create_purchase(
            purchase
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return serialize_purchase(
        result
    )


@router.get("",response_model=list[PurchaseResponse])
def get_purchases(
    skip: int = Query(
        default=0,
        ge=0
    ),

    limit: int = Query(
        default=50,
        ge=1,
        le=100
    ),

    service: PurchaseService = Depends(
        get_purchase_service
    ),
):

    purchases = service.get_purchases(
        skip=skip,
        limit=limit
    )

    return [
        serialize_purchase(purchase)
        for purchase in purchases
    ]


@router.get("/{purchase_id}",response_model=PurchaseResponse)
def get_purchase(
    purchase_id: str,
    service: PurchaseService = Depends(
        get_purchase_service
    ),
):

    purchase = service.get_purchase(
        purchase_id
    )

    if purchase is None:
        raise HTTPException(
            status_code=404,
            detail="Purchase not found.",
        )

    return serialize_purchase(
        purchase
    )