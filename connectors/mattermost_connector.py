import requests
from typing import Dict, Optional, List

from config import MATTERMOST_URL, MATTERMOST_TOKEN
from utils.logger import logger


class MattermostConnector:
    """Gère la connexion et les opérations avec Mattermost."""
    
    def __init__(self):
        """Initialise la connexion à Mattermost."""
        if not all([MATTERMOST_URL, MATTERMOST_TOKEN]):
            raise ValueError("Les variables d'environnement pour Mattermost ne sont pas définies.")
        
        self.url = MATTERMOST_URL.rstrip('/')
        self.token = MATTERMOST_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def check_user_status(self, email: str) -> Optional[bool]:
        """Vérifie si un utilisateur est actif dans Mattermost.
        
        Args:
            email: Email de l'utilisateur à vérifier
            
        Returns:
            bool ou None: True si actif, False si inactif, None si erreur ou utilisateur non trouvé
        """
        try:
            # Récupérer l'utilisateur par email
            user_id = self._get_user_id_by_email(email)
            
            if not user_id:
                logger.warning(f"Utilisateur non trouvé dans Mattermost: {email}")
                return None
            
            # Récupérer les détails de l'utilisateur
            user_url = f"{self.url}/api/v4/users/{user_id}"
            response = requests.get(user_url, headers=self.headers)
            response.raise_for_status()
            
            user_data = response.json()
            
            # Vérifier si l'utilisateur est actif
            # Dans Mattermost, un utilisateur est inactif s'il a "delete_at" > 0
            is_active = user_data.get("delete_at", 0) == 0
            
            logger.info(f"Statut de l'utilisateur {email} dans Mattermost: {'actif' if is_active else 'inactif'}")
            return is_active
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du statut dans Mattermost: {str(e)}")
            return None
    
    def update_user_status(self, email: str, is_active: bool) -> bool:
        """Met à jour le statut d'un utilisateur dans Mattermost.
        
        Args:
            email: Email de l'utilisateur à mettre à jour
            is_active: Nouveau statut (True pour actif, False pour inactif)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Récupérer l'utilisateur par email
            user_id = self._get_user_id_by_email(email)
            
            if not user_id:
                logger.warning(f"Utilisateur non trouvé dans Mattermost: {email}")
                return False
            
            # Si l'utilisateur doit être activé
            if is_active:
                # Activer l'utilisateur
                activate_url = f"{self.url}/api/v4/users/{user_id}/active"
                payload = {"active": True}
                response = requests.put(activate_url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                logger.info(f"Utilisateur {email} activé dans Mattermost")
                return True
            else:
                # Désactiver l'utilisateur
                deactivate_url = f"{self.url}/api/v4/users/{user_id}/active"
                payload = {"active": False}
                response = requests.put(deactivate_url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                logger.info(f"Utilisateur {email} désactivé dans Mattermost")
                return True
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut dans Mattermost: {str(e)}")
            return False
    
    def _get_user_id_by_email(self, email: str) -> Optional[str]:
        """Récupère l'ID d'un utilisateur Mattermost par son email.
        
        Args:
            email: Email de l'utilisateur
            
        Returns:
            str ou None: ID de l'utilisateur ou None si non trouvé
        """
        try:
            search_url = f"{self.url}/api/v4/users/email/{email}"
            response = requests.get(search_url, headers=self.headers)
            
            if response.status_code == 404:
                logger.warning(f"Utilisateur non trouvé dans Mattermost: {email}")
                return None
            
            response.raise_for_status()
            user_data = response.json()
            
            return user_data.get("id")
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de l'utilisateur dans Mattermost: {str(e)}")
            return None