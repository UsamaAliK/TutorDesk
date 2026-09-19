from fastapi import Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from backend.db.database import get_db
from backend.db.models import User
from backend.security import decode_token

oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/login")

async def get_current_user(
        token:Annotated[str,Depends(oauth2_scheme)],
        db:Annotated[AsyncSession,Depends(get_db)]
)->User:
    credentials_exception=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate":"Bearer"}

    )
    try:
        payload=decode_token(token)
        user_id=int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except(jwt.InvalidTokenError,ValueError):
        raise credentials_exception
    user=await db.execute(select(User).where(User.id==user_id))
    user=user.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user