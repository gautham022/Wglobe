import re
import bcrypt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from supabase_client import get_supabase_client

router = APIRouter()


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


def _validate_signup_payload(payload: SignupRequest):
    name = payload.name.strip()
    email = str(payload.email).strip().lower()
    password = payload.password

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Email must be a valid email address")

    if not isinstance(password, str) or not password.strip():
        raise HTTPException(status_code=400, detail="Password is required")

    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    if not any(char.isupper() for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase character")

    if not any(char.islower() for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase character")

    if not any(char.isdigit() for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")

    return name, email, password


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest):
    try:
        name, email, password = _validate_signup_payload(payload)
        supabase = get_supabase_client()

        existing_response = supabase.table("users").select("email").eq("email", email).execute()
        existing_data = getattr(existing_response, "data", None) or []

        if any(item.get("email") == email for item in existing_data if isinstance(item, dict)):
            raise HTTPException(status_code=409, detail="A user with this email already exists")

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        insert_payload = {
            "name": name,
            "email": email,
            "password_hash": password_hash,
        }

        insert_response = supabase.table("users").insert(insert_payload).execute()
        inserted_data = getattr(insert_response, "data", None) or []

        if not inserted_data:
            raise HTTPException(status_code=500, detail="Failed to create user")

        created_user = inserted_data[0]
        return {
            "id": created_user.get("id"),
            "name": created_user.get("name"),
            "email": created_user.get("email"),
            "password_hash": created_user.get("password_hash"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(exc)}") from exc

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(payload: LoginRequest):
    client = get_supabase_client()

    try:
        result = client.table("users").select("*").eq("email", payload.email).execute()

        if not result.data:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user = result.data[0]

        if not pwd_context.verify(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return {
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")