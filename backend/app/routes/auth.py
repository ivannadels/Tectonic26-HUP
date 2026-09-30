from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .. import auth
from ..auth import User, current_user

router = APIRouter(prefix="/auth", tags=["auth"])
GENERIC = "Invalid username or password."


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class MeOut(BaseModel):
    username: str
    display_name: str
    role: str


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response):
    username = body.username.strip().lower()
    if auth.rate_limited(username):
        raise HTTPException(429, "Too many attempts. Try again in a few minutes.")
    user = auth.verify_credentials(username, body.password)
    if not user:
        auth.record_failure(username)
        raise HTTPException(401, GENERIC)
    auth.clear_failures(username)
    auth.create_session(response, request, user.username)
    return MeOut(**user.__dict__)


@router.post("/logout")
def logout(request: Request, response: Response, _: User = Depends(current_user)):
    auth.destroy_session(request, response)
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(current_user)):
    return MeOut(**user.__dict__)
