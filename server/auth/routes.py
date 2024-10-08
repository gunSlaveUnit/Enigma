import datetime
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Cookie, Depends
from passlib.context import CryptContext
from server.auth.models import User
from server.auth.schemas import UserSignInSchema, UserSignUpSchema
from server.root.auth import authenticate_user, get_current_user
from server.root.cache import get_cache_storage
from server.root.crypt import get_crypt_context
from server.root.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/sign-up", status_code=status.HTTP_204_NO_CONTENT)
async def sign_up(
    data: UserSignUpSchema,
    db: AsyncSession = Depends(get_db),
    context: CryptContext = Depends(get_crypt_context),
) -> None:
    """
    User account creation.

    Args:
        data: user data as UserSignUpSchema.
        db: db async session.
        context: helper with hashing algorithms.

    Returns:
        None.

    Raises:
        HTTPException: 409 conflict
        if user with the same name or email already exists.
    """

    same_name_user: Optional[User] = await User.by_name(data.name, db)
    if same_name_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with the same name already exists.",
        )

    same_email_user: Optional[User] = await User.by_email(data.email, db)
    if same_email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with the same email address already exists.",
        )

    await User.create(
        UserSignUpSchema(
            name=data.name,
            email=data.email,
            password=context.hash(data.password),
        ).model_dump(),
        db,
    )


@router.post("/sign-in")
async def sign_in(
    data: UserSignInSchema,
    db: AsyncSession = Depends(get_db),
    cache_storage=Depends(get_cache_storage),
    context: CryptContext = Depends(get_crypt_context),
) -> JSONResponse:
    """
    User authentication into the system with setting the session value.

    Args:
        data: user data as UserSignInSchema.
        db: db async session.
        cache_storage: key-value storage interface.

    Returns:
        JSONResponse: message about successful login.

    Raises:
        HTTPException: 401 if user name or password is incorrect.
    """

    user: Optional[User] = await authenticate_user(
        data.name, data.password, db, context
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect name or password.",
        )

    try:
        await user.update(
            {"login_at": datetime.datetime.now(datetime.UTC)},
            db,
        )
    except AttributeError as e:
        raise HTTPException(
            detail=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    session_id = str(uuid.uuid4())
    await cache_storage.set(session_id, user.id)

    response = JSONResponse({"detail": "Logged in successfully."})
    HTTPS = os.getenv("HTTPS") == "True"
    response.set_cookie(
        "session",
        session_id,
        httponly=True,
        secure=HTTPS,
        samesite="none" if HTTPS else "lax",
    )

    return response


@router.post("/sign-out")
async def sign_out(
    _: User = Depends(get_current_user),
    session: Optional[str] = Cookie(None),
    cache_storage=Depends(get_cache_storage),
) -> JSONResponse:
    """
    Deletes a user session.

    Args:
        _: current user object, not used, just need session check.
        session: session uuid from cookie.
        cache_storage: key-value storage interface.

    Returns:
        JSONResponse: with message that session was successfully removed.

    Raises:
        HTTPException: 401 if session is not provided or expired.
    """

    # No need to check if session is not None here,
    # it's already checked in get_current_user
    await cache_storage.delete(session)

    response = JSONResponse({"detail": f"Session {session} was removed."})
    response.delete_cookie("session")

    return response
