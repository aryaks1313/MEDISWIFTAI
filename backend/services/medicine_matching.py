
from sqlalchemy.orm import Session

from backend.models import Medicine


def find_medicine_candidates(
    db: Session,
    name: str,
    strength: str | None = None,
    dosage_form: str | None = None
):

    query = db.query(Medicine).filter(
        Medicine.generic_name.ilike(f"%{name}%")
        | Medicine.brand_name.ilike(f"%{name}%")
    )

    if strength:
        query = query.filter(
            Medicine.strength == strength
        )

    if dosage_form:
        query = query.filter(
            Medicine.dosage_form == dosage_form
        )

    return query.all()


def apply_customer_preference(
    candidates,
    preference: str
):

    if preference == "exact_brand":
        return candidates

    if preference == "lower_cost":

        return sorted(
            candidates,
            key=lambda medicine: medicine.price
        )

    if preference == "all_options":
        return candidates

    return []
