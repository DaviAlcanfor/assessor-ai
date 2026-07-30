# TODO

Próximos passos planejados. Contexto do projeto em [AGENTS.md](AGENTS.md).

## Redis

`redis` já está em `pyproject.toml` mas nenhuma tool usa ainda.

- [ ] `tools/redis/connection.py` — client lazy (init só no primeiro uso, seguindo o padrão de
      `tools/postgres/connection.py` e `tools/mongo/connection.py`)
- [ ] Cache de sessão: mover/duplicar o histórico curto de mensagens (hoje via `$slice: -5` no
      Mongo) para Redis, com TTL, reduzindo round-trip ao Mongo em cada turno
- [ ] Cache de `perfil_usuario` (hoje lido do Mongo a cada invocação em `main.py:executar_fluxo_assessor`)
- [ ] Rate limit / cooldown do guardrail de entrada por `user_id`
- [ ] Variável de ambiente `REDIS_URI` em `.env.example` e `config/settings.py`

## Qdrant

Hoje o RAG do FAQ usa FAISS local (`tools/faq_tools.py`). Avaliar migração para Qdrant quando
precisar de mais de um documento/coleção ou busca persistente fora de memória.

- [ ] `tools/qdrant/connection.py` — client lazy
- [ ] `tools/qdrant/faq/core.py` — reimplementar `faq_retriever` sobre Qdrant (collection por domínio,
      ex. `faq`, e futuramente `financeiro`/`agenda` para busca semântica sobre histórico)
- [ ] Script de ingestão dos PDFs de `data/documents/` para a collection do Qdrant
- [ ] Decidir: Qdrant local (Docker, mesmo padrão do `config/docker.py`) vs. Qdrant Cloud
- [ ] Variáveis `QDRANT_URL` / `QDRANT_API_KEY`

## API

Hoje só existe o loop de terminal em `main.py`. Expor o fluxo (`fluxo_agentes` em `graph/builder.py`)
via API para permitir outros clientes (TUI, frontend, integrações).

- [ ] Escolher framework (FastAPI é o caminho natural dado o resto do stack Python async)
- [ ] `api/main.py` com endpoint `POST /chat` (equivalente a `executar_fluxo_assessor` em `main.py`)
      recebendo `session_id`/`user_id`/mensagem e retornando a resposta
- [ ] Endpoint de streaming (SSE ou WS) para respostas incrementais do LangGraph
- [ ] Autenticação básica por usuário (hoje `user_id`/`email` são mockados em `main.py`)
- [ ] Extrair a lógica de `montar_mensagem_humana`/`salvar_mensagens`/`_extrair_resposta` de
      `main.py` para um módulo compartilhado entre API e CLI (ex. `core/assessor.py`)
- [ ] Dockerfile + healthcheck

## TUI com Textual

Substituir/complementar a interface atual (`ui/terminal.py`, Rich + pyfiglet) por uma TUI de
verdade com [Textual](https://github.com/Textualize/textual).

- [ ] Adicionar `textual` às dependências (`uv add textual`)
- [ ] `ui/tui/app.py` — App Textual com tela de chat (input fixo embaixo, histórico rolável)
- [ ] Widget de histórico com bolhas usuário/assistente reaproveitando a lógica de
      `exibir_usuario`/`exibir_assistente` de `ui/terminal.py`
- [ ] Indicador de "pensando..." enquanto o grafo LangGraph processa (rodar `fluxo_agentes.invoke`
      em thread/worker do Textual para não travar a UI)
- [ ] Tela/painel lateral opcional mostrando qual agente está ativo (`agentes_chamados` do estado)
- [ ] Comando `/exit` e `Ctrl+C` chamando `chats.encerrar_sessao` como hoje em `main.py`
- [ ] Decidir se a TUI fala direto com `graph/builder.py` (como o `main.py` atual) ou consome a API
      nova — preferir a API se ela sair primeiro, para manter um único client
