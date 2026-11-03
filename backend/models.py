from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="customer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    generic_name = Column(String(200), nullable=False, index=True)
    brand_name = Column(String(200), nullable=True)
    strength = Column(String(100), nullable=True)
    dosage_form = Column(String(100), nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    requires_prescription = Column(Boolean, default=True)
    pharmacy_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    extracted_text = Column(Text, nullable=True)
    ai_candidates = Column(Text, nullable=True)
    status = Column(String(50), default="pending_pharmacist_review")
    pharmacist_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id"),
        nullable=True,
    )
    delivery_person_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )
    status = Column(String(50), default="placed")
    total_amount = Column(Float, nullable=False, default=0)
    delivery_address = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")