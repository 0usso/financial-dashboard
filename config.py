import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de la base de données
DB_TYPE = "postgresql"
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_DB = os.getenv("PG_DB", "trading")
PG_USER = os.getenv("PG_USER", "trading_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "StrongPassword123")
