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
- Não rodar `docker stop`/`docker start` fora do fluxo de `config/docker.py` sem avisar o usuário —
  o container Postgres é compartilhado com outras execuções locais.
- Antes de escrever código que use pydantic, FastAPI, LangChain/LangGraph, SQLAlchemy ou Redis,
  confira `.agents/skills/<lib>.md` — são pegadinhas reais já encontradas neste repo (ver seção
  "Skills por biblioteca" do AGENTS.md).
