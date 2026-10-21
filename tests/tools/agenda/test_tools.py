from datetime import UTC, datetime
from uuid import UUID

from app.infra.context import session_context
from app.infra.postgres.models import Event

OUTRO_USUARIO = UUID("11111111-1111-1111-1111-111111111111")


async def test_add_event_grava_e_retorna_id(agenda, db_session):
    resultado = await agenda.add_event(
        title="Dentista", start_time="2026-02-01T10:00:00+00:00",
        source_text="marcar dentista", notes="",
    )

    assert resultado["status"] == "ok"
    assert db_session.get(Event, resultado["id"]).title == "Dentista"


async def test_query_daily_events_usa_fuso_sao_paulo_nao_utc(agenda, db_session):
    # 2026-01-14 22:00 em São Paulo (UTC-3) = 2026-01-15 01:00 UTC — mesmo bug de
    # timezone já corrigido no financeiro (ver TODO.md), aqui sobre Event.start_time.
    db_session.add(
        Event(
            title="Reunião tarde", start_time=datetime(2026, 1, 15, 1, 0, tzinfo=UTC),
            recorded_at=datetime.now(UTC), source_text="reuniao",
        )
    )
    db_session.commit()

    assert (await agenda.query_daily_events(date_local="2026-01-14"))["total_records"] == 1
    assert (await agenda.query_daily_events(date_local="2026-01-15"))["total_records"] == 0


async def test_query_events_com_intervalo_retorna_cronologico(agenda, db_session):
    await agenda.add_event(title="a", start_time="2026-01-01T12:00:00+00:00", source_text="a", notes="")
    await agenda.add_event(title="b", start_time="2026-01-02T12:00:00+00:00", source_text="b", notes="")

    resultado = await agenda.query_events(date_from_local="2026-01-01", date_to_local="2026-01-02")

    assert [e["title"] for e in resultado["events"]] == ["a", "b"]


async def test_query_events_filtra_por_titulo(agenda, db_session):
    await agenda.add_event(title="Consulta médica", start_time="2026-01-01T12:00:00+00:00", source_text="s", notes="")
    await agenda.add_event(title="Reunião", start_time="2026-01-01T12:00:00+00:00", source_text="s", notes="")

    resultado = await agenda.query_events(title="médica")

    assert resultado["total_records"] == 1
    assert resultado["events"][0]["title"] == "Consulta médica"


async def test_update_event_sem_campos_retorna_erro(agenda, db_session):
    assert (await agenda.update_event(id=1))["status"] == "error"


async def test_update_event_notes_vazia_e_aceita_como_valor_informado(agenda, db_session):
    # notes="" é "falsy" — a guarda de "nada pra atualizar" usava any() e recusava a
    # atualização mesmo o campo tendo sido informado (bug real, corrigido pra all(is None)).
    criado = await agenda.add_event(
        title="Original", start_time="2026-01-01T12:00:00+00:00", source_text="s", notes="algo",
    )

    resultado = await agenda.update_event(id=criado["id"], notes="")

    assert resultado["status"] == "ok"
    assert resultado["rows_affected"] == 1
    assert db_session.get(Event, criado["id"]).notes == ""


async def test_update_event_id_inexistente_retorna_rows_affected_zero(agenda, db_session):
    resultado = await agenda.update_event(id=999, title="novo")

    assert resultado == {"status": "ok", "rows_affected": 0, "id": 999, "updated": None}


async def test_update_event_de_outro_usuario_e_tratado_como_nao_encontrado(agenda, db_session):
    criado = await agenda.add_event(
        title="Original", start_time="2026-01-01T12:00:00+00:00", source_text="s", notes="",
    )

    with session_context(OUTRO_USUARIO):
        resultado = await agenda.update_event(id=criado["id"], title="Sequestrado")

    assert resultado["rows_affected"] == 0
    assert db_session.get(Event, criado["id"]).title == "Original"
