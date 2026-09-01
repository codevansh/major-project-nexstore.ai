from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from app.models.customer import customer_document
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
)


class CustomerService:

    def __init__(self, db: Database):
        self.collection = db.customers

    def create_customer(
        self,
        customer: CustomerCreate,
    ) -> str:

        document = customer_document(
            name=customer.name,
            phone=customer.phone,
            email=customer.email,
        )

        result = self.collection.insert_one(document)

        return str(result.inserted_id)

    def get_customer(
        self,
        customer_id: str,
    ):

        if not ObjectId.is_valid(customer_id):
            return None

        return self.collection.find_one({"_id": ObjectId(customer_id)})

    def get_customer_by_phone(
        self,
        phone: str,
    ):

        return self.collection.find_one({"contact.phone": phone})

    def get_customers(
        self,
        skip: int = 0,
        limit: int = 50,
    ):

        return list(self.collection.find().skip(skip).limit(limit))

    def update_customer(
        self,
        customer_id: str,
        customer: CustomerUpdate,
    ):

        if not ObjectId.is_valid(customer_id):
            return None

        data = customer.model_dump(exclude_unset=True)

        if "phone" in data:
            data["contact.phone"] = data.pop("phone")

        if "email" in data:
            data["contact.email"] = data.pop("email")

        if not data:
            return self.get_customer(customer_id)

        data["updated_at"] = datetime.now(timezone.utc)

        self.collection.update_one({"_id": ObjectId(customer_id)}, {"$set": data})

        return self.get_customer(customer_id)

    def delete_customer(
        self,
        customer_id: str,
    ) -> bool:

        if not ObjectId.is_valid(customer_id):
            return False

        result = self.collection.delete_one({"_id": ObjectId(customer_id)})

        return result.deleted_count > 0
