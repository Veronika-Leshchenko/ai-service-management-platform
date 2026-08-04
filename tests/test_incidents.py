from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app, incidents


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_incidents() -> None:
    """
    Очищает временное хранилище перед каждым тестом.

    Благодаря этому тесты не зависят друг от друга.
    """

    incidents.clear()


def valid_incident_payload() -> dict[str, str]:
    """Возвращает корректные данные для создания заявки."""

    return {
        "title": "Не работает корпоративный VPN",
        "description": (
            "После обновления Windows невозможно подключиться к VPN."
        ),
        "requester_email": "employee@example.com",
        "priority": "high",
    }


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_incident_returns_201() -> None:
    response = client.post(
        "/incidents",
        json=valid_incident_payload(),
    )

    response_body = response.json()

    assert response.status_code == 201
    assert response_body["id"] is not None
    assert response_body["title"] == "Не работает корпоративный VPN"
    assert response_body["priority"] == "high"
    assert response_body["status"] == "open"


def test_created_incident_can_be_received_by_id() -> None:
    create_response = client.post(
        "/incidents",
        json=valid_incident_payload(),
    )
    incident_id = create_response.json()["id"]

    get_response = client.get(f"/incidents/{incident_id}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == incident_id
    assert get_response.json()["title"] == "Не работает корпоративный VPN"


def test_get_incident_returns_404_for_unknown_id() -> None:
    unknown_id = uuid4()

    response = client.get(f"/incidents/{unknown_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Incident not found"}


def test_create_incident_rejects_short_title() -> None:
    payload = valid_incident_payload()
    payload["title"] = "VPN"

    response = client.post("/incidents", json=payload)

    assert response.status_code == 422


def test_create_incident_rejects_unknown_priority() -> None:
    payload = valid_incident_payload()
    payload["priority"] = "urgent"

    response = client.post("/incidents", json=payload)

    assert response.status_code == 422


def test_get_incidents_returns_created_incidents() -> None:
    client.post("/incidents", json=valid_incident_payload())

    second_payload = valid_incident_payload()
    second_payload["title"] = "Не открывается корпоративная почта"
    second_payload["priority"] = "medium"

    client.post("/incidents", json=second_payload)

    response = client.get("/incidents")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_incidents_can_be_filtered_by_status() -> None:
    create_response = client.post(
        "/incidents",
        json=valid_incident_payload(),
    )
    incident_id = create_response.json()["id"]

    client.patch(
        f"/incidents/{incident_id}/status",
        json={"status": "resolved"},
    )

    response = client.get(
        "/incidents",
        params={"status": "resolved"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "resolved"


def test_incident_status_can_be_updated() -> None:
    create_response = client.post(
        "/incidents",
        json=valid_incident_payload(),
    )
    incident_id = create_response.json()["id"]

    update_response = client.patch(
        f"/incidents/{incident_id}/status",
        json={"status": "in_progress"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"


def test_incident_can_be_deleted() -> None:
    create_response = client.post(
        "/incidents",
        json=valid_incident_payload(),
    )
    incident_id = create_response.json()["id"]

    delete_response = client.delete(f"/incidents/{incident_id}")
    get_response = client.get(f"/incidents/{incident_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404