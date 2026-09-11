from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    MessageOut,
    RefreshRequest,
    ResetPasswordRequest,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services.auth_service import (
    AuthService,
    EmailAlreadyExistsError,
    EmailService,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidResetTokenError,
)


REFRESH_COOKIE_NAME = "refresh_token"
oauth = OAuth()


router = APIRouter(prefix="/auth", tags=["auth"])


def _google_client():
    if not settings.google_client_id or not settings.google_client_secret:
        return None
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth.google


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


def _build_auth_response(user: User, access_token: str, refresh_token: str) -> AuthResponse:
    return AuthResponse(access_token=access_token, user=UserOut.model_validate(user))


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    auth_service = AuthService(db)
    try:
        user = auth_service.signup(payload)
        access_token, refresh_token = auth_service.issue_token_pair(user)
        _set_refresh_cookie(response, refresh_token)
        return _build_auth_response(user, access_token, refresh_token)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    auth_service = AuthService(db)
    try:
        user = auth_service.login(payload)
        access_token, refresh_token = auth_service.issue_token_pair(user)
        _set_refresh_cookie(response, refresh_token)
        return _build_auth_response(user, access_token, refresh_token)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/refresh", response_model=AuthResponse)
def refresh(payload: RefreshRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    auth_service = AuthService(db)
    cookie_token = request.cookies.get(REFRESH_COOKIE_NAME)
    refresh_token = payload.refresh_token or cookie_token

    try:
        user, access_token, new_refresh_token = auth_service.refresh(refresh_token or "")
        _set_refresh_cookie(response, new_refresh_token)
        return _build_auth_response(user, access_token, new_refresh_token)
    except InvalidRefreshTokenError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", response_model=MessageOut)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> MessageOut:
    auth_service = AuthService(db)
    auth_service.logout(request.cookies.get(REFRESH_COOKIE_NAME))
    _clear_refresh_cookie(response)
    return MessageOut(message="Logged out.")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get("/google/login")
async def google_login(request: Request) -> RedirectResponse:
    google = _google_client()
    if google is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured.")
    redirect_uri = f"{settings.backend_url}{settings.api_v1_prefix}/auth/google/callback"
    return await google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    google = _google_client()
    if google is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured.")
    try:
        token = await google.authorize_access_token(request)
        profile = token.get("userinfo")
        if not profile:
            profile = await google.userinfo(token=token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google authentication failed.") from exc

    provider_user_id = profile.get("sub") or profile.get("id")
    email = profile.get("email")
    name = profile.get("name") or email
    avatar_url = profile.get("picture")

    if not provider_user_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incomplete Google profile.")

    auth_service = AuthService(db)
    user = auth_service.upsert_google_user(
        provider_user_id=str(provider_user_id),
        email=str(email),
        name=str(name),
        avatar_url=str(avatar_url) if avatar_url else None,
    )
    app_access_token, refresh_token = auth_service.issue_token_pair(user)
    redirect_response = RedirectResponse(
        url=f"{settings.frontend_url}/oauth/callback#access_token={app_access_token}"
    )
    _set_refresh_cookie(redirect_response, refresh_token)
    return redirect_response


@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> MessageOut:
    auth_service = AuthService(db)
    reset_token = auth_service.forgot_password(payload.email)
    if reset_token:
        EmailService.send_password_reset_email(to_email=payload.email, token=reset_token)
    return MessageOut(message="If that email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageOut)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageOut:
    auth_service = AuthService(db)
    try:
        auth_service.reset_password(payload.token, payload.new_password)
        return MessageOut(message="Password has been reset.")
    except InvalidResetTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
