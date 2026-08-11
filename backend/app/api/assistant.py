from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.assistant import FinancialAssistantAnswer, FinancialAssistantQuestion
from app.services.ai_provider import AIProviderNotConfiguredError, AIProviderProcessingError, OpenAIInvoiceExtractionProvider
from app.services.assistant import build_financial_assistant_context

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("", response_model=FinancialAssistantAnswer)
def ask_financial_assistant(
    question_data: FinancialAssistantQuestion,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialAssistantAnswer:
    try:
        provider = OpenAIInvoiceExtractionProvider(settings.openai_api_key.get_secret_value(), settings.openai_invoice_model)
        context = build_financial_assistant_context(db, current_user.id, question_data.currency)
        return provider.answer_financial_question(question_data.question, context)
    except AIProviderNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Financial assistant provider is not configured") from exc
    except AIProviderProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Financial assistant provider failed") from exc
