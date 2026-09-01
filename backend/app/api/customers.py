from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pymongo.database import Database

from app.core.database import get_database

from app.schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
)

from app.services.customer_service import (
    CustomerService,
)

router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)


def get_customer_service(
    db: Database = Depends(get_database),
) -> CustomerService:

    return CustomerService(db)


def serialize_customer(
    customer: dict,
) -> dict:

    contact = customer.get("contact", {})

    summary = customer.get("purchase_summary", {})

    return {
        "id": str(customer["_id"]),
        "name": customer["name"],
        "phone": contact.get("phone"),
        "email": contact.get("email"),
        "segment": customer.get("segment", "new"),
        "total_orders": summary.get("total_orders", 0),
        "total_spent": summary.get("total_spent", 0.0),
        "average_order_value": summary.get("average_order_value", 0.0),
    }


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=201,
)
def create_customer(
    customer: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
):

    if customer.phone:

        existing = service.get_customer_by_phone(customer.phone)

        if existing:

            raise HTTPException(
                status_code=409,
                detail="Customer with this phone number already exists.",
            )

    customer_id = service.create_customer(customer)

    created = service.get_customer(customer_id)

    return serialize_customer(created)


@router.get(
    "",
    response_model=list[CustomerResponse],
)
def get_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: CustomerService = Depends(get_customer_service),
):

    customers = service.get_customers(skip=skip, limit=limit)

    return [serialize_customer(customer) for customer in customers]


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def get_customer(
    customer_id: str,
    service: CustomerService = Depends(get_customer_service),
):

    customer = service.get_customer(customer_id)

    if customer is None:

        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    return serialize_customer(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def update_customer(
    customer_id: str,
    customer: CustomerUpdate,
    service: CustomerService = Depends(get_customer_service),
):

    updated = service.update_customer(customer_id, customer)

    if updated is None:

        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    return serialize_customer(updated)


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: str,
    service: CustomerService = Depends(get_customer_service),
):

    deleted = service.delete_customer(customer_id)

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    return {
        "message": "Customer deleted successfully.",
        "customer_id": customer_id,
    }
