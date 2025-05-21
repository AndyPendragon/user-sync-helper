import requests
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict

from config import OWNCLOUD_URL, OWNCLOUD_ADMIN_USER, OWNCLOUD_ADMIN_PASSWORD
from utils.logger import logger


class OwnCloudConnector:
    """Gère la connexion et les opérations avec OwnCloud via son API WebDAV et OCS."""
    
    def __init__(self):
        """Initialise la connexion à OwnCloud."""
        if not all([OWNCLOUD_URL, OWNCLOUD_ADMIN_USER, OWNCLOUD_ADMIN_PASSWORD]):
            raise ValueError("Les variables d'environnement pour OwnCloud ne sont pas définies.")
        
        self.url = OWNCLOUD_URL.rstrip('/')
        self.admin_user = OWNCLOUD_ADMIN_USER
        self.admin_password = OWNCLOUD_ADMIN_PASSWORD
        
        # URL de base pour l'API OCS
        self.ocs_base_url = f"{self.url}/ocs/v1.php"
        
        # Vérifier la connexion au démarrage
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Teste la connexion à OwnCloud."""
        try:
            # Tester la connexion en récupérant les informations du serveur
            url = f"{self.ocs_base_url}/cloud/capabilities"
            
            response = requests.get(
                url,
                auth=(self.admin_user, self.admin_password),
                headers={"OCS-APIRequest": "true"},
                params={"format": "json"}
            )
            response.raise_for_status()
            
            logger.info("Connexion réussie à OwnCloud")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du test de connexion à OwnCloud: {str(e)}")
            raise
    
    def check_user_status(self, email: str) -> Optional[bool]:
        """Vérifie si un utilisateur est actif dans OwnCloud.
        
        Args:
            email: Email de l'utilisateur à vérifier
            
        Returns:
            bool ou None: True si actif, False si inactif, None si erreur ou utilisateur non trouvé
        """
        try:
            # Extraire le nom d'utilisateur de l'email (dans certaines configurations OwnCloud)
            # On suppose que le nom d'utilisateur est la partie avant @
            username = email.split('@')[0]
            
            # Essayer d'abord avec l'email complet
            user_info = self._get_user_info(email)
            
            # Si non trouvé, essayer avec le nom d'utilisateur
            if not user_info and username != email:
                user_info = self._get_user_info(username)
            
            if not user_info:
                logger.warning(f"Utilisateur non trouvé dans OwnCloud: {email}")
                return None
            
            # Vérifier si l'utilisateur est activé
            is_active = user_info.get("enabled", "false").lower() == "true"
            
            logger.info(f"Statut de l'utilisateur {email} dans OwnCloud: {'actif' if is_active else 'inactif'}")
            return is_active
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du statut dans OwnCloud: {str(e)}")
            return None
    
    def update_user_status(self, email: str, is_active: bool) -> bool:
        """Met à jour le statut d'un utilisateur dans OwnCloud.
        
        Args:
            email: Email de l'utilisateur à mettre à jour
            is_active: Nouveau statut (True pour actif, False pour inactif)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Extraire le nom d'utilisateur de l'email
            username = email.split('@')[0]
            
            # Trouver le bon identifiant utilisateur
            found_username = None
            
            # Essayer d'abord avec l'email complet
            user_info = self._get_user_info(email)
            if user_info:
                found_username = email
            
            # Si non trouvé, essayer avec le nom d'utilisateur
            if not user_info and username != email:
                user_info = self._get_user_info(username)
                if user_info:
                    found_username = username
            
            if not found_username:
                logger.warning(f"Utilisateur non trouvé dans OwnCloud: {email}")
                return False
            
            # Construire l'URL pour mettre à jour l'utilisateur
            url = f"{self.ocs_base_url}/cloud/users/{found_username}/enable"
            
            if not is_active:
                url = f"{self.ocs_base_url}/cloud/users/{found_username}/disable"
            
            # Envoyer la requête pour activer/désactiver l'utilisateur
            response = requests.put(
                url,
                auth=(self.admin_user, self.admin_password),
                headers={"OCS-APIRequest": "true"},
                params={"format": "json"}
            )
            
            # Vérifier le statut de la réponse
            if response.status_code in [200, 201, 100]:
                action = "activé" if is_active else "désactivé"
                logger.info(f"Utilisateur {found_username} {action} avec succès dans OwnCloud")
                return True
            else:
                logger.error(f"Erreur lors de la mise à jour du statut de l'utilisateur dans OwnCloud: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut dans OwnCloud: {str(e)}")
            return False
    
    def _get_user_info(self, user_id: str) -> Optional[Dict]:
        """Récupère les informations d'un utilisateur dans OwnCloud.
        
        Args:
            user_id: Identifiant de l'utilisateur (email ou nom d'utilisateur)
            
        Returns:
            dict ou None: Informations de l'utilisateur, ou None si erreur ou utilisateur non trouvé
        """
        try:
            url = f"{self.ocs_base_url}/cloud/users/{user_id}"
            
            response = requests.get(
                url,
                auth=(self.admin_user, self.admin_password),
                headers={"OCS-APIRequest": "true"},
                params={"format": "xml"}  # L'API OwnCloud retourne parfois des formats différents selon l'endpoint
            )
            
            # Si l'utilisateur n'existe pas, OwnCloud retourne généralement un code 404 ou 997 (dans le corps OCS)
            if response.status_code == 404:
                return None
            
            # Parser la réponse XML
            root = ET.fromstring(response.text)
            
            # Vérifier le statut de la réponse OCS
            status_code = root.find(".//statuscode")
            if status_code is not None and status_code.text == "997":  # Code d'erreur OwnCloud pour utilisateur non trouvé
                return None
            
            # Extraire les données utilisateur
            data = {}
            data_elem = root.find(".//data")
            
            if data_elem is not None:
                for child in data_elem:
                    data[child.tag] = child.text
            
            return data
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations utilisateur depuis OwnCloud: {str(e)}")
            return None
    
    def create_user(self, email: str, display_name: str, password: str) -> bool:
        """Crée un nouvel utilisateur dans OwnCloud.
        
        Args:
            email: Email de l'utilisateur (servira d'identifiant)
            display_name: Nom complet à afficher
            password: Mot de passe initial
            
        Returns:
            bool: True si la création a réussi, False sinon
        """
        try:
            # Extraire le nom d'utilisateur de l'email pour certaines configurations OwnCloud
            username = email.split('@')[0]
            
            # Vérifier si l'utilisateur existe déjà
            if self._get_user_info(email) or (username != email and self._get_user_info(username)):
                logger.warning(f"L'utilisateur {email} existe déjà dans OwnCloud")
                return False
            
            # URL pour créer un utilisateur
            url = f"{self.ocs_base_url}/cloud/users"
            
            # Données pour la création de l'utilisateur
            data = {
                "userid": email,  # Utiliser l'email comme identifiant
                "password": password,
                "displayName": display_name,
                "email": email
            }
            
            # Envoyer la requête
            response = requests.post(
                url,
                auth=(self.admin_user, self.admin_password),
                headers={"OCS-APIRequest": "true"},
                params={"format": "json"},
                data=data
            )
            
            # Vérifier le statut de la réponse
            if response.status_code in [200, 201, 100]:
                logger.info(f"Utilisateur {email} créé avec succès dans OwnCloud")
                return True
            else:
                logger.error(f"Erreur lors de la création de l'utilisateur dans OwnCloud: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'utilisateur dans OwnCloud: {str(e)}")
            return False
    
    def delete_user(self, email: str) -> bool:
        """Supprime un utilisateur de OwnCloud.
        
        Args:
            email: Email de l'utilisateur à supprimer
            
        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        try:
            # Extraire le nom d'utilisateur de l'email
            username = email.split('@')[0]
            
            # Trouver le bon identifiant utilisateur
            found_username = None
            
            # Essayer d'abord avec l'email complet
            if self._get_user_info(email):
                found_username = email
            
            # Si non trouvé, essayer avec le nom d'utilisateur
            elif username != email and self._get_user_info(username):
                found_username = username
            
            if not found_username:
                logger.warning(f"Utilisateur non trouvé dans OwnCloud: {email}")
                return False
            
            # URL pour supprimer l'utilisateur
            url = f"{self.ocs_base_url}/cloud/users/{found_username}"
            
            # Envoyer la requête
            response = requests.delete(
                url,
                auth=(self.admin_user, self.admin_password),
                headers={"OCS-APIRequest": "true"},
                params={"format": "json"}
            )
            
            # Vérifier le statut de la réponse
            if response.status_code in [200, 201, 100]:
                logger.info(f"Utilisateur {found_username} supprimé avec succès de OwnCloud")
                return True
            else:
                logger.error(f"Erreur lors de la suppression de l'utilisateur de OwnCloud: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'utilisateur de OwnCloud: {str(e)}")
            return False
    
    def reset_user_password(self, email: str, new_password: str) -> bool:
        """Réinitialise le mot de passe d'un utilisateur dans OwnCloud.
        
        Args:
            email: Email de l'utilisateur
            new_password: Nouveau mot de passe
            
        Returns:
            bool: True si la réinitialisation a réussi, False sinon
        """
        try:
            # Extraire le nom d'utilisateur de l'email
            username = email.split('@')[0]
            
            # Trouver le bon identifiant utilisateur
            found_username = None
            
            # Essayer d'abord avec l'email complet
            if self._get_user_info(email):
                found_username = email
            
            # Si non trouvé, essayer avec le nom d'utilisateur
            elif username != email and self._get_user_info(username):
                found_username = username
            
            if not found_username:
                logger.warning(f"Utilisateur non trouvé dans OwnCloud: {email}")
                return False
            
            # URL pour changer le mot de passe
            url = f"{self.ocs_base_url}/cloud/users/{found_username}"
            
            # Données pour la mise à jour
            data = {
                "key": "password",
                "value": new_password
            }
            
            # Envoyer la requête
            response = requests.put(
                url,
                auth=(self.admin_user, self.admin_password),
                headers={"OCS-APIRequest": "true"},
                params={"format": "json"},
                data=data
            )
            
            # Vérifier le statut de la réponse
            if response.status_code in [200, 201, 100]:
                logger.info(f"Mot de passe de l'utilisateur {found_username} réinitialisé avec succès dans OwnCloud")
                return True
            else:
                logger.error(f"Erreur lors de la réinitialisation du mot de passe dans OwnCloud: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation du mot de passe dans OwnCloud: {str(e)}")
            return False
    
    def list_users(self) -> List[str]:
        """Liste tous les utilisateurs dans OwnCloud.
        
        Returns:
            list: Liste des identifiants utilisateurs
        """
        try:
            # URL pour lister les utilisateurs
            url = f"{self.ocs_base_url}/cloud/users"
            
            # Envoyer la requête
            response = requests.get(
                url,
                auth=(self.admin_user, self.admin_password),
                headers={"OCS-APIRequest": "true"},
                params={"format": "xml"}
            )
            
            # Parser la réponse XML
            root = ET.fromstring(response.text)
            
            # Extraire les identifiants utilisateurs
            users = []
            data_elem = root.find(".//data")
            
            if data_elem is not None:
                for element in data_elem:
                    if element.tag == "element":
                        users.append(element.text)
            
            logger.info(f"Liste des utilisateurs récupérée avec succès: {len(users)} utilisateurs trouvés")
            return users
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la liste des utilisateurs depuis OwnCloud: {str(e)}")
            return []