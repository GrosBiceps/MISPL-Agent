"""Journal d'audit de sécurité — écriture des événements (cf. api.models.AuditEvent).

Règle absolue : aucun mot de passe, hachage, jeton ni contenu de conversation
n'est transmis à record_event. Le paramètre `detail` est tronqué et réservé à
une information courte non sensible (ex. liste des champs modifiés).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session as DBSession

from api.models import AuditEvent

logger = logging.getLogger("mispl.audit")

_DETAIL_MAX_LENGTH = 200

LOGIN_SUCCESS = "login_success"
LOGIN_FAILURE = "login_failure"
ACCOUNT_LOCKED = "account_locked"
LOGOUT = "logout"
PASSWORD_CHANGED = "password_changed"
PASSWORD_CHANGE_FAILED = "password_change_failed"
PASSWORD_REHASHED = "password_rehashed"
ADMIN_USER_CREATED = "admin_user_created"
ADMIN_USER_UPDATED = "admin_user_updated"
ADMIN_PASSWORD_RESET = "admin_password_reset"
ADMIN_SESSIONS_REVOKED = "admin_sessions_revoked"


def record_event(
    db: DBSession,
    event: str,
    *,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    source_ip: str | None = None,
    detail: str | None = None,
    commit: bool = True,
) -> None:
    """Ajoute un événement d'audit. Un échec d'écriture est journalisé mais ne
    fait jamais échouer la requête métier."""
    if detail is not None:
        detail = detail[:_DETAIL_MAX_LENGTH]
    try:
        db.add(AuditEvent(
            event=event,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            source_ip=source_ip,
            detail=detail,
        ))
        if commit:
            db.commit()
    except Exception:  # noqa: BLE001 — l'audit ne doit pas casser le service
        db.rollback()
        logger.exception("Écriture du journal d'audit impossible (événement %s)", event)
        return
    logger.info("audit event=%s actor=%s target=%s ip=%s", event, actor_user_id, target_user_id, source_ip)
