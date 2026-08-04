"""API router for authentication operations (Registration, Login, User Profile)."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from apps.database import get_db
from apps.security import verify_password, create_access_token
from apps.users import crud
from apps.users.schemas import UserCreate, UserOut, Token
from apps.auth.dependencies import get_current_user
from apps.users.models import User
from services.bravo import send_welcome_email

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user account.

    Checks if username or email already exists, hashes password, creates user,
    and dispatches a welcome email via Brevo in the background.

    Args:
        user_in (UserCreate): Registration input schema containing username, email, and password.
        background_tasks (BackgroundTasks): FastAPI background tasks dependency.
        db (Session): Database session dependency.

    Raises:
        HTTPException: HTTP 400 Bad Request if username or email is already registered.

    Returns:
        UserOut: Output schema containing created user details excluding password.
    """
    if crud.get_user_by_username(db, username=user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    if crud.get_user_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = crud.create_user(db, user_data=user_in)

    # Dispatch welcome email asynchronously via Brevo (Bravo) service
    background_tasks.add_task(send_welcome_email, email=user.email, username=user.username)

    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user credentials and issue a signed JWT access token.

    Compatible with FastAPI OAuth2 Password Request Form (Swagger UI).
    Form data `username` field can accept either username or email address.

    Args:
        form_data (OAuth2PasswordRequestForm): Form containing username and password.
        db (Session): Database session dependency.

    Raises:
        HTTPException: HTTP 401 Unauthorized if credentials are incorrect.

    Returns:
        Token: Object containing JWT access_token and token_type ("bearer").
    """
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user:
        user = crud.get_user_by_email(db, email=form_data.username)

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve profile details of the currently authenticated user.

    Args:
        current_user (User): Authenticated user instance from JWT dependency.

    Returns:
        UserOut: Current user's profile details.
    """
    return current_user
