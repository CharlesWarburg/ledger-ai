import uuid
from typing import Mapping, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def add_customer_record(
    db: Session,
    owner_id: uuid.UUID,
    values: Mapping[str, object],
) -> Customer:
    customer = Customer(owner_id=owner_id, **dict(values))
    db.add(customer)
    return customer


def list_customer_records(
    db: Session,
    owner_id: uuid.UUID,
    offset: int = 0,
    limit: int = 100,
) -> list[Customer]:
    statement = (
        select(Customer)
        .where(Customer.owner_id == owner_id)
        .order_by(Customer.name, Customer.id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_customer_record(
    db: Session,
    owner_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> Optional[Customer]:
    statement = select(Customer).where(
        Customer.id == customer_id,
        Customer.owner_id == owner_id,
    )
    return db.scalar(statement)


def update_customer_record(
    customer: Customer,
    values: Mapping[str, object],
) -> Customer:
    for field, value in values.items():
        setattr(customer, field, value)
    return customer


def delete_customer_record(db: Session, customer: Customer) -> None:
    db.delete(customer)
