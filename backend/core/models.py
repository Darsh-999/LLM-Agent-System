# backend/core/models.py

from typing import Literal
from pydantic import BaseModel, EmailStr, Field

# Define the allowed roles using a Literal type for strict validation
Role = Literal["manager", "assistant_manager", "developer"]


class UserBase(BaseModel):
    """
    Base model for a user, containing common fields.
    """

    email: EmailStr
    role: Role = Field(
        ..., description="The role of the user, must be one of the predefined roles."
    )


class UserCreate(UserBase):
    """
    Pydantic model for creating a new user.
    Used for the /register endpoint.
    """

    password: str = Field(
        ...,
        min_length=8,
        description="User's password, must be at least 8 characters long.",
    )


class UserInDB(UserBase):
    """
    Pydantic model representing a user as stored in the database.
    Includes the hashed password.
    """

    hashed_password: str


class UserOut(UserBase):
    """
    Pydantic model for representing a user in API responses.
    Excludes sensitive information like the password.
    """

    pass


class Token(BaseModel):
    """
    Pydantic model for the JWT access token response.
    """

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Pydantic model for the data encoded within a JWT.
    """

    email: str | None = None
    role: Role | None = None
