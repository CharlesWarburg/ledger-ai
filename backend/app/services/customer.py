import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.repositories.customer import (
    add_customer_record,
    delete_customer_record,
    get_customer_record,
    list_customer_records,
    update_customer_record,
)
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerNotFoundError(ValueError):
    pass


def create_customer(
    db: Session,
    owner_id: uuid.UUID,
    customer_data: CustomerCreate,
) -> Customer:
    customer = add_customer_record(
        db,
        owner_id,
        customer_data.model_dump(),
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(customer)
    return customer


def list_customers(
    db: Session,
    owner_id: uuid.UUID,
    offset: int = 0,
    limit: int = 100,
) -> list[Customer]:
    return list_customer_records(db, owner_id, offset=offset, limit=limit)


def get_customer(
    db: Session,
    owner_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> Customer:
    customer = get_customer_record(db, owner_id, customer_id)
    if customer is None:
        raise CustomerNotFoundError("Customer not found")
    return customer


def update_customer(
    db: Session,
    owner_id: uuid.UUID,
    customer_id: uuid.UUID,
    customer_data: CustomerUpdate,
) -> Customer:
    customer = get_customer(db, owner_id, customer_id)
    update_customer_record(
        customer,
        customer_data.model_dump(exclude_unset=True),
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(customer)
    return customer


def delete_customer(
    db: Session,
    owner_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> None:
    customer = get_customer(db, owner_id, customer_id)
    delete_customer_record(db, customer)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
