from dataclasses import dataclass, field

from app.domain.errors import RuleViolation
from app.domain.value_objects import EquipmentSet


@dataclass(eq=False)
class Artist:
    """Agrégat Artiste : un groupe et ses besoins techniques."""

    id: int | None
    name: str
    genre: str
    required_equipment: EquipmentSet = field(default_factory=EquipmentSet)

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise RuleViolation("Le nom de l'artiste est obligatoire")
