import subprocess
import re
from typing import Optional, List, Dict

from config import POSTFIX_SERVER, POSTFIX_ADMIN_USER, POSTFIX_ADMIN_PASSWORD
from utils.logger import logger


class PostfixConnector:
    """Gère la connexion et les opérations avec Postfix.
    
    Cette classe utilise des commandes shell pour interagir avec Postfix
    via SSH ou des commandes locales, selon la configuration.
    """
    
    def __init__(self):
        """Initialise la connexion à Postfix."""
        if not POSTFIX_SERVER:
            logger.warning("La variable d'environnement POSTFIX_SERVER n'est pas définie. Utilisation du serveur local.")
            self.server = "localhost"
        else:
            self.server = POSTFIX_SERVER
        
        self.admin_user = POSTFIX_ADMIN_USER
        self.admin_password = POSTFIX_ADMIN_PASSWORD
        
        # Vérifier si le serveur est accessible
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Teste la connexion au serveur Postfix."""
        try:
            if self.server == "localhost":
                # Exécuter une commande locale pour vérifier si Postfix est installé
                result = subprocess.run(
                    ["postconf", "-d", "mail_version"],
                    capture_output=True, text=True, timeout=5
                )
                
                if result.returncode != 0:
                    logger.error("Postfix n'est pas installé sur le serveur local.")
                    raise ValueError("Postfix n'est pas installé sur le serveur local.")
                
                logger.info(f"Connexion réussie à Postfix local: {result.stdout.strip()}")
            else:
                # Exécuter une commande SSH pour vérifier la connexion
                ssh_cmd = [
                    "ssh",
                    "-o", "BatchMode=yes",
                    "-o", "ConnectTimeout=5",
                    f"{self.admin_user}@{self.server}",
                    "postconf -d mail_version"
                ]
                
                result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode != 0:
                    logger.error(f"Erreur de connexion SSH au serveur Postfix: {result.stderr}")
                    raise ValueError(f"Erreur de connexion SSH au serveur Postfix: {result.stderr}")
                
                logger.info(f"Connexion réussie au serveur Postfix distant: {result.stdout.strip()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du test de connexion à Postfix: {str(e)}")
            raise
    
    def check_user_status(self, email: str) -> Optional[bool]:
        """Vérifie si un utilisateur est actif dans Postfix.
        
        Args:
            email: Email de l'utilisateur à vérifier
            
        Returns:
            bool ou None: True si actif, False si inactif, None si erreur ou utilisateur non trouvé
        """
        try:
            # Extraction du domaine de l'email
            domain = email.split('@')[-1]
            username = email.split('@')[0]
            
            # Commande pour vérifier si l'adresse email est active
            if self.server == "localhost":
                cmd = [
                    "postmap", "-q", email, "virtual_mailbox_maps"
                ]
            else:
                cmd = [
                    "ssh", f"{self.admin_user}@{self.server}",
                    f"postmap -q {email} virtual_mailbox_maps"
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # Si la commande renvoie quelque chose, l'utilisateur existe et est actif
            is_active = result.returncode == 0 and result.stdout.strip() != ""
            
            # Vérifier également si l'utilisateur est dans la table des redirections
            # (certaines configurations utilisent virtual_alias_maps au lieu de virtual_mailbox_maps)
            if not is_active:
                if self.server == "localhost":
                    cmd_alias = [
                        "postmap", "-q", email, "virtual_alias_maps"
                    ]
                else:
                    cmd_alias = [
                        "ssh", f"{self.admin_user}@{self.server}",
                        f"postmap -q {email} virtual_alias_maps"
                    ]
                
                result_alias = subprocess.run(cmd_alias, capture_output=True, text=True, timeout=10)
                is_active = result_alias.returncode == 0 and result_alias.stdout.strip() != ""
            
            # Si l'utilisateur n'est pas trouvé directement, vérifier si le domaine existe
            if not is_active:
                # Vérifier si l'utilisateur existe dans la base de données Postfix
                if self.server == "localhost":
                    cmd_check = [
                        "grep", "-E", f"^{username}@{domain}", "/etc/postfix/virtual_mailbox"
                    ]
                else:
                    cmd_check = [
                        "ssh", f"{self.admin_user}@{self.server}",
                        f"grep -E '^{username}@{domain}' /etc/postfix/virtual_mailbox"
                    ]
                
                result_check = subprocess.run(cmd_check, capture_output=True, text=True, timeout=10)
                is_active = result_check.returncode == 0 and "#" not in result_check.stdout
            
            logger.info(f"Statut de l'utilisateur {email} dans Postfix: {'actif' if is_active else 'inactif ou non trouvé'}")
            return is_active
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du statut dans Postfix: {str(e)}")
            return None
    
    def update_user_status(self, email: str, is_active: bool) -> bool:
        """Met à jour le statut d'un utilisateur dans Postfix.
        
        Args:
            email: Email de l'utilisateur à mettre à jour
            is_active: Nouveau statut (True pour actif, False pour inactif)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Extraction du domaine de l'email
            domain = email.split('@')[-1]
            username = email.split('@')[0]
            mailbox = f"{domain}/{username}/"
            
            # Commandes pour activer/désactiver l'utilisateur
            if is_active:
                # Activer l'utilisateur
                if self.server == "localhost":
                    # Ajouter/décommenter l'utilisateur dans le fichier virtual_mailbox
                    cmd_activate = [
                        "sed", "-i",
                        f"s/^#*{username}@{domain}[[:space:]]*{domain}\\/{username}\\//"\
                        f"{username}@{domain} {domain}\\/{username}\\//g",
                        "/etc/postfix/virtual_mailbox"
                    ]
                else:
                    cmd_activate = [
                        "ssh", f"{self.admin_user}@{self.server}",
                        f"sed -i 's/^#*{username}@{domain}[[:space:]]*{domain}\\/{username}\\//"\
                        f"{username}@{domain} {domain}\\/{username}\\//g' /etc/postfix/virtual_mailbox"
                    ]
                
                result = subprocess.run(cmd_activate, capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    logger.error(f"Erreur lors de l'activation de l'utilisateur dans Postfix: {result.stderr}")
                    return False
                
                # Mettre à jour la table Postfix
                if self.server == "localhost":
                    cmd_update = ["postmap", "/etc/postfix/virtual_mailbox"]
                else:
                    cmd_update = [
                        "ssh", f"{self.admin_user}@{self.server}",
                        "postmap /etc/postfix/virtual_mailbox"
                    ]
                
                result_update = subprocess.run(cmd_update, capture_output=True, text=True, timeout=10)
                
                if result_update.returncode != 0:
                    logger.error(f"Erreur lors de la mise à jour de la table Postfix: {result_update.stderr}")
                    return False
                
                logger.info(f"Utilisateur {email} activé dans Postfix")
                return True
                
            else:
                # Désactiver l'utilisateur
                if self.server == "localhost":
                    # Commenter l'utilisateur dans le fichier virtual_mailbox
                    cmd_deactivate = [
                        "sed", "-i",
                        f"s/^{username}@{domain}[[:space:]]*{domain}\\/{username}\\//"\
                        f"#{username}@{domain} {domain}\\/{username}\\//g",
                        "/etc/postfix/virtual_mailbox"
                    ]
                else:
                    cmd_deactivate = [
                        "ssh", f"{self.admin_user}@{self.server}",
                        f"sed -i 's/^{username}@{domain}[[:space:]]*{domain}\\/{username}\\//"\
                        f"#{username}@{domain} {domain}\\/{username}\\//g' /etc/postfix/virtual_mailbox"
                    ]
                
                result = subprocess.run(cmd_deactivate, capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    logger.error(f"Erreur lors de la désactivation de l'utilisateur dans Postfix: {result.stderr}")
                    return False
                
                # Mettre à jour la table Postfix
                if self.server == "localhost":
                    cmd_update = ["postmap", "/etc/postfix/virtual_mailbox"]
                else:
                    cmd_update = [
                        "ssh", f"{self.admin_user}@{self.server}",
                        "postmap /etc/postfix/virtual_mailbox"
                    ]
                
                result_update = subprocess.run(cmd_update, capture_output=True, text=True, timeout=10)
                
                if result_update.returncode != 0:
                    logger.error(f"Erreur lors de la mise à jour de la table Postfix: {result_update.stderr}")
                    return False
                
                logger.info(f"Utilisateur {email} désactivé dans Postfix")
                return True
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut dans Postfix: {str(e)}")
            return False