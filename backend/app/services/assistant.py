import json
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.repositories.insights import list_customer_outstanding_balances
from app.services.dashboard import get_dashboard
from app.services.insights import (
    get_cash_flow_forecast,
    list_duplicate_invoices,
    list_slow_payers,
)


def build_financial_assistant_context(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    as_of_date: date = None,
) -> str:
    effective_date = as_of_date or date.today()
    customer_balances = list_customer_outstanding_balances(
        db,
        owner_id,
        currency,
        effective_date,
    )
    context = {
        "dashboard": get_dashboard(
            db, owner_id, currency=currency, as_of_date=effective_date
        ).model_dump(mode="json"),
        "duplicate_invoices": list_duplicate_invoices(
            db, owner_id, currency=currency
        ).model_dump(mode="json"),
        "cash_flow_forecast": get_cash_flow_forecast(
            db, owner_id, currency=currency, as_of_date=effective_date
        ).model_dump(mode="json"),
        "slow_payers": list_slow_payers(
            db, owner_id, currency=currency, as_of_date=effective_date
        ).model_dump(mode="json"),
        "outstanding_by_customer": [
            {
                "customer_id": str(customer.id),
                "customer_name": customer.name,
                "outstanding_invoice_count": invoice_count,
                "outstanding_balance": str(outstanding_balance),
                "currency": currency,
            }
            for customer, invoice_count, outstanding_balance in customer_balances
        ],
    }
    return json.dumps(context)
