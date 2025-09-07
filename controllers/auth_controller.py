"""
Authentication controller
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from utils.auth import authenticate_user, create_access_token, get_current_user

router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict


class RefreshTokenRequest(BaseModel):
    token: str


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate user and return access token
    """
    user = authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]},
        expires_delta=access_token_expires,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=1800,  # 30 minutes in seconds
        user={
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        },
    )


@router.post("/refresh")
async def refresh_token(refresh_data: RefreshTokenRequest):
    """
    Refresh access token
    """
    try:
        from utils.auth import verify_token

        payload = verify_token(refresh_data.token)
        email = payload.get("sub")
        role = payload.get("role")

        # Create new token
        access_token_expires = timedelta(minutes=30)
        new_token = create_access_token(
            data={"sub": email, "role": role}, expires_delta=access_token_expires
        )

        return {"access_token": new_token, "token_type": "bearer", "expires_in": 1800}
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout user (in a real implementation, you'd invalidate the token)
    """
    return {"message": "Successfully logged out", "user_id": current_user["user_id"]}


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current user information
    """
    return current_user
