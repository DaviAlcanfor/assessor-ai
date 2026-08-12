# SQLAlchemy

## Coluna com `server_default`/`DEFAULT` do Postgres precisa também de `default=` no model

O ORM sempre manda toda coluna mapeada no `INSERT`, inclusive `NULL` explícito pra atributo não
setado no objeto Python. Isso pisa no `DEFAULT` do banco — que só dispara quando a coluna é
*omitida* do `INSERT`, não quando ela chega como `NULL`. SQL cru (que só manda as colunas que você
escreve) não tem esse problema; o ORM tem. Se a coluna tem um `DEFAULT` no banco, replique o mesmo
valor como `default=` no `mapped_column`, senão todo insert via ORM sem esse campo grava `NULL` em
vez de cair no default (bug real já corrigido em `models.py`).

Do this:

```python
from sqlalchemy.orm import Mapped, mapped_column

LEGACY_USER_ID = "00000000-0000-0000-0000-000000000001"


class Transaction(Base):
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), default=LEGACY_USER_ID)
```

Instead of:

```python
# DO NOT DO THIS
class Transaction(Base):
    # banco tem DEFAULT '00000000-...'::uuid, mas o ORM manda user_id=NULL explícito
    # em todo insert que não setar o atributo, e o DEFAULT do banco nunca dispara
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
```

## Filtrar por data local em coluna `timestamptz` exige conversão de timezone explícita

`func.date(coluna)` sobre uma coluna `timestamptz` converte pro timezone da *sessão* do Postgres
(normalmente UTC), não pro timezone que o domínio espera. Um registro às 22h em São Paulo é 01h UTC
do dia seguinte — filtrar/agrupar por `func.date()` cru coloca esse registro no dia errado (bug
real em produção, `financeiro/core.py`, corrigido reusando os helpers abaixo).

Do this, converter explicitamente antes de extrair a data:

```python
from sqlalchemy import func


def local_date(column):
    """(column AT TIME ZONE 'America/Sao_Paulo')::date"""
    return func.date(func.timezone("America/Sao_Paulo", column))


query.where(local_date(Transaction.occurred_at) == "2026-08-12")
```

Instead of:

```python
# DO NOT DO THIS
query.where(func.date(Transaction.occurred_at) == "2026-08-12")  # usa o timezone da sessão (UTC)
```
