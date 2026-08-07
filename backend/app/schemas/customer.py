import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerNormalizers(BaseModel):
    @field_validator("name", mode="before", check_fields=False)
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if value is None:
            raise ValueError("Customer name cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Customer name cannot be empty")
        return value

    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator(
        "phone",
        "address_line_1",
        "address_line_2",
        "city",
        "postal_code",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("country_code", "vat_number", mode="before", check_fields=False)
    @classmethod
    def normalize_codes(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().upper()
            return value or None
        return value


class CustomerCreate(CustomerNormalizers):
    name: str = Field(min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    address_line_1: Optional[str] = Field(default=None, max_length=255)
    address_line_2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    country_code: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
    )
    vat_number: Optional[str] = Field(default=None, max_length=32)


class CustomerUpdate(CustomerNormalizers):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    address_line_1: Optional[str] = Field(default=None, max_length=255)
    address_line_2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    country_code: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
    )
    vat_number: Optional[str] = Field(default=None, max_length=32)


class CustomerResponse(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
