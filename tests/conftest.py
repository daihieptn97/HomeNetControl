import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.drop_all()
        db.create_all()
        from app import _bootstrap_defaults

        _bootstrap_defaults(application)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in(client):
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client
