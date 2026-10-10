class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query=None, projection=None):
        query = query or {}
        return [document for document in self.documents if self._matches(document, query)]

    def find_one(self, query):
        return next(
            (document for document in self.documents if self._matches(document, query)),
            None,
        )

    @classmethod
    def _matches(cls, document, query):
        for field, expected in query.items():
            if field == "items.product_id":
                if not any(
                    item.get("product_id") == expected
                    for item in (document.get("items") or [])
                    if isinstance(item, dict)
                ):
                    return False
                continue
            actual = document.get(field)
            if isinstance(expected, dict):
                if "$gte" in expected and (actual is None or actual < expected["$gte"]):
                    return False
                if "$lte" in expected and (actual is None or actual > expected["$lte"]):
                    return False
            elif actual != expected:
                return False
        return True


class FakeDatabase:
    def __init__(self, sales=None, products=None):
        self.sales = FakeCollection(sales or [])
        self.products = FakeCollection(products or [])
        self.inventory = FakeCollection([])
        self.purchases = FakeCollection([])
        self.customers = FakeCollection([])
        self.suppliers = FakeCollection([])
        self.expenses = FakeCollection([])
