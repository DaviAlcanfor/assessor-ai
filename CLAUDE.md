# CLAUDE.md

Contexto completo do projeto, arquitetura, convenções e stack está em [AGENTS.md](AGENTS.md) —
leia-o primeiro. Este arquivo só existe para instruções específicas do Claude Code; não duplique
conteúdo do AGENTS.md aqui.

## Instruções específicas para o Claude Code

- Este é um projeto pessoal em estágio inicial/experimental — prefira mudanças diretas e simples,
  sem abstrações especulativas.
- Respeite o idioma do arquivo (português para código de domínio, inglês para infraestrutura) —
  ver seção "Convenções" do AGENTS.md.
- Antes de adicionar uma tool nova (Redis, Qdrant, API, etc.), siga o padrão descrito em
  "Ao adicionar uma tool nova" no AGENTS.md e confira o [TODO.md](TODO.md) para o que já está
  planejado.
- Postgres, Mongo, Redis e Qdrant são serviços em nuvem — não há infra local via Docker. Não
  proponha subir container nem `docker compose` sem falar com o usuário antes.
- Antes de dizer que terminou: `just check` e `just test`. Não deletar arquivo nem rodar comando
  destrutivo (`git reset --hard`, `rm -rf`, force push) sem permissão explícita — ver "Regras de
  operação para agentes" no AGENTS.md.
- Antes de escrever código que use pydantic, FastAPI, LangChain/LangGraph, SQLAlchemy, Mongo ou Redis,
  confira `.agents/skills/<lib>.md` — são pegadinhas reais já encontradas neste repo (ver seção
  "Skills por biblioteca" do AGENTS.md).
