from sqlalchemy import column

from app.infra.postgres import (
    local_date,
    local_date_filter,
    local_date_range_filter,
)


def test_local_date_aplica_timezone_sao_paulo():
    expressao = local_date(column("occurred_at"))

    assert str(expressao) == "date(timezone(:timezone_1, occurred_at))"


def test_local_date_filter_compara_com_data_local():
    expressao = local_date_filter(column("occurred_at"), "2026-01-01")
    sql = str(expressao.compile(compile_kwargs={"literal_binds": True}))

    assert sql == "date(timezone('America/Sao_Paulo', occurred_at)) = '2026-01-01'"


def test_local_date_range_filter_usa_between():
    expressao = local_date_range_filter(
        column("occurred_at"), "2026-01-01", "2026-01-31"
    )
    sql = str(expressao.compile(compile_kwargs={"literal_binds": True}))

    assert sql == (
        "date(timezone('America/Sao_Paulo', occurred_at)) "
        "BETWEEN '2026-01-01' AND '2026-01-31'"
    )
