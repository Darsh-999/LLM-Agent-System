# backend/core/models.py

from datetime import datetime
from typing import Any, List, Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from pydantic_core import core_schema

# Define the allowed roles using a Literal type for strict validation
Role = Literal["manager", "assistant_manager", "developer"]


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        """
        Defines the Pydantic core schema for the ObjectId type.
        This ensures correct validation, serialization, and JSON schema generation.
        """

        def validate_from_str(v: str) -> ObjectId:
            """Validate that the input string is a valid ObjectId."""
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid ObjectId")
            return ObjectId(v)

        def validate_from_objectid(v: ObjectId) -> ObjectId:
            """Pass through ObjectId instances."""
            return v

        # Create a union schema that handles both string and ObjectId inputs
        python_schema = core_schema.union_schema(
            [
                core_schema.no_info_after_validator_function(
                    validate_from_objectid, core_schema.is_instance_schema(ObjectId)
                ),
                core_schema.no_info_after_validator_function(
                    validate_from_str, core_schema.str_schema()
                ),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=python_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


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

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
    }


class PDFOut(BaseModel):
    """
    Model for representing a PDF in API responses.
    This model now correctly handles the ObjectId from the database.
    """

    id: PyObjectId = Field(..., alias="_id")
    filename: str
    title: Optional[str] = None
    page_count: int

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {PyObjectId: str},
    }


class Citation(BaseModel):
    """
    Model for a single citation source.
    """

    source_name: str
    source_title: Optional[str] = None
    page_number: int


class ChatMessageBase(BaseModel):
    """
    Base model for a single message within a chat session.
    """

    role: Literal["user", "assistant"]
    content: str


class ChatMessageInDB(ChatMessageBase):
    """
    Model representing a message as stored in the database.
    """

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    chat_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.now)
    citations: List[Citation] = []


class ChatMessageOut(ChatMessageBase):
    """
    Model for representing a message in API responses.
    """

    id: PyObjectId = Field(..., alias="_id")
    created_at: datetime
    citations: List[Citation] = []

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {PyObjectId: str, ObjectId: str},
    }


class ChatSessionBase(BaseModel):
    """
    Base model for a chat session.
    """

    owner_email: EmailStr
    title: str = "New Chat"


class ChatSessionInDB(ChatSessionBase):
    """
    Model representing a chat session as stored in the database.
    """

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.now)


class ChatSessionOut(BaseModel):
    """
    Model for representing a chat session in API list responses.
    """

    id: PyObjectId = Field(..., alias="_id")
    title: str
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {PyObjectId: str, ObjectId: str},
    }


class WebLinkBase(BaseModel):
    """Base model for a scraped web link."""

    url: HttpUrl  # Pydantic's HttpUrl type provides URL validation
    title: str
    owner_email: EmailStr


class WebLinkInDB(WebLinkBase):
    """Model representing a web link as stored in the database."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {ObjectId: str}


class WebLinkOut(BaseModel):
    """Model for representing a web link in API responses."""

    id: PyObjectId = Field(..., alias="_id")

    url: HttpUrl
    title: str

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {PyObjectId: str}
