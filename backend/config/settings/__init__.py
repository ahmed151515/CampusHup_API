import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env FIRST (before anything else)
load_dotenv(BASE_DIR / ".env")
ENV = os.getenv("ENV")

match ENV:
    case "prod":
        from .prod import *
    case "dev":
        from .dev import *

    case "test":
        from .test import *
