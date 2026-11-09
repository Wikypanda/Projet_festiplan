from dataclasses import dataclass
from datetime import datetime

from app.domain.errors import RuleViolation


@dataclass(eq=False)
class Incident:
    """Agrégat Incident, rattaché à un concert par son identifiant."""

    id: int | None
    concert_id: int
    description: str
    occurred_at: datetime
    resolved: bool = False

    def __post_init__(self):
        if not self.description or not self.description.strip():  # R10
            raise RuleViolation("La description de l'incident est obligatoire")
