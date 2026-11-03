
# backend/reset_database.py

from backend.database import Base, engine

# Import all models so SQLAlchemy registers every table.
from backend.models import (
    User,
    Medicine,
    Prescription,
    Order,
    OrderItem,
)


def reset_database():
    database_name = engine.url.database

    print("\nMediSwift AI Database Reset")
    print("---------------------------")
    print(f"Database: {database_name}")
    print(f"Host: {engine.url.host}")
    print("\nWARNING: All existing data in the model tables will be deleted.")

    confirmation = input(
        f"\nType '{database_name}' to confirm the reset: "
    )

    if confirmation != database_name:
        print("Reset cancelled. No database changes were made.")
        return

    try:
        # Drop existing tables in dependency-safe order.
        Base.metadata.drop_all(bind=engine)

        # Create all tables using the current SQLAlchemy models.
        Base.metadata.create_all(bind=engine)

        print("\nDatabase reset completed successfully!")
        print("All tables were recreated from backend/models.py.")

    except Exception as error:
        print("\nDatabase reset failed.")
        print(f"Error: {error}")
        raise


if __name__ == "__main__":
    reset_database()
