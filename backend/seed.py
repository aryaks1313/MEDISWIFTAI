from backend.database import Base, SessionLocal, engine
from backend.models import Medicine, User
from backend.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

demo_users = [
    {
        "name": "Demo Customer",
        "email": "customer@mediswift.demo",
        "password": "Customer@123",
        "role": "customer",
    },
    {
        "name": "Demo Pharmacist",
        "email": "pharmacist@mediswift.demo",
        "password": "Pharmacist@123",
        "role": "shop_owner",
    },
    {
        "name": "Demo Delivery Partner",
        "email": "delivery@mediswift.demo",
        "password": "Delivery@123",
        "role": "delivery_person",
    },
]

demo_medicines = [
    {
        "name": "Paracetamol 500 mg",
        "generic_name": "Paracetamol",
        "brand_name": "Generic",
        "strength": "500 mg",
        "dosage_form": "Tablet",
        "price": 2.50,
        "stock": 100,
        "requires_prescription": False,
        "pharmacy_name": "MediSwift Demo Pharmacy",
    },
    {
        "name": "Cetirizine 10 mg",
        "generic_name": "Cetirizine",
        "brand_name": "Generic",
        "strength": "10 mg",
        "dosage_form": "Tablet",
        "price": 3.00,
        "stock": 75,
        "requires_prescription": False,
        "pharmacy_name": "MediSwift Demo Pharmacy",
    },
    {
        "name": "Amoxicillin 500 mg",
        "generic_name": "Amoxicillin",
        "brand_name": "Generic",
        "strength": "500 mg",
        "dosage_form": "Capsule",
        "price": 8.00,
        "stock": 40,
        "requires_prescription": True,
        "pharmacy_name": "MediSwift Demo Pharmacy",
    },
    {
        "name": "Metformin 500 mg",
        "generic_name": "Metformin",
        "brand_name": "Generic",
        "strength": "500 mg",
        "dosage_form": "Tablet",
        "price": 4.00,
        "stock": 60,
        "requires_prescription": True,
        "pharmacy_name": "MediSwift Demo Pharmacy",
    },
]

try:
    for item in demo_users:
        existing = db.query(User).filter(
            User.email == item["email"]
        ).first()

        if not existing:
            user = User(
                name=item["name"],
                email=item["email"],
                password_hash=hash_password(item["password"]),
                role=item["role"],
            )
            db.add(user)

    for item in demo_medicines:
        existing = db.query(Medicine).filter(
            Medicine.name == item["name"]
        ).first()

        if not existing:
            db.add(Medicine(**item))

    db.commit()
    print("Demo users and medicines created successfully.")

finally:
    db.close()