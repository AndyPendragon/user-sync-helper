from typing import Dict, Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    """Modèle représentant un utilisateur dans le système."""
    
    id: str
    email: str
    username: str
    name: Optional[str] = None
    is_active: bool = True
    
    # Statut de l'utilisateur dans chaque application
    app_status: Dict[str, bool] = Field(default_factory=dict)
    
    @property
    def mattermost_active(self) -> Optional[bool]:
        """Vérifie si l'utilisateur est actif sur Mattermost."""
        return self.app_status.get("mattermost")
    
    @property
    def postfix_active(self) -> Optional[bool]:
        """Vérifie si l'utilisateur est actif sur Postfix."""
        return self.app_status.get("postfix")
    
    @property
    def owncloud_active(self) -> Optional[bool]:
        """Vérifie si l'utilisateur est actif sur OwnCloud."""
        return self.app_status.get("owncloud")

    def __str__(self) -> str:
        return f"User(id={self.id}, email={self.email}, username={self.username}, active={self.is_active})"