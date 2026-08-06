from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user import add_user, get_user_by_email
from app.schemas.auth import UserLogin, UserRegister

DUMMY_PASSWORD_HASH = hash_password("dummy-password-used-only-for-timing")


class EmailAlreadyRegisteredError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


def register_user(db: Session, registration: UserRegister) -> User:
    email = str(registration.email)
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError("Email is already registered")

    user = add_user(
        db,
        email=email,
        hashed_password=hash_password(registration.password),
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAlreadyRegisteredError("Email is already registered") from exc

    db.refresh(user)
    return user


def authenticate_user(db: Session, credentials: UserLogin) -> str:
    user = get_user_by_email(db, str(credentials.email))

    if user is None:
        verify_password(credentials.password, DUMMY_PASSWORD_HASH)
        raise InvalidCredentialsError("Invalid email or password")

    if not verify_password(credentials.password, user.hashed_password):
        raise InvalidCredentialsError("Invalid email or password")

    if not user.is_active:
        raise InvalidCredentialsError("Invalid email or password")

    return create_access_token(user.id)
