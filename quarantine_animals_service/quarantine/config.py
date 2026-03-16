import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/biolab")
CORE_BASE_URL = os.getenv("CORE_BASE_URL", "http://core-service.local")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENTITY_TYPE = os.getenv("ENTITY_TYPE", "qa_record")
