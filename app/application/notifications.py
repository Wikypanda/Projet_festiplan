"""Réaction aux événements de domaine : envoi des notifications.

Correction du défaut 2 : la notification est un EFFET SECONDAIRE. Elle est
déclenchée après l'enregistrement de la modification, et son échec ne doit
jamais faire croire que l'opération métier a échoué. L'échec est journalisé
et renvoyé sous forme d'avertissement à l'appelant.
"""
import logging
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from app.application.ports import Notifier
from app.domain.events import ConcertCancelled, ConcertRescheduled, DomainEvent, PlanningPublished

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class OperationResult(Generic[T]):
    """Résultat d'une opération métier réussie + avertissements éventuels."""

    value: T
    warnings: list[str] = field(default_factory=list)


class NotificationHandler:
    def __init__(self, notifier: Notifier):
        self.notifier = notifier

    def handle(self, events: list[DomainEvent]) -> list[str]:
        warnings = []
        for event in events:
            subject, message = self._describe(event)
            try:
                self.notifier.send(subject, message)
            except Exception as exc:  # l'effet secondaire ne doit pas casser l'opération
                logger.warning("Échec de notification pour %s : %s", event, exc)
                warnings.append(f"La modification est enregistrée, mais la notification n'a pas pu être envoyée ({exc})")
        return warnings

    @staticmethod
    def _describe(event: DomainEvent) -> tuple[str, str]:
        if isinstance(event, ConcertRescheduled):
            message = f"Concert déplacé au {event.new_slot.start.isoformat()} (fin {event.new_slot.end.isoformat()})"
            if event.reason:
                message += f" — planning publié modifié, motif : {event.reason}"
            return f"Modification du concert #{event.concert_id}", message
        if isinstance(event, ConcertCancelled):
            return f"Annulation du concert #{event.concert_id}", "Le concert a été annulé."
        if isinstance(event, PlanningPublished):
            return f"Publication du festival #{event.festival_id}", f"Le planning du festival {event.festival_name} a été publié."
        raise ValueError(f"Événement non géré : {event!r}")
