from pydantic import BaseModel, Field


class SaleItemRequest(BaseModel):
    barcode: str = Field(min_length=4, max_length=50)

    quantity: int = Field(default=1, ge=1)


class SaleCheckoutRequest(BaseModel):
    store_id: str = Field(min_length=1, max_length=100)
    customer_id: str | None = None
    items: list[SaleItemRequest] = Field(min_length=1)
    payment_method: str = Field(default="cash", max_length=50)
    discount: float = Field(default=0, ge=0)


class BarcodeScanRequest(BaseModel):
    barcode: str = Field(min_length=4, max_length=50)
    store_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1)


class SaleItemResponse(BaseModel):
    product_id: str
    barcode: str
    name: str
    quantity: int
    unit_price: float
    subtotal: float


class SaleResponse(BaseModel):
    id: str
    invoice_number: str
    store_id: str
    customer_id: str | None
    items: list[SaleItemResponse]
    subtotal: float
    discount: float
    total: float
    payment_method: str
    status: str
