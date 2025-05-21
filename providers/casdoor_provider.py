import json
import requests
from typing import List, Dict, Any, Optional

from config import (
    CASDOOR_ENDPOINT,
    CASDOOR_CLIENT_ID,
    CASDOOR_CLIENT_SECRET,
    CASDOOR_ORGANIZATION,
    CASDOOR_APPLICATION
)
from models.user import User
from utils.logger import logger


class CasdoorProvider:
    """Gère la connexion et les opérations avec Casdoor."""
    
    def __init__(self):
        """Initialise la connexion à Casdoor."""
        if not all([
            CASDOOR_ENDPOINT,
            CASDOOR_CLIENT_ID,
            CASDOOR_CLIENT_SECRET,
            CASDOOR_ORGANIZATION,
            CASDOOR_APPLICATION
        ]):
            raise ValueError("Les variables d'environnement pour Casdoor ne sont pas définies.")
        
        self.endpoint = CASDOOR_ENDPOINT.rstrip('/')
        self.client_id = CASDOOR_CLIENT_ID
        self.client_secret = CASDOOR_CLIENT_SECRET
        self.organization = CASDOOR_ORGANIZATION
        self.application = CASDOOR_APPLICATION
        
        # Récupérer le token d'accès
        self.access_token = self._get_access_token()
    
    def _get_access_token(self) -> str:
        """Récupère un token d'accès OAuth depuis Casdoor."""
        try:
            token_url = f"{self.endpoint}/api/login/oauth/access_token"
            
            params = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }
            
            response = requests.post(token_url, data=params)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise ValueError("Aucun token d'accès reçu de Casdoor")
                
            logger.info("Token d'accès Casdoor récupéré avec succès")
            return access_token
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du token d'accès Casdoor: {str(e)}")
            raise
    
    def get_all_users(self) -> List[User]:
        """Récupère tous les utilisateurs depuis Casdoor."""
        try:
            users_url = f"{self.endpoint}/api/get-users?owner={self.organization}"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            response = requests.get(users_url, headers=headers)
            response.raise_for_status()
            
            users_data = response.json()
            
            if not users_data or "data" not in users_data:
                logger.warning("Aucun utilisateur trouvé dans Casdoor.")
                return []
            
            # Convertir les données en objets User
            users = []
            for user_data in users_data["data"]:
                user = User(
                    id=user_data.get("id", user_data.get("name")),  # Fallback au nom si id n'existe pas
                    email=user_data.get("email", ""),
                    username=user_data.get("name", ""),
                    name=user_data.get("displayName", ""),
                    is_active=not user_data.get("isDeleted", False) and not user_data.get("isForbidden", False),
                    # Casdoor ne connait pas le statut des applications, donc on laisse vide
                    app_status={}
                )
                users.append(user)
            
            logger.info(f"Récupération de {len(users)} utilisateurs depuis Casdoor.")
            return users
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs depuis Casdoor: {str(e)}")
            return []
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur de Casdoor par son adresse email."""
        try:
            # Casdoor n'a pas d'API directe pour rechercher par email, utilisons la liste complète
            all_users = self.get_all_users()
            for user in all_users:
                if user.email.lower() == email.lower():
                    return user
            
            logger.warning(f"Aucun utilisateur trouvé dans Casdoor avec l'email: {email}")
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur par email depuis Casdoor: {str(e)}")
            return None
    
    def update_user_status(self, user_id: str, is_active: bool) -> bool:
        """Met à jour le statut d'un utilisateur dans Casdoor.
        
        Args:
            user_id: ID de l'utilisateur à mettre à jour
            is_active: Nouveau statut (True pour actif, False pour inactif)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # D'abord récupérer l'utilisateur complet
            user_url = f"{self.endpoint}/api/get-user?id={self.organization}/{user_id}"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            response = requests.get(user_url, headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            
            if not user_data or "data" not in user_data or not user_data["data"]:
                logger.warning(f"Utilisateur non trouvé dans Casdoor: {user_id}")
                return False
            
            # Mettre à jour le statut
            user_obj = user_data["data"]
            user_obj["isForbidden"] = not is_active
            
            # Envoyer la mise à jour
            update_url = f"{self.endpoint}/api/update-user"
            response = requests.post(
                update_url,
                headers={**headers, "Content-Type": "application/json"},
                data=json.dumps(user_obj)
            )
            response.raise_for_status()
            
            logger.info(f"Statut de l'utilisateur {user_id} mis à jour dans Casdoor: {'actif' if is_active else 'inactif'}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut dans Casdoor: {str(e)}")
            return False