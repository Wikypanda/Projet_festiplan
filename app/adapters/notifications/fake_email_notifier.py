from app.application.ports import Notifier


class FakeEmailNotifier(Notifier):
    """Faux expéditeur d'emails : affiche le message au lieu de l'envoyer.

    `fail=True` simule une panne du service (FESTIPLAN_FAIL_NOTIFICATIONS=true).
    """

    def __init__(self, recipient: str = "production@festiplan.test", fail: bool = False):
        self.recipient = recipient
        self.fail = fail

    def send(self, subject: str, message: str) -> None:
        if self.fail:
            raise RuntimeError("Simulation : le service de notification est indisponible")
        print(f"[FAKE EMAIL] to={self.recipient} subject={subject} body={message}")
