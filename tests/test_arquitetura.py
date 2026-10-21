"""
As regras de camada do projeto, verificadas nos imports (via `ast`, sem importar nada).

    domain  → settings → infra → repositories → services → graph / api

Seta pra direita = "pode importar". `telemetry` é transversal. Cada regra abaixo é uma frase do
AGENTS.md; quando uma quebra, o teste aponta o arquivo e o import.
"""

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent / "app"


def _imports(arquivo: Path) -> list[tuple[int, str]]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    achados: list[tuple[int, str]] = []

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            achados += [(no.lineno, a.name) for a in no.names if a.name.startswith("app.")]
        elif isinstance(no, ast.ImportFrom) and no.module and no.module.startswith("app"):
            achados.append((no.lineno, no.module))
            # `from app import graph` também conta como importar `app.graph`
            if no.module == "app":
                achados += [(no.lineno, f"app.{a.name}") for a in no.names]

    return achados


def _arquivos(pacote: str) -> list[Path]:
    return sorted(p for p in (RAIZ / pacote).rglob("*.py") if "__pycache__" not in p.parts)


def _violacoes(pacote: str, proibidos: tuple[str, ...], excecoes: frozenset[str] = frozenset()) -> list[str]:
    ruins = []
    for arquivo in _arquivos(pacote):
        rel = arquivo.relative_to(RAIZ.parent).as_posix()
        if rel in excecoes:
            continue
        for linha, modulo in _imports(arquivo):
            if any(modulo == p or modulo.startswith(p + ".") for p in proibidos):
                ruins.append(f"{rel}:{linha} importa {modulo}")
    return ruins


def _sem_violacao(violacoes: list[str]) -> None:
    assert not violacoes, "Camada importando o que não deve:\n  " + "\n  ".join(violacoes)


def test_domain_so_importa_domain():
    """O domínio é neutro: tipos, erros e regras sem I/O, que qualquer camada pode usar."""

    _sem_violacao(_violacoes("domain", (
        "app.settings", "app.infra", "app.repositories", "app.services", "app.graph", "app.api",
        "app.schemas", "app.telemetry", "app.tui",
    )))


def test_infra_nao_importa_camadas_de_cima():
    # `telemetry` e `domain` são transversais; infra não conhece quem a usa.
    _sem_violacao(_violacoes("infra", (
        "app.repositories", "app.services", "app.graph", "app.api", "app.schemas", "app.tui",
    )))


def test_repositories_nao_importam_services_graph_nem_api():
    _sem_violacao(_violacoes("repositories", ("app.services", "app.graph", "app.api", "app.tui")))


def test_so_services_importam_repositories():
    """Repository + service andam juntos: ninguém fora de um service chama um repository direto."""

    for pacote in ("api", "graph", "tui", "infra", "schemas", "domain", "telemetry"):
        _sem_violacao(_violacoes(pacote, ("app.repositories",)))


def test_services_nao_importam_api():
    _sem_violacao(_violacoes("services", ("app.api", "app.tui")))


def test_tools_chamam_services_e_nunca_a_infra_de_dados():
    """A tool só valida argumentos e embrulha em `Response`: dado é com o service."""

    _sem_violacao(_violacoes(
        "graph/tools",
        ("app.infra.postgres", "app.infra.mongo", "app.infra.qdrant", "app.infra.redis"),
        # ingest.py é um script offline que indexa o PDF no Qdrant: não é tool do LLM
        excecoes=frozenset({"app/graph/tools/faq/ingest.py"}),
    ))


@pytest.mark.parametrize("pacote", ["api", "tui"])
def test_entrega_nao_toca_banco_nem_grafo_direto(pacote):
    """API, TUI, A2A e MCP chegam aos dados só por services (o MCP expõe as tools do grafo)."""

    _sem_violacao(_violacoes(
        pacote,
        ("app.infra.postgres", "app.infra.mongo", "app.infra.qdrant", "app.graph.builder", "app.graph.state"),
        # O lifespan é o único lugar da API que abre e fecha recursos de processo: compila o grafo no
        # boot e descarta o pool do Postgres no shutdown (ver o docstring dele).
        excecoes=frozenset({"app/api/lifespan.py"}),
    ))
