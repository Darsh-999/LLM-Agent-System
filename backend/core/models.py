# backend/core/models.py

from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, HttpUrl

# Define the allowed roles using a Literal type for strict validation
Role = Literal["manager", "assistant_manager", "developer"]


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, *args, **kwargs):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


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


class PDFBase(BaseModel):
    """
    Base model for a PDF document.
    """

    filename: str
    title: Optional[str] = None
    page_count: int
    owner_email: EmailStr


class PDFInDB(PDFBase):
    """
    Model representing a PDF as stored in the database.
    Includes the MongoDB `_id`.
    """

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {ObjectId: str}


class PDFOut(BaseModel):
    """
    Model for representing a PDF in API responses.
    This model now correctly handles the ObjectId from the database.
    """

    id: PyObjectId = Field(..., alias="_id")

    filename: str
    title: Optional[str] = None
    page_count: int

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {PyObjectId: str}
