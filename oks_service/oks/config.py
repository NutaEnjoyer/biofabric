import os

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://biofabric:biofabric_secret@localhost:5432/biofabric",
)
