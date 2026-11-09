# Étape 1 — Diagnostic de l'architecture initiale

> Ce diagnostic décrit le code **avant** refactorisation (dossiers `app/api`, `app/services`,
> `app/repositories`, `app/utils`, `app/models.py`, `app/schemas.py`, `app/database.py`, aujourd'hui supprimés).

## 1. Responsabilités de chaque partie

| Partie | Rôle attendu | Ce qu'elle fait réellement |
|---|---|---|
| `app/api/*.py` (routes FastAPI) | Traduire HTTP ↔ application | Traduit HTTP, **mais** interroge aussi SQLAlchemy directement (`concerts.get_concert`, `concerts.reschedule_concert`, tout `incidents.py`) et duplique des règles (R1 dans `reschedule_concert`) |
| `app/services/*.py` | Règles métier / orchestration | Mélange règles métier, requêtes SQLAlchemy (`db.query(...)`), `commit()` et envoi de notifications. Chaque service **instancie lui-même** ses dépendances (`ConcertRepository(db)`, `NotificationService()`) |
| `app/repositories/*.py` | Accès aux données | CRUD minimal, chaque `create()` fait son propre `commit()`. Les services les contournent souvent |
| `app/models.py` | Tables SQLAlchemy | Utilisé partout comme « modèle métier » : les règles manipulent des objets ORM, statuts en chaînes libres (`"published"`, `"cancelled"`), équipements en chaîne `"a,b,c"` |
| `app/schemas.py` (Pydantic) | Format des requêtes | Seule protection de R9 (`capacity > 0`) et de R10 (`min_length=3`) |
| `app/utils/email_sender.py` | Envoi d'email | Lit la configuration globale `settings` ; appelé directement par `NotificationService` |

## 2. Dépendances

```
           ┌────────────────────────────── app/api (FastAPI) ──────────────────────────────┐
           │  festivals.py   artists.py   stages.py   concerts.py   incidents.py           │
           └──────┬──────────────────────────────────────────┬──────────────┬─────────────┘
                  │ instancie                                 │ db.query()   │ db.query()
                  ▼                                           ▼              ▼
   ┌──────── app/services ─────────┐                 ┌───────────── app/models (ORM) ─────┐
   │ SchedulingService(db)         │── db.query() ──▶│ Festival  Artist  Stage  Concert   │
   │ PublicationService(db)        │── commit() ────▶│ Incident                           │
   │ FestivalService, StageService │                 └──────────────▲─────────────────────┘
   └──────┬───────────────┬────────┘                                │
          │ instancie     │ instancie                               │
          ▼               ▼                                         │
 app/repositories   NotificationService ─▶ utils/email_sender ─▶ config.settings (global)
 (Session SQLAlchemy) ───────────────────────────────────────────────┘
```

Toutes les flèches vont vers SQLAlchemy : **il n'existe aucun code métier indépendant de la base**.

## 3. Où se trouvaient les règles métier

| Règle | Emplacement initial | Problème |
|---|---|---|
| R1 fin > début | `SchedulingService.create_concert`, `reschedule_concert` **et** `api/concerts.py` | Dupliquée 3 fois |
| R2 / R3 chevauchements | `SchedulingService._check_conflicts` | Appelée **uniquement à la création** → défaut 1 |
| R4 références | `create_concert` (une seule erreur 400 pour 3 cas) | Absente du déplacement |
| R5 équipements | `create_concert`, découpage de chaînes `"a,b"` | Logique de parsing mêlée à la règle |
| R6 période | `create_concert` | Absente du déplacement |
| R7 planning publié | **Nulle part** | Défaut 3 |
| R8 publication valide | **Nulle part** (commentaire « contrôle incomplet ») | Publication d'un planning incohérent possible |
| R9 capacité > 0 | Pydantic (`Field(gt=0)`) uniquement | Contournable hors HTTP (seed, script, test) |
| R10 incident | Route `incidents.py` (existence) + Pydantic `min_length=3` | Une description `"   "` (3 espaces) est acceptée |

## 4. Dépendances directes à FastAPI et SQLAlchemy

- Tous les services reçoivent une `sqlalchemy.orm.Session` dans leur constructeur.
- `api/concerts.py` et `api/incidents.py` font des requêtes SQLAlchemy dans les contrôleurs.
- Les règles métier manipulent des objets ORM (`Concert`, `Stage`) → impossibles à utiliser sans base.
- `NotificationService` appelle `send_email`, qui lit `settings` global : impossible d'injecter un double de test.

## 5. Testabilité et risques d'incohérence

- **Testabilité** : pour tester « deux concerts ne se chevauchent pas », il faut une base SQLite, des lignes en
  base et souvent un `TestClient`. Les 6 tests fournis ne vérifient que des validations de format.
- **Effets secondaires couplés** : `reschedule_concert` fait `commit()` puis notifie ; une panne de notification
  devient une erreur 500 alors que la donnée est modifiée (défaut 2). Même chose pour `publish`.
- **Pas d'état métier explicite** : `status` est une chaîne libre, aucune transition n'est contrôlée.
- **Bug annexe** : la notification de publication passe l'id du *festival* à `notify_schedule_change(concert_id, …)`
  → sujet « Modification du concert #1 » pour une publication.

## 6. Exemple concret de responsabilité mal placée

`PATCH /concerts/{id}/reschedule` (fichier `app/api/concerts.py` initial) :

```python
concert = db.query(Concert).filter(Concert.id == concert_id).first()   # SQL dans le contrôleur
if payload.end_time <= payload.start_time:                              # règle R1 dans le contrôleur
    raise HTTPException(400, ...)
return SchedulingService(db).reschedule_concert(concert_id, payload)    # service instancié ici
...
except RuntimeError as exc:                                             # panne de notification
    raise HTTPException(status_code=500, ...)                           # → 500 après commit
```

Et dans `SchedulingService.reschedule_concert` : pas de contrôle de conflit, de période ni de statut,
`self.db.commit()` puis `self.notifications.notify_schedule_change(...)`.
Une seule opération mélange donc HTTP, SQL, règles métier partielles et effet secondaire.

## 7. Reproduction des trois défauts

### Pas à pas (Swagger ou curl, après `python -m app.seed`)

Dans les données de démo, le concert #1 (Iron Vow) occupe Mainstage de 18h00 à 19h00 le 18/06.

| Défaut | Étapes | Résultat observé sur le code initial |
|---|---|---|
| 1 | `PATCH /concerts/2/reschedule` `{"start_time":"2027-06-18T18:30:00","end_time":"2027-06-18T19:30:00"}` | **200** : le concert #2 chevauche le #1 sur Mainstage |
| 2 | `FESTIPLAN_FAIL_NOTIFICATIONS=true`, puis même requête, puis `GET /concerts/2` | **500** « service de notification indisponible »… mais `GET` montre que le déplacement **est enregistré** |
| 3 | `POST /festivals/1/publish` puis `PATCH /concerts/3/reschedule` vers le 25/06 | **200** : planning publié modifié, et même hors des dates du festival |

Trace réelle obtenue sur le code initial :

```
GET 2   -> start_time 2027-06-18T19:30:00
PATCH   -> 500 {'detail': 'Simulation : le service de notification est indisponible'}
GET 2   -> start_time 2027-06-18T18:30:00        <- modifié malgré le 500, et en chevauchement
publish -> published                             <- planning incohérent publié (R8)
PATCH published + hors festival -> 200 2027-06-25T21:00:00
```

### Preuve par les tests

Les tests de `tests/non_regression/test_defects.py` ont été écrits **avant** toute modification et exécutés
sur le code initial :

```
FAILED test_defect1_reschedule_onto_occupied_stage_is_refused            assert 200 == 409
FAILED test_defect1_artist_cannot_play_on_two_stages_at_the_same_time    assert 200 == 409
FAILED test_defect1_reschedule_outside_festival_period_is_refused        assert 200 == 400
FAILED test_defect2_reschedule_succeeds_even_if_notification_fails       assert 500 == 200
FAILED test_defect2_publish_succeeds_even_if_notification_fails          assert 500 == 200
FAILED test_defect3_ordinary_reschedule_is_refused_once_published        assert 200 == 409
FAILED test_defect3_published_planning_can_be_changed_through_explicit_procedure   assert 404 == 200
FAILED test_defect3_explicit_procedure_still_checks_conflicts            assert 404 == 409
FAILED test_defect3_new_concert_is_refused_once_published                assert 201 == 409
9 failed, 1 passed
```

Le seul test qui passait (`test_defect1_valid_reschedule_is_accepted`) vérifie qu'un déplacement valide est
accepté : il garantit que la correction ne bloque pas les cas légitimes. Après refactorisation : **10 passed**.
