"""Tests des routes /conversations — isolation par compte, CRUD historique de chat."""

from api.models import Conversation, Message, User
from api.security import hash_password


def make_user(db_session_factory, **overrides):
    defaults = dict(
        email="tech@labo.fr", password_hash=hash_password("MotDePasseRobuste1!"),
        display_name="Tech", platform_role="user", can_use_dsi_mode=False, is_active=True,
    )
    defaults.update(overrides)
    db = db_session_factory()
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.close()


def login(client, email="tech@labo.fr", password="MotDePasseRobuste1!"):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


def make_conversation(db_session_factory, user_email, title="Titre test"):
    db = db_session_factory()
    user = db.query(User).filter(User.email == user_email).one()
    conv = Conversation(user_id=user.id, title=title)
    db.add(conv)
    db.commit()
    conv_id = conv.id
    db.close()
    return conv_id


class TestAuthRequired:
    def test_list_unauthenticated_returns_401(self, client, db_session_factory):
        resp = client.get("/conversations")
        assert resp.status_code == 401

    def test_get_unauthenticated_returns_401(self, client, db_session_factory):
        resp = client.get("/conversations/1")
        assert resp.status_code == 401

    def test_delete_unauthenticated_returns_401(self, client, db_session_factory):
        resp = client.delete("/conversations/1")
        assert resp.status_code == 401


class TestListConversations:
    def test_empty_list_for_new_user(self, client, db_session_factory):
        make_user(db_session_factory)
        login(client)
        resp = client.get("/conversations")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_only_returns_own_conversations(self, client, db_session_factory):
        make_user(db_session_factory, email="a@labo.fr")
        make_user(db_session_factory, email="b@labo.fr")
        make_conversation(db_session_factory, "a@labo.fr", title="Conversation de A")
        make_conversation(db_session_factory, "b@labo.fr", title="Conversation de B")

        login(client, email="a@labo.fr")
        resp = client.get("/conversations")
        assert resp.status_code == 200
        titles = [c["title"] for c in resp.json()]
        assert titles == ["Conversation de A"]


class TestGetConversation:
    def test_returns_messages_in_order(self, client, db_session_factory):
        make_user(db_session_factory)
        conv_id = make_conversation(db_session_factory, "tech@labo.fr", title="Ma conversation")

        db = db_session_factory()
        db.add(Message(conversation_id=conv_id, role="user", content="Question ?"))
        db.add(
            Message(
                conversation_id=conv_id,
                role="assistant",
                content="Réponse.",
                sources_json='[{"function_name": "Substr", "source": "doc.md", "score": 0.9, "exact_match": true}]',
            )
        )
        db.commit()

        login(client)
        resp = client.get(f"/conversations/{conv_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Ma conversation"
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][1]["sources"][0]["function_name"] == "Substr"

    def test_returns_404_for_other_users_conversation(self, client, db_session_factory):
        make_user(db_session_factory, email="a@labo.fr")
        make_user(db_session_factory, email="b@labo.fr")
        conv_id = make_conversation(db_session_factory, "a@labo.fr")

        login(client, email="b@labo.fr")
        resp = client.get(f"/conversations/{conv_id}")
        assert resp.status_code == 404

    def test_returns_404_for_nonexistent_conversation(self, client, db_session_factory):
        make_user(db_session_factory)
        login(client)
        resp = client.get("/conversations/999")
        assert resp.status_code == 404


class TestDeleteConversation:
    def test_deletes_own_conversation_and_messages(self, client, db_session_factory):
        make_user(db_session_factory)
        conv_id = make_conversation(db_session_factory, "tech@labo.fr")

        db = db_session_factory()
        db.add(Message(conversation_id=conv_id, role="user", content="Question ?"))
        db.commit()

        login(client)
        resp = client.delete(f"/conversations/{conv_id}")
        assert resp.status_code == 200

        db = db_session_factory()
        assert db.get(Conversation, conv_id) is None
        assert db.query(Message).filter(Message.conversation_id == conv_id).count() == 0

    def test_returns_404_for_other_users_conversation(self, client, db_session_factory):
        make_user(db_session_factory, email="a@labo.fr")
        make_user(db_session_factory, email="b@labo.fr")
        conv_id = make_conversation(db_session_factory, "a@labo.fr")

        login(client, email="b@labo.fr")
        resp = client.delete(f"/conversations/{conv_id}")
        assert resp.status_code == 404

        db = db_session_factory()
        assert db.get(Conversation, conv_id) is not None
