from datetime import datetime, timezone


def user_document(
    name: str,
    email: str,
    hashed_password: str,
) -> dict:
    return {
        "name": name,
        "email": email,
        "hashed_password": hashed_password,
        "role": "manager",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }