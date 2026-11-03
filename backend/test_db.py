
from sqlalchemy import text

from backend.database import engine

try:
    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT version()")
        )

        print(result.scalar())

        print("PostgreSQL connection successful!")

except Exception as error:

    print("Database connection failed:")
    print(error)
