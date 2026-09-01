from pydantic import BaseModel, Field


class InventoryCreate(BaseModel):
    product_id: str
    store_id: str

    available: int = Field(default=0, ge=0)
    reserved: int = Field(default=0, ge=0)
    damaged: int = Field(default=0, ge=0)

    reorder_level: int = Field(default=10, ge=0)
    reorder_quantity: int = Field(default=50, ge=1)


class InventoryUpdate(BaseModel):
    available: int | None = Field(default=None,ge=0)

    reserved: int | None = Field(default=None,ge=0)

    damaged: int | None = Field(default=None,ge=0)

    reorder_level: int | None = Field(default=None,ge=0)

    reorder_quantity: int | None = Field(default=None,ge=1)


class InventoryResponse(BaseModel):
    id: str

    product_id: str
    store_id: str

    available: int
    reserved: int
    damaged: int

    reorder_level: int
    reorder_quantity: int

    stock_status: str
