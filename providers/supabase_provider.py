from typing import List, Dict, Any, Optional
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_USERS_TABLE
from models.user import User
from utils.logger import logger


class SupabaseProvider:
    """Gère la connexion et les opérations avec Supabase."""
    
    def __init__(self):
        """Initialise la connexion à Supabase."""
        if not all([SUPABASE_URL, SUPABASE_KEY]):
            raise ValueError("Les variables d'environnement pour Supabase ne sont pas définies.")
        
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.table = SUPABASE_USERS_TABLE
    
    def get_all_users(self) -> List[User]:
        """Récupère tous les utilisateurs depuis Supabase."""
        try:
            response = self.client.table(self.table).select("*").execute()
            
            if not response.data:
                logger.warning("Aucun utilisateur trouvé dans Supabase.")
                return []
            
            # Convertir les données en objets User
            users = []
            for user_data in response.data:
                user = User(
                    id=user_data.get("id"),
                    email=user_data.get("email"),
                    username=user_data.get("username"),
                    name=user_data.get("name"),
                    is_active=user_data.get("is_active", True),
                    app_status={
                        "mattermost": user_data.get("mattermost_active", None),
                        "postfix": user_data.get("postfix_active", None),
                        "owncloud": user_data.get("owncloud_active", None)
                    }
                )
                users.append(user)
            
            logger.info(f"Récupération de {len(users)} utilisateurs depuis Supabase.")
            return users
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs depuis Supabase: {str(e)}")
            return []
    
    def update_user_app_status(self, user_id: str, app_name: str, is_active: bool) -> bool:
        """Met à jour le statut d'une application pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur à mettre à jour
            app_name: Nom de l'application ('mattermost', 'postfix', 'owncloud')
            is_active: Nouveau statut (True pour actif, False pour inactif)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Vérifier que l'app_name est valide
            if app_name not in ["mattermost", "postfix", "owncloud"]:
                logger.error(f"Nom d'application invalide: {app_name}")
                return False
                
            # Mettre à jour le statut
            column_name = f"{app_name}_active"
            
            response = self.client.table(self.table).update({
                column_name: is_active
            }).eq("id", user_id).execute()
            
            if response.data:
                logger.info(f"Statut de {app_name} mis à jour pour l'utilisateur {user_id}: {is_active}")
                return True
            else:
                logger.warning(f"Aucune mise à jour effectuée pour l'utilisateur {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut dans Supabase: {str(e)}")
            return False
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par son adresse email."""
        try:
            response = self.client.table(self.table).select("*").eq("email", email).execute()
            
            if not response.data:
                logger.warning(f"Aucun utilisateur trouvé avec l'email: {email}")
                return None
            
            user_data = response.data[0]
            return User(
                id=user_data.get("id"),
                email=user_data.get("email"),
                username=user_data.get("username"),
                name=user_data.get("name"),
                is_active=user_data.get("is_active", True),
                app_status={
                    "mattermost": user_data.get("mattermost_active", None),
                    "postfix": user_data.get("postfix_active", None),
                    "owncloud": user_data.get("owncloud_active", None)
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur par email: {str(e)}")
            return None