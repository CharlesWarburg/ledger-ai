from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FinancialAssistantQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1000)
    currency: str = Field(default="GBP", min_length=3, max_length=3)

    @field_validator("question", mode="before")
    @classmethod
    def normalize_question(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Question cannot be empty")
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class FinancialAssistantAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=3000)
    data_scope: str = Field(min_length=1, max_length=500)
    caveat: Optional[str] = Field(default=None, max_length=1000)
