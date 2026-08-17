"""Tests des modèles ORM users/sessions — DB en mémoire, sans FastAPI."""

import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import Base
from api.models import Conversation, Message, UsageDaily, User, UserSession


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestUserModel:
    def test_create_and_query_user(self):
        db = make_session()
        user = User(
            email="tech1@labo.fr",
            password_hash="hash-placeholder",
            display_name="Tech Un",
            platform_role="user",
            can_use_dsi_mode=False,
        )
        db.add(user)
        db.commit()

        fetched = db.query(User).filter(User.email == "tech1@labo.fr").one()
        assert fetched.display_name == "Tech Un"
        assert fetched.platform_role == "user"
        assert fetched.can_use_dsi_mode is False
        assert fetched.is_active is True  # défaut
        assert fetched.failed_login_count == 0  # défaut

    def test_email_unique_constraint(self):
        db = make_session()
        db.add(User(email="dup@labo.fr", password_hash="h", display_name="A", platform_role="user"))
        db.commit()
        db.add(User(email="dup@labo.fr", password_hash="h", display_name="B", platform_role="user"))
        import pytest
        with pytest.raises(Exception):
            db.commit()


class TestUserSessionModel:
    def test_create_session_linked_to_user(self):
        db = make_session()
        user = User(email="tech2@labo.fr", password_hash="h", display_name="Tech Deux", platform_role="user")
        db.add(user)
        db.commit()

        now = datetime.datetime.utcnow()
        session_row = UserSession(
            token="tok-abc123",
            user_id=user.id,
            created_at=now,
            expires_at=now + datetime.timedelta(hours=8),
        )
        db.add(session_row)
        db.commit()

        fetched = db.get(UserSession, "tok-abc123")
        assert fetched.user_id == user.id
        assert fetched.revoked_at is None
        assert fetched.user.email == "tech2@labo.fr"
        assert user.sessions[0].token == "tok-abc123"


class TestConversationModel:
    def test_create_conversation_linked_to_user(self):
        db = make_session()
        user = User(email="tech3@labo.fr", password_hash="h", display_name="Tech Trois", platform_role="user")
        db.add(user)
        db.commit()

        conv = Conversation(user_id=user.id, title="Comment utiliser Substr ?")
        db.add(conv)
        db.commit()

        fetched = db.query(Conversation).filter(Conversation.user_id == user.id).one()
        assert fetched.title == "Comment utiliser Substr ?"
        assert fetched.messages == []


class TestMessageModel:
    def test_create_messages_linked_to_conversation(self):
        db = make_session()
        user = User(email="tech4@labo.fr", password_hash="h", display_name="Tech Quatre", platform_role="user")
        db.add(user)
        db.commit()

        conv = Conversation(user_id=user.id, title="Formater une date")
        db.add(conv)
        db.commit()

        db.add(Message(conversation_id=conv.id, role="user", content="Comment formater la date ?"))
        db.add(
            Message(
                conversation_id=conv.id,
                role="assistant",
                content="Utilisez FormatDate()",
                sources_json='[{"function_name": "FormatDate"}]',
            )
        )
        db.commit()

        fetched = db.get(Conversation, conv.id)
        assert len(fetched.messages) == 2
        assert fetched.messages[0].role == "user"
        assert fetched.messages[1].sources_json == '[{"function_name": "FormatDate"}]'

    def test_deleting_conversation_cascades_to_messages(self):
        db = make_session()
        user = User(email="tech5@labo.fr", password_hash="h", display_name="Tech Cinq", platform_role="user")
        db.add(user)
        db.commit()

        conv = Conversation(user_id=user.id, title="Test cascade")
        db.add(conv)
        db.commit()
        db.add(Message(conversation_id=conv.id, role="user", content="Question"))
        db.commit()
        conv_id = conv.id

        db.delete(conv)
        db.commit()

        assert db.query(Message).filter(Message.conversation_id == conv_id).count() == 0


class TestUsageDailyModel:
    def test_create_and_query_usage_row(self):
        db = make_session()
        user = User(email="tech6@labo.fr", password_hash="h", display_name="Tech Six", platform_role="user")
        db.add(user)
        db.commit()

        today = datetime.date.today()
        db.add(
            UsageDaily(
                user_id=user.id, date=today,
                prompt_tokens=100, completion_tokens=50, request_count=1,
            )
        )
        db.commit()

        fetched = db.query(UsageDaily).filter(UsageDaily.user_id == user.id).one()
        assert fetched.date == today
        assert fetched.prompt_tokens == 100
        assert fetched.completion_tokens == 50
        assert fetched.request_count == 1

    def test_unique_constraint_on_user_and_date(self):
        db = make_session()
        user = User(email="tech7@labo.fr", password_hash="h", display_name="Tech Sept", platform_role="user")
        db.add(user)
        db.commit()

        today = datetime.date.today()
        db.add(UsageDaily(user_id=user.id, date=today, prompt_tokens=10, completion_tokens=5, request_count=1))
        db.commit()

        db.add(UsageDaily(user_id=user.id, date=today, prompt_tokens=20, completion_tokens=10, request_count=1))
        import pytest
        with pytest.raises(Exception):
            db.commit()
