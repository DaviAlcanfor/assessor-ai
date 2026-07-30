# TODO

Próximos passos planejados. Contexto do projeto em [AGENTS.md](AGENTS.md).

## Refatoração: camada de serviço compartilhada

Hoje `main.py` mistura três coisas: o loop de terminal, a lógica de montar/persistir mensagens
(`montar_mensagem_humana`, `salvar_mensagens`, `_extrair_resposta`) e a invocação do grafo
(`fluxo_agentes.invoke`). Isso trava a criação de TUI e API, porque as duas precisariam duplicar
essa lógica. Extrair tudo que não é "loop de terminal" para um módulo compartilhado, usado igualmente
por CLI, TUI e API. `main.py` vira só um dispatcher (`python main.py terminal|tui|api`).

**Nome do módulo:** o exemplo usou `agent_flow/` como provisório. Sugestão: chamar de **`chat/`**
em vez disso — evita colisão de vocabulário com `graph/` (que já é o "flow" do LangGraph) e
`agents/` (que já é "agent"), e casa com o nome que a collection do Mongo já usa
(`tools/mongo/chats`). Mas qualquer nome único e sem overlap com os módulos existentes resolve;
decidir na hora de implementar.

Estrutura proposta (usando `chat/` como nome de exemplo):

```text
chat/
├── service.py        # send_message(), create_chat(), get_history() — a API pública do módulo
├── models.py          # modelos internos (request/response), independentes dos schemas do Mongo/tool
├── repositories.py    # acesso a chats/mensagens (hoje espalhado em tools/mongo/chats e tools/mongo/users)
└── runner.py           # chama fluxo_agentes.invoke (graph/builder.py) e extrai a resposta

interfaces/
├── terminal.py         # TerminalService — loop de input() atual do main.py, usando chat.service
├── tui/
│   └── app.py           # AssessorTUI (Textual), usando chat.service — ver seção "TUI com Textual"
└── api/
    └── app.py            # FastAPI app + rotas HTTP, usando chat.service — ver seção "API"
```

- [ ] Definir o nome final do módulo de serviço (`chat/`, `agent_flow/` ou outro) e criar a pasta
- [ ] `chat/models.py` — modelos de entrada/saída do serviço, sem depender de detalhes do LangGraph
      ou do schema do Mongo diretamente
- [ ] `chat/repositories.py` — mover para cá o acesso a `tools/mongo/chats` e `tools/mongo/users`
      hoje chamado direto em `main.py` (`chats.buscar`, `chats.criar`, `chats.atualizar_mensagens`,
      `users.buscar`, `chats.encerrar_sessao`)
- [ ] `chat/runner.py` — mover `estado_inicial` + `fluxo_agentes.invoke` + `_extrair_resposta` de
      `main.py` para cá
- [ ] `chat/service.py` com `send_message(user_id, chat_id, content)`, `create_chat(user_id)`,
      `get_history(chat_id)` — orquestra runner + repositories, é o único ponto de entrada usado
      pelas três interfaces
- [ ] `interfaces/terminal.py` — extrair o `while True` de `main.py` para uma `TerminalService`/função
      que só faz I/O de terminal (Rich) e chama `chat.service`
- [ ] `interfaces/tui/app.py` — ver checklist da seção "TUI com Textual" abaixo, agora consumindo
      `chat.service` em vez de chamar `graph/builder.py` direto
- [ ] `interfaces/api/app.py` — ver checklist da seção "API" abaixo, agora consumindo `chat.service`
- [ ] Reescrever `main.py` como dispatcher puro (`terminal`/`tui`/`api` por argv), sem lógica de negócio
- [ ] Atualizar `ui/terminal.py` (funções de exibição Rich) para ser usado só por `interfaces/terminal.py`
      e `interfaces/tui/app.py`, não por lógica de fluxo

Fluxo da API depois da refatoração:

```text
HTTP request
  -> autenticação
  -> identifica user_id pelo token
  -> valida ownership do chat
  -> chat.service.send_message(...)
       -> carrega histórico (chat.repositories)
       -> executa o agente (chat.runner)
       -> persiste mensagem do usuário e resposta (chat.repositories)
  -> retorna resposta
```

## Alembic para PostgreSQL

Hoje não existe tabela de usuário no Postgres — `user_id` é só uma string gerada em `main.py`
(`uuid4()`, mockado) e o cadastro "de verdade" mora inteiro no Mongo (`tools/mongo/users`).
Sem uma tabela de usuário no Postgres, transações e eventos (`tools/postgres/financeiro`,
`tools/postgres/agenda`) não têm de fato uma FK confiável para `user_id`.

- [ ] Adicionar `alembic` às dependências (`uv add alembic`) e rodar `alembic init`
- [ ] Tabela `users` no Postgres **enxuta** — só o necessário para ligar com o domínio financeiro/agenda
      (ex. `id`, `mongo_user_id` ou algum identificador comum, `created_at`); dados "valiosos" de
      perfil/comportamento continuam só no Mongo (`profile`, histórico, etc.)
- [ ] Decidir o identificador comum entre Postgres e Mongo (reusar o mesmo UUID nos dois em vez de
      IDs desacoplados) e garantir que `users.garantir_usuario` (Mongo) e a nova tabela Postgres
      sejam criados juntos
- [ ] Migration inicial cobrindo o schema atual (transações, eventos, categorias) já existente no
      Postgres, hoje presumivelmente criado fora de migration — trazer para dentro do Alembic
- [ ] FK de `transactions`/`events` para `users.id`
- [ ] Documentar o comando de migration no README (`alembic upgrade head`)

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

Hoje só existe o loop de terminal em `main.py`. Expor o fluxo via API para permitir outros clientes
(TUI, frontend, integrações). Depende da refatoração acima — a API é só mais uma interface sobre
`chat.service`, não deve chamar `graph/builder.py` direto.

- [ ] Escolher framework (FastAPI é o caminho natural dado o resto do stack Python async)
- [ ] `interfaces/api/app.py` com endpoint `POST /chats/{chat_id}/messages` chamando
      `chat.service.send_message(...)` e retornando a resposta
- [ ] Endpoint de streaming (SSE ou WS) para respostas incrementais do LangGraph
- [ ] Autenticação por token, identificando `user_id` a partir dele (hoje é mockado em `main.py`) e
      validando ownership do chat antes de chamar o service
- [ ] Dockerfile + healthcheck

## TUI com Textual

Substituir/complementar a interface atual (`ui/terminal.py`, Rich + pyfiglet) por uma TUI de
verdade com [Textual](https://github.com/Textualize/textual).

- [ ] Adicionar `textual` às dependências (`uv add textual`)
- [ ] `interfaces/tui/app.py` — `AssessorTUI`, App Textual com tela de chat (input fixo embaixo,
      histórico rolável), chamando `chat.service.send_message(...)` — nunca `graph/builder.py` direto
- [ ] Widget de histórico com bolhas usuário/assistente reaproveitando a lógica de
      `exibir_usuario`/`exibir_assistente` de `ui/terminal.py`
- [ ] Indicador de "pensando..." enquanto o agente processa (rodar `chat.service.send_message` em
      thread/worker do Textual para não travar a UI)
- [ ] Tela/painel lateral opcional mostrando qual agente está ativo (`agentes_chamados` do estado)
- [ ] Comando `/exit` e `Ctrl+C` encerrando a sessão via `chat.service`
