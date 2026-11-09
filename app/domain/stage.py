from dataclasses import dataclass, field

from app.domain.errors import RuleViolation
from app.domain.value_objects import EquipmentSet


@dataclass(eq=False)
class Stage:
    """Agrégat Scène. Elle référence son festival par identifiant."""

    id: int | None
    festival_id: int
    name: str
    capacity: int
    available_equipment: EquipmentSet = field(default_factory=EquipmentSet)

    def __post_init__(self):
        if self.capacity <= 0:  # R9
            raise RuleViolation("La capacité d'une scène doit être strictement positive")
