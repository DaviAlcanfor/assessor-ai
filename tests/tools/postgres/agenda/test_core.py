from datetime import UTC, datetime
from uuid import UUID

from assessor_ai.tools.postgres.agenda.core import (
    add_event,
    query_daily_events,
    query_events,
    update_event,
)
from assessor_ai.tools.postgres.connection import reset_current_user, set_current_user
from assessor_ai.tools.postgres.models import Event

OUTRO_USUARIO = UUID("11111111-1111-1111-1111-111111111111")


def test_add_event_grava_e_retorna_id(db_session):
    resultado = add_event.func(
        title="Dentista", start_time="2026-02-01T10:00:00+00:00",
        source_text="marcar dentista", notes="",
    )

    assert resultado["status"] == "ok"
    assert db_session.get(Event, resultado["id"]).title == "Dentista"


def test_query_daily_events_usa_fuso_sao_paulo_nao_utc(db_session):
    # 2026-01-14 22:00 em São Paulo (UTC-3) = 2026-01-15 01:00 UTC — mesmo bug de
    # timezone já corrigido no financeiro (ver TODO.md), aqui sobre Event.start_time.
    db_session.add(
        Event(
            title="Reunião tarde", start_time=datetime(2026, 1, 15, 1, 0, tzinfo=UTC),
            recorded_at=datetime.now(UTC), source_text="reuniao",
        )
    )
    db_session.commit()

    assert query_daily_events.func(date_local="2026-01-14")["total_records"] == 1
    assert query_daily_events.func(date_local="2026-01-15")["total_records"] == 0


def test_query_events_com_intervalo_retorna_cronologico(db_session):
    add_event.func(title="a", start_time="2026-01-01T12:00:00+00:00", source_text="a", notes="")
    add_event.func(title="b", start_time="2026-01-02T12:00:00+00:00", source_text="b", notes="")

    resultado = query_events.func(date_from_local="2026-01-01", date_to_local="2026-01-02")

    assert [e["title"] for e in resultado["events"]] == ["a", "b"]


def test_query_events_filtra_por_titulo(db_session):
    add_event.func(title="Consulta médica", start_time="2026-01-01T12:00:00+00:00", source_text="s", notes="")
    add_event.func(title="Reunião", start_time="2026-01-01T12:00:00+00:00", source_text="s", notes="")

    resultado = query_events.func(title="médica")

    assert resultado["total_records"] == 1
    assert resultado["events"][0]["title"] == "Consulta médica"


def test_update_event_sem_campos_retorna_erro(db_session):
    assert update_event.func(id=1)["status"] == "error"


def test_update_event_id_inexistente_retorna_rows_affected_zero(db_session):
    resultado = update_event.func(id=999, title="novo")

    assert resultado == {"status": "ok", "rows_affected": 0, "id": 999, "updated": None}


def test_update_event_de_outro_usuario_e_tratado_como_nao_encontrado(db_session):
    criado = add_event.func(
        title="Original", start_time="2026-01-01T12:00:00+00:00", source_text="s", notes="",
    )

    token = set_current_user(OUTRO_USUARIO)
    try:
        resultado = update_event.func(id=criado["id"], title="Sequestrado")
    finally:
        reset_current_user(token)

    assert resultado["rows_affected"] == 0
    assert db_session.get(Event, criado["id"]).title == "Original"
