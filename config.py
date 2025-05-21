import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_USERS_TABLE = os.getenv("SUPABASE_USERS_TABLE", "users")

# Configuration Casdoor
CASDOOR_ENDPOINT = os.getenv("CASDOOR_ENDPOINT")
CASDOOR_CLIENT_ID = os.getenv("CASDOOR_CLIENT_ID")
CASDOOR_CLIENT_SECRET = os.getenv("CASDOOR_CLIENT_SECRET")
CASDOOR_ORGANIZATION = os.getenv("CASDOOR_ORGANIZATION")
CASDOOR_APPLICATION = os.getenv("CASDOOR_APPLICATION")

# Configuration Mattermost
MATTERMOST_URL = os.getenv("MATTERMOST_URL")
MATTERMOST_TOKEN = os.getenv("MATTERMOST_TOKEN")

# Configuration Postfix
POSTFIX_SERVER = os.getenv("POSTFIX_SERVER")
POSTFIX_ADMIN_USER = os.getenv("POSTFIX_ADMIN_USER")
POSTFIX_ADMIN_PASSWORD = os.getenv("POSTFIX_ADMIN_PASSWORD")

# Configuration OwnCloud
OWNCLOUD_URL = os.getenv("OWNCLOUD_URL")
OWNCLOUD_ADMIN_USER = os.getenv("OWNCLOUD_ADMIN_USER")
OWNCLOUD_ADMIN_PASSWORD = os.getenv("OWNCLOUD_ADMIN_PASSWORD")

# Configuration de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")