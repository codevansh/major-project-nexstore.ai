from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import user_document
from app.schemas.user import TokenResponse, UserRegister, UserResponse

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user: UserRegister,
    db: Database = Depends(get_database),
):
    existing_user = db.users.find_one({"email": user.email.lower()})

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    document = user_document(
        name=user.name,
        email=user.email.lower(),
        hashed_password=hash_password(user.password),
    )

    try:
        result = db.users.insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    return {
        "id": str(result.inserted_id),
        "name": document["name"],
        "email": document["email"],
        "role": document["role"],
        "is_active": document["is_active"],
    }


@router.post("/login", response_model=TokenResponse)
def login_user(
    credentials: OAuth2PasswordRequestForm = Depends(),
    db: Database = Depends(get_database),
):
    user = db.users.find_one({"email": credentials.username.lower()})

    if not user or not user.get("hashed_password") or not verify_password(
        credentials.password,
        user["hashed_password"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    access_token = create_access_token(
        {
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_authenticated_user(
    current_user: dict = Depends(get_current_user),
):
    return current_user
