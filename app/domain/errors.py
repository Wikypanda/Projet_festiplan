"""Erreurs métier. Elles ne connaissent rien de HTTP : c'est l'adaptateur
FastAPI qui décide du code de réponse associé à chacune."""


class DomainError(Exception):
    """Classe de base de toutes les erreurs métier."""


class NotFound(DomainError):
    """Un objet référencé n'existe pas (R4, R10)."""


class RuleViolation(DomainError):
    """Une donnée viole une règle métier (R1, R4, R5, R6, R9, R10...)."""


class SchedulingConflict(DomainError):
    """Le créneau demandé entre en conflit avec un autre concert (R2, R3)."""


class InvalidStateTransition(DomainError):
    """L'opération n'est pas autorisée dans l'état actuel (R7, R8)."""


class PlanningNotPublishable(InvalidStateTransition):
    """Le planning contient des concerts qui ne respectent pas les règles (R8)."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Le planning ne peut pas être publié : " + " ; ".join(problems))
