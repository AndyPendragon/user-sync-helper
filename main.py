#!/usr/bin/env python3
import click
from typing import List, Dict, Optional, Any
import os
from providers.supabase_provider import SupabaseProvider
from providers.casdoor_provider import CasdoorProvider
from models.user import User
from utils.logger import logger, console


class UserSyncTool:
    """Outil de synchronisation des utilisateurs entre Supabase, Casdoor et les applications."""
    
    def __init__(self):
        """Initialise l'outil avec les fournisseurs et connecteurs."""        
        # Vérifier si les variables d'environnement Supabase sont définies
        if not all(key in os.environ for key in ["SUPABASE_URL", "SUPABASE_KEY"]):
            logger.error("Les variables d'environnement pour Supabase ne sont pas définies.")
            raise ValueError("Les variables d'environnement pour Supabase ne sont pas définies.")
        self.supabase = SupabaseProvider()
        self.casdoor = CasdoorProvider()
        
        # Les connecteurs seront initialisés à la demande
        self._mattermost_connector = None
        self._postfix_connector = None
        self._owncloud_connector = None
    
    @property
    def mattermost_connector(self):
        """Initialise le connecteur Mattermost à la demande."""
        if self._mattermost_connector is None:
            from connectors.mattermost_connector import MattermostConnector
            self._mattermost_connector = MattermostConnector()
        return self._mattermost_connector
    
    @property
    def postfix_connector(self):
        """Initialise le connecteur Postfix à la demande."""
        if self._postfix_connector is None:
            from connectors.postfix_connector import PostfixConnector
            self._postfix_connector = PostfixConnector()
        return self._postfix_connector
    
    @property
    def owncloud_connector(self):
        """Initialise le connecteur OwnCloud à la demande."""
        if self._owncloud_connector is None:
            from connectors.owncloud_connector import OwnCloudConnector
            self._owncloud_connector = OwnCloudConnector()
        return self._owncloud_connector
    
    def sync_status(self, apps: List[str] = None) -> Dict[str, Any]:
        """Vérifie l'état des utilisateurs dans toutes les applications spécifiées.
        
        Args:
            apps: Liste des applications à vérifier, par défaut toutes
            
        Returns:
            Dict contenant les statistiques de synchronisation
        """
        if apps is None:
            apps = ["mattermost", "postfix", "owncloud"]
        
        # Vérifier que toutes les applications spécifiées sont valides
        valid_apps = set(["mattermost", "postfix", "owncloud"])
        if not set(apps).issubset(valid_apps):
            invalid_apps = set(apps) - valid_apps
            logger.error(f"Applications invalides spécifiées: {', '.join(invalid_apps)}")
            return {"error": "Applications invalides spécifiées"}
        
        # Récupérer tous les utilisateurs depuis Supabase
        users = self.supabase.get_all_users()
        
        if not users:
            logger.warning("Aucun utilisateur trouvé dans Supabase. Rien à synchroniser.")
            return {"error": "Aucun utilisateur trouvé"}
        
        result = {
            "total_users": len(users),
            "discrepancies": {app: 0 for app in apps},
            "details": []
        }
        
        # Vérifier le statut de chaque utilisateur dans chaque application
        for user in users:
            user_discrepancies = []
            
            for app in apps:
                real_status = self._check_app_status(user, app)
                db_status = user.app_status.get(app)
                
                # Si le statut est connu dans la base de données
                if db_status is not None and real_status is not None:
                    if db_status != real_status:
                        result["discrepancies"][app] += 1
                        user_discrepancies.append({
                            "app": app,
                            "db_status": db_status,
                            "real_status": real_status
                        })
                        
                        # Afficher la différence
                        from utils.logger import log_status_diff
                        log_status_diff(user.username, app, db_status, real_status)
            
            if user_discrepancies:
                result["details"].append({
                    "user": user.username,
                    "email": user.email,
                    "discrepancies": user_discrepancies
                })
        
        # Afficher un résumé
        console.print("\n[bold green]Résumé de la synchronisation:[/bold green]")
        console.print(f"Utilisateurs vérifiés: {result['total_users']}")
        
        for app in apps:
            discrepancies = result["discrepancies"][app]
            if discrepancies > 0:
                console.print(f"[yellow]Divergences dans {app}: {discrepancies}[/yellow]")
            else:
                console.print(f"[green]Aucune divergence dans {app}[/green]")
        
        return result
    
    def _check_app_status(self, user: User, app: str) -> Optional[bool]:
        """Vérifie le statut réel d'un utilisateur dans une application.
        
        Args:
            user: L'utilisateur à vérifier
            app: Le nom de l'application ('mattermost', 'postfix', 'owncloud')
            
        Returns:
            bool ou None: True si actif, False si inactif, None si inconnu
        """
        try:
            if app == "mattermost":
                return self.mattermost_connector.check_user_status(user.email)
            elif app == "postfix":
                return self.postfix_connector.check_user_status(user.email)
            elif app == "owncloud":
                return self.owncloud_connector.check_user_status(user.email)
            else:
                logger.error(f"Application non prise en charge: {app}")
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du statut dans {app}: {str(e)}")
            return None
    
    def apply_status(self, apps: List[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Applique le statut des utilisateurs dans toutes les applications spécifiées.
        
        Args:
            apps: Liste des applications à mettre à jour, par défaut toutes
            dry_run: Si True, n'applique pas réellement les changements
            
        Returns:
            Dict contenant les statistiques des mises à jour
        """
        if apps is None:
            apps = ["mattermost", "postfix", "owncloud"]
        
        # Vérifier que toutes les applications spécifiées sont valides
        valid_apps = set(["mattermost", "postfix", "owncloud"])
        if not set(apps).issubset(valid_apps):
            invalid_apps = set(apps) - valid_apps
            logger.error(f"Applications invalides spécifiées: {', '.join(invalid_apps)}")
            return {"error": "Applications invalides spécifiées"}
        
        # Récupérer tous les utilisateurs depuis Supabase
        users = self.supabase.get_all_users()
        
        if not users:
            logger.warning("Aucun utilisateur trouvé dans Supabase. Rien à appliquer.")
            return {"error": "Aucun utilisateur trouvé"}
        
        result = {
            "total_users": len(users),
            "updates": {app: 0 for app in apps},
            "success": {app: 0 for app in apps},
            "errors": {app: 0 for app in apps},
            "details": []
        }
        
        # Mode simulation
        if dry_run:
            console.print("[bold yellow]Mode simulation activé. Aucune modification ne sera appliquée.[/bold yellow]\n")
        
        # Appliquer le statut pour chaque utilisateur dans chaque application
        for user in users:
            user_updates = []
            
            for app in apps:
                real_status = self._check_app_status(user, app)
                db_status = user.app_status.get(app)
                
                # Si le statut est connu dans la base de données et qu'il diffère du statut réel
                if db_status is not None and real_status is not None and db_status != real_status:
                    result["updates"][app] += 1
                    
                    success = False
                    if not dry_run:
                        success = self._apply_app_status(user, app, db_status)
                    else:
                        # En mode simulation, on simule une réussite
                        success = True
                        
                    user_updates.append({
                        "app": app,
                        "old_status": real_status,
                        "new_status": db_status,
                        "success": success
                    })
                    
                    # Comptabiliser le résultat
                    if success:
                        result["success"][app] += 1
                    else:
                        result["errors"][app] += 1
                    
                    # Afficher l'action
                    action = f"{'Simulation de m' if dry_run else 'M'}ise à jour du statut ({db_status})"
                    from utils.logger import log_action
                    log_action(user.username, app, action, success)
            
            if user_updates:
                result["details"].append({
                    "user": user.username,
                    "email": user.email,
                    "updates": user_updates
                })
        
        # Afficher un résumé
        console.print("\n[bold green]Résumé de l'application des statuts:[/bold green]")
        console.print(f"Utilisateurs traités: {result['total_users']}")
        
        for app in apps:
            updates = result["updates"][app]
            if updates > 0:
                success_rate = (result["success"][app] / updates) * 100 if updates > 0 else 0
                console.print(f"[yellow]Mises à jour dans {app}: {updates} (Réussite: {success_rate:.1f}%)[/yellow]")
            else:
                console.print(f"[green]Aucune mise à jour nécessaire dans {app}[/green]")
        
        return result
    
    def _apply_app_status(self, user: User, app: str, status: bool) -> bool:
        """Applique le statut d'un utilisateur dans une application.
        
        Args:
            user: L'utilisateur à mettre à jour
            app: Le nom de l'application ('mattermost', 'postfix', 'owncloud')
            status: Le statut à appliquer (True pour actif, False pour inactif)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            if app == "mattermost":
                return self.mattermost_connector.update_user_status(user.email, status)
            elif app == "postfix":
                return self.postfix_connector.update_user_status(user.email, status)
            elif app == "owncloud":
                return self.owncloud_connector.update_user_status(user.email, status)
            else:
                logger.error(f"Application non prise en charge: {app}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut dans {app}: {str(e)}")
            return False
    
    def sync_from_casdoor_to_supabase(self) -> Dict[str, Any]:
        """Synchronise les statuts des utilisateurs de Casdoor vers Supabase.
        
        Returns:
            Dict contenant les statistiques de synchronisation
        """
        # Récupérer tous les utilisateurs depuis Casdoor
        casdoor_users = self.casdoor.get_all_users()
        
        if not casdoor_users:
            logger.warning("Aucun utilisateur trouvé dans Casdoor. Rien à synchroniser.")
            return {"error": "Aucun utilisateur trouvé dans Casdoor"}
        
        # Récupérer tous les utilisateurs depuis Supabase
        supabase_users = self.supabase.get_all_users()
        
        # Créer un dictionnaire pour une recherche plus rapide
        supabase_users_dict = {user.email: user for user in supabase_users}
        
        result = {
            "total_casdoor_users": len(casdoor_users),
            "total_supabase_users": len(supabase_users),
            "updates": 0,
            "success": 0,
            "errors": 0,
            "details": []
        }
        
        # Pour chaque utilisateur dans Casdoor
        for casdoor_user in casdoor_users:
            # Trouver l'utilisateur correspondant dans Supabase
            supabase_user = supabase_users_dict.get(casdoor_user.email)
            
            if supabase_user and supabase_user.is_active != casdoor_user.is_active:
                result["updates"] += 1
                
                # Mettre à jour le statut dans Supabase
                success = False
                try:
                    # Nous devons créer un tableau séparé dans Supabase pour stocker le statut global
                    # Pour l'instant, mettons à jour le statut de chaque application
                    for app in ["mattermost", "postfix", "owncloud"]:
                        if supabase_user.app_status.get(app) is not None:
                            self.supabase.update_user_app_status(
                                supabase_user.id, app, casdoor_user.is_active
                            )
                    success = True
                except Exception as e:
                    logger.error(f"Erreur lors de la synchronisation de {casdoor_user.email}: {str(e)}")
                
                # Comptabiliser le résultat
                if success:
                    result["success"] += 1
                else:
                    result["errors"] += 1
                
                # Enregistrer les détails
                result["details"].append({
                    "user": casdoor_user.username,
                    "email": casdoor_user.email,
                    "casdoor_status": casdoor_user.is_active,
                    "supabase_status": supabase_user.is_active,
                    "success": success
                })
                
                # Afficher l'action
                status_text = "actif" if casdoor_user.is_active else "inactif"
                logger.info(f"{'✅' if success else '❌'} Synchronisation de {casdoor_user.email}: {status_text}")
        
        # Afficher un résumé
        console.print("\n[bold green]Résumé de la synchronisation Casdoor → Supabase:[/bold green]")
        console.print(f"Utilisateurs Casdoor: {result['total_casdoor_users']}")
        console.print(f"Utilisateurs Supabase: {result['total_supabase_users']}")
        console.print(f"Mises à jour: {result['updates']}")
        
        if result["updates"] > 0:
            success_rate = (result["success"] / result["updates"]) * 100
            console.print(f"Taux de réussite: {success_rate:.1f}%")
        
        return result


@click.group()
def cli():
    """Outil de synchronisation des utilisateurs entre Supabase, Casdoor et diverses applications."""
    pass


@cli.command()
@click.option("--app", "-a", multiple=True, help="Applications à vérifier (mattermost, postfix, owncloud)")
def check(app):
    """Vérifie le statut des utilisateurs dans les applications."""
    apps = list(app) if app else None
    sync_tool = UserSyncTool()
    sync_tool.sync_status(apps)


@cli.command()
@click.option("--app", "-a", multiple=True, help="Applications à mettre à jour (mattermost, postfix, owncloud)")
@click.option("--dry-run", "-d", is_flag=True, help="Mode simulation, n'applique pas les changements")
def apply(app, dry_run):
    """Applique le statut des utilisateurs dans les applications."""
    apps = list(app) if app else None
    sync_tool = UserSyncTool()
    sync_tool.apply_status(apps, dry_run)


@cli.command()
def sync_casdoor():
    """Synchronise les utilisateurs de Casdoor vers Supabase."""
    sync_tool = UserSyncTool()
    sync_tool.sync_from_casdoor_to_supabase()


if __name__ == "__main__":
    cli()