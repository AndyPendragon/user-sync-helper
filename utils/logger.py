import logging
from rich.console import Console
from rich.logging import RichHandler
from config import LOG_LEVEL

# Console pour l'affichage amélioré
console = Console()

# Configuration du logger avec Rich
def setup_logger():
    """Configure et retourne un logger avec Rich pour un meilleur affichage."""
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    return logging.getLogger("user_sync")

# Logger principal
logger = setup_logger()

def log_status_diff(username: str, app_name: str, db_status: bool, real_status: bool):
    """Affiche la différence de statut pour un utilisateur."""
    if db_status == real_status:
        return
    
    status_text = {
        (True, False): f"🔴 {username} est ACTIF dans Supabase mais INACTIF dans {app_name}",
        (False, True): f"🔵 {username} est INACTIF dans Supabase mais ACTIF dans {app_name}"
    }
    
    logger.warning(status_text.get((db_status, real_status)))

def log_action(username: str, app_name: str, action: str, success: bool):
    """Affiche le résultat d'une action sur une application."""
    result = "✅ Réussi" if success else "❌ Échec"
    logger.info(f"{result}: {action} pour {username} sur {app_name}")