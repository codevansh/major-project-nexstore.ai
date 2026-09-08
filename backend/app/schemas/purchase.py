from pydantic import BaseModel, Field

class PurchaseItemRequest(BaseModel):
    barcode: str = Field(
        min_length=4,
        max_length=50
    )
    quantity: int = Field(
        ge=1
    )
    unit_cost: float = Field(
        ge=0
    )


class PurchaseCreate(BaseModel):
    invoice_number: str = Field(
        min_length=1,
        max_length=100
    )
    supplier_id: str
    store_id: str
    items: list[PurchaseItemRequest] = Field(
        min_length=1
    )
    discount: float = Field(
        default=0,
        ge=0
    )
    tax: float = Field(
        default=0,
        ge=0
    )


class PurchaseResponse(BaseModel):
    id: str
    invoice_number: str
    supplier_id: str
    store_id: str
    items: list[dict]
    subtotal: float
    discount: float
    tax: float
    total: float
    status: str