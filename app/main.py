from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="AI Service Management Platform",
    description="Учебная корпоративная система управления заявками и инцидентами",
    version="0.1.0",
)


class IncidentStatus(str, Enum):
    """Допустимые состояния заявки."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentPriority(str, Enum):
    """Допустимые приоритеты заявки."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentCreate(BaseModel):
    """Данные, которые пользователь передает при создании заявки."""

    title: str = Field(
        min_length=5,
        max_length=100,
        examples=["Не работает корпоративный VPN"],
    )
    description: str = Field(
        min_length=10,
        max_length=1000,
        examples=["После обновления Windows невозможно подключиться к VPN."],
    )
    requester_email: str = Field(
        min_length=5,
        max_length=254,
        examples=["employee@example.com"],
    )
    priority: IncidentPriority = IncidentPriority.MEDIUM


class IncidentStatusUpdate(BaseModel):
    """Данные для изменения статуса заявки."""

    status: IncidentStatus


class Incident(BaseModel):
    """Полная модель заявки, которую возвращает API."""

    id: UUID
    title: str
    description: str
    requester_email: str
    priority: IncidentPriority
    status: IncidentStatus


# Временное хранилище.
# После перезапуска программы данные исчезнут.
incidents: dict[UUID, Incident] = {}


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Проверка доступности приложения."""

    return {"status": "ok"}


@app.post(
    "/incidents",
    response_model=Incident,
    status_code=status.HTTP_201_CREATED,
    tags=["Incidents"],
)
def create_incident(payload: IncidentCreate) -> Incident:
    """Создает новую заявку."""

    incident = Incident(
        id=uuid4(),
        title=payload.title,
        description=payload.description,
        requester_email=payload.requester_email,
        priority=payload.priority,
        status=IncidentStatus.OPEN,
    )

    incidents[incident.id] = incident
    return incident


@app.get(
    "/incidents",
    response_model=list[Incident],
    tags=["Incidents"],
)
def get_incidents(
    incident_status: Annotated[
        IncidentStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[Incident]:
    """Возвращает все заявки или фильтрует их по статусу."""

    result = list(incidents.values())

    if incident_status is not None:
        result = [
            incident
            for incident in result
            if incident.status == incident_status
        ]

    return result


@app.get(
    "/incidents/{incident_id}",
    response_model=Incident,
    tags=["Incidents"],
)
def get_incident(incident_id: UUID) -> Incident:
    """Возвращает одну заявку по идентификатору."""

    incident = incidents.get(incident_id)

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return incident


@app.patch(
    "/incidents/{incident_id}/status",
    response_model=Incident,
    tags=["Incidents"],
)
def update_incident_status(
    incident_id: UUID,
    payload: IncidentStatusUpdate,
) -> Incident:
    """Изменяет статус заявки."""

    incident = incidents.get(incident_id)

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    updated_incident = incident.model_copy(
        update={"status": payload.status}
    )
    incidents[incident_id] = updated_incident

    return updated_incident


@app.delete(
    "/incidents/{incident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Incidents"],
)
def delete_incident(incident_id: UUID) -> None:
    """Удаляет заявку."""

    if incident_id not in incidents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    del incidents[incident_id]