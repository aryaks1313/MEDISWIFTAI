import json
import os
import shutil
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models import (
    Medicine,
    Order,
    OrderItem,
    Prescription,
    User,
)
from backend.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from backend.ai.prescription_agent import analyze_prescription_text

load_dotenv()

app = FastAPI(
    title="MediSwift AI API",
    description="Medicine ordering demo with pharmacist review.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to your frontend origin in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads/prescriptions"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)


# ---------- Request schemas ----------

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str
    password: str = Field(min_length=8)
    role: str = "customer"


class LoginRequest(BaseModel):
    email: str
    password: str


class MedicineRequest(BaseModel):
    name: str
    generic_name: str
    brand_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    requires_prescription: bool = True
    pharmacy_name: Optional[str] = None


class OrderItemRequest(BaseModel):
    medicine_id: int
    quantity: int = Field(gt=0)


class OrderRequest(BaseModel):
    items: list[OrderItemRequest]
    delivery_address: str = Field(min_length=5)
    prescription_id: Optional[int] = None


class PrescriptionReviewRequest(BaseModel):
    status: str
    pharmacist_notes: Optional[str] = None


class OrderStatusRequest(BaseModel):
    status: str


class AssignDeliveryRequest(BaseModel):
    delivery_person_id: int


# ---------- Helpers ----------

def user_payload(user: User):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }


def medicine_payload(medicine: Medicine):
    return {
        "id": medicine.id,
        "name": medicine.name,
        "generic_name": medicine.generic_name,
        "brand_name": medicine.brand_name,
        "strength": medicine.strength,
        "dosage_form": medicine.dosage_form,
        "price": medicine.price,
        "stock": medicine.stock,
        "requires_prescription": medicine.requires_prescription,
        "pharmacy_name": medicine.pharmacy_name,
    }


def order_payload(order: Order):
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "prescription_id": order.prescription_id,
        "delivery_person_id": order.delivery_person_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "delivery_address": order.delivery_address,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "medicine_id": item.medicine_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in order.items
        ],
    }


# ---------- General ----------

@app.get("/")
def root():
    return {
        "message": "Welcome to MediSwift AI",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------- Authentication ----------

@app.post("/api/auth/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    allowed_roles = {"customer", "shop_owner", "delivery_person"}

    if data.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid registration role",
        )

    existing = (
        db.query(User)
        .filter(User.email == data.email.lower())
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user = User(
        name=data.name,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        role=data.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Registration successful",
        "user": user_payload(user),
    }


@app.post("/api/auth/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == data.email.lower())
        .first()
    )

    if not user or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_payload(user),
    }


@app.get("/api/auth/me")
def get_me(user: User = Depends(get_current_user)):
    return user_payload(user)


# ---------- Medicine catalogue ----------

@app.get("/api/medicines")
def list_medicines(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Medicine).filter(Medicine.is_active.is_(True))

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Medicine.name.ilike(term)
            | Medicine.generic_name.ilike(term)
            | Medicine.brand_name.ilike(term)
        )

    medicines = query.order_by(Medicine.name).all()
    return [medicine_payload(item) for item in medicines]


@app.post("/api/medicines")
def create_medicine(
    data: MedicineRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("shop_owner")),
):
    medicine = Medicine(**data.model_dump())
    db.add(medicine)
    db.commit()
    db.refresh(medicine)

    return medicine_payload(medicine)


@app.put("/api/medicines/{medicine_id}")
def update_medicine(
    medicine_id: int,
    data: MedicineRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("shop_owner")),
):
    medicine = db.query(Medicine).filter(
        Medicine.id == medicine_id
    ).first()

    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    for key, value in data.model_dump().items():
        setattr(medicine, key, value)

    db.commit()
    db.refresh(medicine)

    return medicine_payload(medicine)


@app.delete("/api/medicines/{medicine_id}")
def deactivate_medicine(
    medicine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("shop_owner")),
):
    medicine = db.query(Medicine).filter(
        Medicine.id == medicine_id
    ).first()

    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    medicine.is_active = False
    db.commit()

    return {"message": "Medicine removed from active catalogue"}


# ---------- Prescription upload and review ----------

@app.post("/api/prescriptions/upload")
def upload_prescription(
    file: UploadFile = File(...),
    preference: str = Form("all_options"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("customer")),
):
    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail="Upload a JPG, PNG, WEBP, or PDF prescription",
        )

    # Avoid using the original filename as a filesystem path.
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file extension",
        )

    safe_filename = f"user_{user.id}_{os.urandom(8).hex()}{extension}"
    destination = UPLOAD_DIR / safe_filename

    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    prescription = Prescription(
        customer_id=user.id,
        file_path=str(destination),
        extracted_text=None,
        ai_candidates=None,
        status="pending_pharmacist_review",
    )

    db.add(prescription)
    db.commit()
    db.refresh(prescription)

    # This starter version does not yet perform OCR.
    # The AI endpoint accepts OCR text once OCR has been integrated.
    return {
        "id": prescription.id,
        "status": prescription.status,
        "preference": preference,
        "message": (
            "Prescription uploaded. OCR and pharmacist review are required "
            "before prescription medicines can be dispensed."
        ),
    }


@app.post("/api/prescriptions/{prescription_id}/analyze")
def analyze_prescription(
    prescription_id: int,
    extracted_text: str = Form(...),
    preference: str = Form("all_options"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id
    ).first()

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if user.role == "customer" and prescription.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your prescription")

    medicines = db.query(Medicine).filter(
        Medicine.is_active.is_(True)
    ).all()

    catalogue = [medicine_payload(item) for item in medicines]

    result = analyze_prescription_text(
        extracted_text=extracted_text,
        catalogue=catalogue,
        preference=preference,
    )

    prescription.extracted_text = extracted_text
    prescription.ai_candidates = json.dumps(result)
    prescription.status = "pending_pharmacist_review"

    db.commit()

    return result


@app.get("/api/prescriptions")
def list_prescriptions(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("shop_owner")),
):
    prescriptions = (
        db.query(Prescription)
        .order_by(Prescription.created_at.desc())
        .all()
    )

    return [
        {
            "id": item.id,
            "customer_id": item.customer_id,
            "file_path": item.file_path,
            "extracted_text": item.extracted_text,
            "ai_candidates": item.ai_candidates,
            "status": item.status,
            "pharmacist_notes": item.pharmacist_notes,
            "created_at": item.created_at.isoformat(),
        }
        for item in prescriptions
    ]


@app.post("/api/prescriptions/{prescription_id}/review")
def review_prescription(
    prescription_id: int,
    data: PrescriptionReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("shop_owner")),
):
    allowed_statuses = {
        "approved_by_pharmacist",
        "rejected_by_pharmacist",
        "needs_clarification",
    }

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid pharmacist review status",
        )

    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id
    ).first()

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    prescription.status = data.status
    prescription.pharmacist_notes = data.pharmacist_notes

    db.commit()

    return {
        "id": prescription.id,
        "status": prescription.status,
        "pharmacist_notes": prescription.pharmacist_notes,
    }


# ---------- Orders ----------

@app.post("/api/orders")
def create_order(
    data: OrderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("customer")),
):
    if not data.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    prescription = None

    if data.prescription_id:
        prescription = db.query(Prescription).filter(
            Prescription.id == data.prescription_id,
            Prescription.customer_id == user.id,
        ).first()

        if not prescription:
            raise HTTPException(
                status_code=404,
                detail="Prescription not found",
            )

    total = 0
    validated_items = []

    for requested_item in data.items:
        medicine = db.query(Medicine).filter(
            Medicine.id == requested_item.medicine_id,
            Medicine.is_active.is_(True),
        ).first()

        if not medicine:
            raise HTTPException(
                status_code=404,
                detail=f"Medicine {requested_item.medicine_id} not found",
            )

        if medicine.stock < requested_item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {medicine.name}",
            )

        if medicine.requires_prescription:
            if not prescription:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{medicine.name} requires a prescription "
                        "linked to the order"
                    ),
                )

            if prescription.status != "approved_by_pharmacist":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Prescription medicines can only be ordered after "
                        "pharmacist approval"
                    ),
                )

        line_total = medicine.price * requested_item.quantity
        total += line_total

        validated_items.append(
            (medicine, requested_item.quantity, medicine.price)
        )

    order = Order(
        customer_id=user.id,
        prescription_id=prescription.id if prescription else None,
        status="placed",
        total_amount=total,
        delivery_address=data.delivery_address,
    )

    db.add(order)
    db.flush()

    for medicine, quantity, price in validated_items:
        medicine.stock -= quantity

        order_item = OrderItem(
            order_id=order.id,
            medicine_id=medicine.id,
            quantity=quantity,
            unit_price=price,
        )
        db.add(order_item)

    db.commit()
    db.refresh(order)

    return order_payload(order)


@app.get("/api/orders")
def list_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "customer":
        orders = db.query(Order).filter(
            Order.customer_id == user.id
        ).order_by(Order.created_at.desc()).all()

    elif user.role == "delivery_person":
        orders = db.query(Order).filter(
            Order.delivery_person_id == user.id
        ).order_by(Order.created_at.desc()).all()

    elif user.role == "shop_owner":
        orders = db.query(Order).order_by(
            Order.created_at.desc()
        ).all()

    else:
        raise HTTPException(status_code=403, detail="Access denied")

    return [order_payload(order) for order in orders]


@app.post("/api/orders/{order_id}/assign-delivery")
def assign_delivery(
    order_id: int,
    data: AssignDeliveryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("shop_owner")),
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    delivery_person = db.query(User).filter(
        User.id == data.delivery_person_id,
        User.role == "delivery_person",
        User.is_active.is_(True),
    ).first()

    if not delivery_person:
        raise HTTPException(
            status_code=404,
            detail="Active delivery person not found",
        )

    order.delivery_person_id = delivery_person.id
    order.status = "assigned_to_delivery"

    db.commit()

    return order_payload(order)


@app.patch("/api/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    data: OrderStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    transitions = {
        "shop_owner": {
            "placed": {"confirmed", "cancelled"},
            "confirmed": {"ready_for_pickup", "cancelled"},
            "ready_for_pickup": {"assigned_to_delivery"},
        },
        "delivery_person": {
            "assigned_to_delivery": {"picked_up"},
            "picked_up": {"out_for_delivery"},
            "out_for_delivery": {"delivered"},
        },
    }

    if user.role == "delivery_person":
        if order.delivery_person_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="This order is assigned to another delivery person",
            )

    allowed = transitions.get(user.role, {}).get(order.status, set())

    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change order from {order.status} to {data.status}",
        )

    order.status = data.status
    db.commit()

    return order_payload(order)