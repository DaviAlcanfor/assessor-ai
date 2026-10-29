# Decisão técnica: o juiz e a escrita no banco

## Resumo

**Problema.** Hoje a tool que escreve dá `commit()` antes de o juiz opinar. Se o juiz recusa a frase, o chat mostra uma resposta segura, mas a linha em `transactions` ou em `events` continua no banco.

**Regra que a solução garante.** Se o turno for recusado, nenhuma escrita desse turno permanece, seja criação ou alteração, no financeiro ou na agenda.

**Decisão.** Família *Transacionar*. As tools deixam de confirmar a escrita. Todas as escritas do turno entram numa única transação do Postgres, aberta pelo runner antes do grafo. O runner só faz `commit` no fim do grafo, e só se o juiz aprovou. Recusa, juiz sem resposta, erro em qualquer nó ou queda do processo desfazem tudo. O padrão é desfazer.

**Cobertura.** Uma única mudança em `PostgresConn.session()` cobre `add_transaction`, `update_transaction`, `add_event` e também `update_event` (existe no projeto, o enunciado não a lista). Nenhuma tool, service, repository, rota ou API foi alterada.

**Prova.** Postgres real, LLMs reais e JeV real, sem forçar veredito. O juiz real aprovou os pedidos normais (a escrita ficou, uma vez) e recusou pedidos que as tools não conseguem gravar de fato (nada ficou), nas quatro tools. Tabela na seção 4.

**Custo da escolha.** A conexão do banco fica presa até o fim do turno (medido: de 10,9 s a 37,7 s). O juiz em si acrescenta de 0,31 s a 0,47 s por turno e cerca de 850 tokens de entrada. Seção 3.

**Limites.** O corte do juiz (0,5) não foi calibrado, a amostra real é de 18 turnos e o juiz confere a frase contra os dados gravados, não o que a tool consegue fazer. Seção 4, no fim.

### Onde achar cada item do enunciado

| Item pedido | Seção |
|---|---|
| 1. A decisão tomada, e por quê (fronteira, fluxo antes e depois, garantia nas três tools) | 1 |
| 2. As decisões que o grupo não tomou, e por quê | 2 |
| 3. O efeito nas métricas do SRE, e como | 3 |
| 4. As outras decisões: `add_google_event`, `salvar_mensagem`, juiz sem resposta, queda do processo, repetição do pedido, evidência com marcador único | 4 |
| 5. Arquivos criados e arquivos modificados | 5 |

---

## 1. A decisão tomada, e por quê

### A fronteira

A escrita só permanece se o juiz aprovar o turno. Em vez de cada tool confirmar o que gravou, o runner (`services/runner.py`) abre uma transação do turno antes de rodar o grafo e a fecha depois dele:

- juiz aprovou e o grafo terminou sem erro: `commit`;
- qualquer outro caso: `rollback`.

A transação chega às tools por um `ContextVar`, o mesmo mecanismo que o projeto já usa para saber o usuário do turno (`session_context`). Ela fica em `app/infra/postgres/transacao_do_turno.py`.

### Por que Transacionar e não as outras famílias

A regra exige que o dado recusado nunca fique visível nem permanente. Só a transação garante isso sem exceção: enquanto o veredito não chega, a linha nem existe para outras consultas, e se o processo cair ela some sozinha. Interceptar julgaria a ação em vez da frase. Adiar e Compensar deixam uma linha no banco durante o turno. O custo que aceitei foi a conexão presa até o fim do turno (seção 3).

### Por que cabe neste grafo

Todo acesso ao Postgres passa por `PostgresConn.session()`, usado pelo `@transacional` de todos os repositories. Alterando só ele, as quatro escritas ficam cobertas, sem mexer em tool, service ou repository. Cada operação roda dentro de um `SAVEPOINT`, para a falha de uma tool não desfazer as escritas que as outras já fizeram, e um `Lock` serializa tool calls paralelas (a sessão do SQLAlchemy não aceita uso concorrente).

### O fluxo, antes e depois

Antes:

```
modelo → tool grava e dá commit → orquestrador → guardrail de saída → chat
```

Depois:

```
modelo → tool grava (sem commit) → orquestrador → JUIZ → guardrail de saída → runner: commit se aprovado, senão rollback
```

### O que o juiz avalia

Uma chamada ao JeV com três perguntas sobre a frase que iria ao usuário:

1. **Grounding:** tudo o que a frase afirma aparece na fala do usuário ou no que as tools receberam e devolveram?
2. **Relevância:** a frase atende ao pedido por inteiro?
3. **Fidelidade:** o que foi gravado (valor, moeda, data, título) bate com o que o usuário pediu?

A terceira cobre o caso dos "2 dólares", em que a frase está coerente e o dado gravado, errado. Por isso o juiz recebe também os **argumentos** de cada tool, não só o retorno (o retorno do `add_transaction` não repete o valor gravado). Aprova se as três passam. Recusado, o juiz troca a frase por uma fixa e segura.

### A garantia, em cada tool que grava

| Desfecho do turno | O usuário vê | O banco guarda |
|---|---|---|
| Aprovado | a frase do orquestrador | a escrita, uma vez |
| Recusado | a frase segura | igual a antes do turno |
| Juiz sem resposta, com escrita no turno | a frase segura | igual a antes do turno |
| Erro em algum nó | o erro, como já era | igual a antes do turno |

Vale para `add_transaction`, `update_transaction`, `add_event` e `update_event`.

### Como cheguei nisso

Comecei com um rascunho solto, antes de olhar o código, e viajei bastante nele. Depois fui debatendo com uma IA, passando pelo código do projeto e pelo juiz do Frigus, até chegar nesta solução. A ideia central do rascunho era viável: é o Transacionar, com um objeto de aprovação que confirma ou desfaz. O resto não era:

- **Thread paralela e `yield`:** o fluxo já é sequencial e a sessão do SQLAlchemy não aceita uso por duas threads ao mesmo tempo. Bastou deixar a transação aberta durante o turno.
- **`@retry` até aprovar:** cada volta custa uma chamada de LLM e uma de JeV, dentro do SLO de 8 s, e só conserta a frase, não uma escrita errada. Recusado, o turno agora desfaz e devolve uma frase segura.
- **`wireup`:** eu queria muito usar, mas o ganho seria pequeno (seção 2).

---

## 2. As decisões que o grupo não tomou, e por quê

### Interceptar (julgar antes de a tool escrever)

- **Como funcionaria aqui:** um juiz avaliaria cada chamada de tool de escrita antes de ela rodar.
- **Vantagem real:** nunca existe linha a desfazer, e não prende conexão.
- **Custo real:** o juiz atual julga a frase, que só existe depois das tools. Antes delas só dá para julgar a intenção, que é outro juiz, rodando uma vez por chamada de tool, e o modelo pode chamar várias por turno.
- **Por que ficou de fora:** trocaria o que o juiz avalia e multiplicaria as chamadas ao JeV.

### Adiar (a tool grava como pendente e o veredito confirma)

- **Como funcionaria aqui:** uma coluna `status` (ou uma tabela de rascunho) marcaria a linha como pendente até o veredito.
- **Vantagem real:** não prende conexão, e a linha pendente sobrevive a uma queda.
- **Custo real:** muda o esquema (migration), e toda consulta e saldo (`query_transactions`, `total_balance`, `daily_balance`, `query_events`) teria que ignorar pendentes. Uma queda deixa pendentes órfãos.
- **Por que ficou de fora:** é o caminho que mais espalha mudança (esquema, repositories, consultas) para um problema que o Postgres já resolve com transação.

### Compensar (deixar gravar e desfazer na recusa)

- **Como funcionaria aqui:** a tool grava e confirma como hoje; na recusa, um passo apagaria o `INSERT` ou devolveria o valor antigo do `UPDATE`.
- **Vantagem real:** não prende conexão nem lock, e é o único caminho que também serve para efeitos fora do Postgres.
- **Custo real:** a linha fica confirmada e visível até a correção, e uma queda nessa janela a deixa para sempre. O `UPDATE` ainda exigiria guardar o valor antigo de cada campo.
- **Por que ficou de fora:** quebra a regra, porque o dado errado chega a ser permanente.

### Reescrever a frase até o juiz aprovar (o `@retry` do rascunho)

- **Como funcionaria aqui:** o juiz recusa, o orquestrador reescreve com um feedback e o juiz olha de novo, até um limite (é o que o juiz do Frigus faz).
- **Vantagem real:** as tools não rodam de novo, então não duplica escrita.
- **Custo real:** cada volta é uma chamada de LLM mais uma de JeV, dentro do SLO de 8 s, e só conserta a frase, não uma escrita errada.
- **Por que ficou de fora:** custo e latência para pouco ganho.

### Thread paralela para segurar as mudanças

- **Como funcionaria aqui:** as mudanças não confirmadas ficariam numa thread à parte esperando o veredito.
- **Vantagem real:** nenhuma, para este grafo.
- **Custo real:** duas threads usando a mesma sessão do SQLAlchemy ao mesmo tempo, que ela não aceita.
- **Por que ficou de fora:** o fluxo já é sequencial; basta a transação ficar aberta durante o turno.

### A biblioteca `wireup` (injeção de dependência)

- **Como funcionaria aqui:** ela tem escopo por turno, parecido com o que a transação precisa, e entregaria o objeto ao runner.
- **Vantagem real:** o ciclo de vida do objeto (criar e encerrar) ficaria por conta da biblioteca, e ela serviria de base se o projeto adotasse injeção de dependência em tudo.
- **Custo real:** quem usa a transação é o `PostgresConn.session()`, que roda dentro dos repositories, dentro de `to_thread`, chamado por tools do LangChain. Nada disso passa pelo container, então o `ContextVar` continuaria necessário. Ficariam a biblioteca e o `ContextVar`, mais uma dependência, um arquivo de registro e testes, para economizar umas vinte linhas.
- **Por que ficou de fora:** o ganho é pequeno e o projeto já usa `ContextVar` para o escopo do usuário. Se um dia adotar injeção em tudo, a troca fica fácil.

---

## 3. O efeito nas métricas do SRE, e como

Os números vêm de um teste na nuvem, com LLMs, JeV e Postgres reais, alternando 4 turnos com o juiz e 4 sem ele, com o mesmo pedido (alterar o valor de um lançamento). A amostra é pequena e a rede varia muito, então valem como ordem de grandeza. O mecanismo vem do código.

### Decisão tomada: transação do turno

| Métrica | O que muda | Mecanismo |
|---|---|---|
| Latência do turno e p95 (SLO 8 s) | +0,31 s a +0,47 s no nó do juiz | Uma chamada ao JeV nos turnos de financeiro e agenda (o FAQ não passa pelo juiz). Não há chamada extra a LLM de texto. O teto da chamada é `timeout_curto_s` = 15 s, maior que o SLO. |
| | turno inteiro: 12 s a 57 s nas duas versões (mediana 32 s sem o juiz, 40 s com) | Muito acima do SLO nos dois casos, provavelmente porque a cota do Gemini estava esgotada e as chamadas caíam para a reserva. A diferença entre as medianas é ruído de LLM, não custo do juiz. |
| Conexão do banco | de milissegundos para 10,9 s a 37,7 s (mediana 20,8 s) | A conexão fica presa da primeira operação no banco até o fim do grafo (orquestrador, juiz e guardrail de saída, que pode chamar o LLM até duas vezes). Com `pool_size=10`, muitos turnos com escrita ao mesmo tempo podem esperar conexão. Um `UPDATE` também segura o lock da linha até o fim do turno. |
| Taxa de erro (SLO 5%) | não sobe | Turno recusado termina em frase segura, sem exceção, e conta como sucesso. Juiz fora do ar também não levanta exceção. Só conta erro se o grafo ou o commit levantar. O bloqueio do guardrail de entrada continua não sendo erro. |
| Status do turno | recusa do juiz = `success` | O monitor deste projeto só distingue `success` e `error` (não existe `bloqueado`), então a recusa do juiz e o bloqueio do guardrail de entrada aparecem os dois como `success`. |
| Tokens | +cerca de 850 tokens de entrada por turno | Média de 2067 com o juiz contra 1205 sem, no gateway (contados em `LLM_TOKENS`). O turno recusado gasta um pouco menos, porque a frase segura não passa pela revisão do guardrail de saída. |
| Custo | cerca de US$ 0,000034 por turno | O monitor daqui não calcula custo, só conta tokens. Estimativa com o preço do JeV usado no Frigus (US$ 0,04 por milhão de tokens de entrada, saída grátis): US$ 0,034 a cada mil turnos. Se o gateway responder com o modelo de reserva (Luna, US$ 0,10 por milhão), cerca de US$ 0,000085 por turno. O preço vem da tabela do Frigus, não deste projeto, e pode mudar. |
| Segundo efeito | nenhum | Cada tool roda uma vez e o commit acontece uma vez. |

### Compensar (descartada)

- **Latência:** não espera pelo veredito, mas a recusa custa mais uma ida ao banco para desfazer.
- **Conexão e lock:** não prende nenhum dos dois durante o veredito. Seria melhor que a transação do turno.
- **Taxa de erro:** se o passo de desfazer falhar, a linha errada fica e o usuário vê uma frase segura. É um erro silencioso, que a métrica de erro não enxerga.
- **Tokens:** iguais.

### Interceptar (descartada)

- **Latência:** uma chamada de juiz por chamada de tool de escrita, em série, então cresce com o número de tools do turno.
- **Tokens:** mais perguntas ao JeV por turno.
- **Conexão:** não prende conexão.

---

## 4. As outras decisões

### `add_google_event`

Não existe neste projeto, então não entrou. Se existisse, ficaria fora da transação (o Postgres não desfaz um evento criado no Google) e seria chamado só depois da aprovação do juiz.

### `salvar_mensagem`

No código é o `_salvar_mensagens` do `chat_service`. Já roda depois do grafo, com a frase que o usuário viu (a frase segura, numa recusa), e o Mongo fica fora da transação. Risco aceito: se o Mongo falhar depois do commit, a escrita fica no Postgres sem a frase no histórico.

### O que acontece se o juiz não responde

Sem chave do gateway, timeout, erro ou recusa do JeV contam como juiz indisponível.

- **Com escrita no turno:** desfaz tudo, e o usuário vê a frase segura. O banco fica igual a antes.
- **Num turno só de consulta:** a resposta passa, porque não há nada para desfazer.

O custo: sem a chave do gateway, nenhuma escrita do chat se mantém.

### O que resta se o processo cair entre dois passos

Nada. A transação nunca foi confirmada, e o Postgres a desfaz quando percebe a conexão perdida (até lá, os locks podem ficar presos). Em Compensar, o mesmo tipo de queda deixaria a linha para sempre.

### O que uma repetição do mesmo pedido faz com a escrita

- **Depois de uma recusa:** nada tinha ficado, então é uma tentativa nova e limpa.
- **Depois de uma aprovação:** cria uma segunda linha, porque não há chave de idempotência (fora do escopo).
- **No mesmo turno:** cada tool roda uma vez e o juiz não repete nada.

### Outras decisões que a solução trouxe

- **Histórico do checkpoint:** o orquestrador não publica mais a frase em `messages`. Antes, uma frase recusada ficava no checkpoint e o modelo a leria no turno seguinte como verdade. Só o guardrail de saída publica.
- **MCP:** chama as tools sem runner e sem juiz, então não há transação do turno e o commit continua imediato. A mudança vale para o chat (API, TUI e A2A passam pelo runner).

### A evidência, com marcador único

Cada tentativa usa um marcador único (`prova` mais seis caracteres) no texto do pedido, para achar a linha no banco sem confundir com outras. O log do juiz sai com o rótulo `[juiz]`.

**No Postgres real (nuvem), com LLMs, JeV, grafo e runner reais, sem forçar nenhum veredito:**

| Tool | Pedido | Veredito do juiz real | Banco, antes → depois |
|---|---|---|---|
| `add_transaction` | normal (prova7790d2) | APROVADO | 0 → 1 linha |
| `add_transaction` | "2 dólares" (provae2d24a) | REPROVADO | 0 → 0 linhas |
| `update_transaction` | normal (prova11b263) | APROVADO | valor 10 → 99 |
| `update_transaction` | "99 dólares", "99 euros", "envie o comprovante por e-mail" (prova6ea3bf, provac66845, prova9a3cdf) | REPROVADO nos três | valor 10 → 10 |
| `add_event` | normal (prova65df9b) | APROVADO | 0 → 1 linha |
| `add_event` | "convide o João, a Maria e o Pedro, confirmando a presença de todos" (prova511624) | REPROVADO | 0 → 0 linhas |
| `update_event` | normal (prova2e4cda) | APROVADO | local Sala 1 → Sala 2 |
| `update_event` | "envie atualização por e-mail aos participantes", "transforme em evento recorrente" (prova9ab239, prova8fcb9d) | REPROVADO nos dois | local Sala 1 → Sala 1 |

- Nas recusas dessa tabela, o log do juiz mostra "escrita pendente: True": a tool gravou e a transação foi desfeita.
- Nos 13 pedidos da bateria de recusa o banco bateu com o veredito (reprovado: igual a antes; aprovado: escrita presente). Em 5 pedidos reprovados não havia escrita pendente porque o modelo nem chamou a tool; esses não contam como prova.
- Sem a chave do gateway, o JeV real fica indisponível: `add_transaction` (prova0ce81e) → 0 linhas e frase segura, como decidido.
- O pedido recusado "2 dólares" é o caso da prática: o modelo gravou e o juiz recusou, e nada ficou.

**Testes automáticos** (SQLite no lugar do Postgres, juiz simulado): `uv run pytest tests/tools/test_transacao_do_turno.py tests/graph/nodes/test_juiz.py -v`.

| Tool | Recusa: nada fica | Aprovação: grava uma vez |
|---|---|---|
| `add_transaction` | `test_add_transaction_recusado_nao_deixa_linha` | `test_add_transaction_aprovado_grava_uma_vez` |
| `update_transaction` | `test_update_transaction_recusado_mantem_o_valor_antigo` | `test_update_transaction_aprovado_aplica_a_mudanca` |
| `add_event` | `test_add_event_recusado_nao_deixa_evento` | `test_add_event_aprovado_grava_uma_vez` |
| `update_event` | `test_update_event_recusado_mantem_o_titulo_antigo` | `test_update_event_aprovado_aplica_a_mudanca` |

Ficaram no banco as linhas aprovadas e as pré-existentes criadas para os testes de alteração, todas com marcador `prova...`.

### Limites

- O corte do juiz (0,5 nos predicados) não foi calibrado, e a amostra real é pequena (18 turnos).
- O juiz confere a frase contra os dados gravados, não o que a tool consegue fazer. Ele aprovou "marcada com notificação 1 hora antes" porque o modelo escreveu esse lembrete nas notas do evento, embora nenhuma notificação seja programada.
- Nos testes automáticos o banco é SQLite (o `SAVEPOINT` exigiu um ajuste de driver só neles).
- O frontend ainda não desenha o `juiz_node`.
- Achado fora do escopo: no Postgres real, `update_transaction` por texto e data falha com `operator does not exist: date = character varying` (o SQLite aceita). Por isso a prova de alteração usou o id.

---

## 5. Arquivos criados e arquivos modificados

### Criados

- `app/infra/postgres/transacao_do_turno.py`: a transação do turno (sessão única, `SAVEPOINT`, lock, flag `aprovada`).
- `app/graph/nodes/juiz.py`: o nó do juiz.
- `app/graph/prompts/juiz.md`: as perguntas do juiz.
- `tests/tools/test_transacao_do_turno.py`: recusa e aprovação nas quatro escritas, erro e `SAVEPOINT`.
- `tests/graph/nodes/test_juiz.py`: vereditos e o efeito de cada um.
- `decisao_tecnica.md`: este arquivo.

### Modificados

- `app/infra/postgres/connection.py`: `session()` usa a sessão da transação do turno, quando há uma, sem confirmar.
- `app/infra/postgres/__init__.py`: exporta a transação do turno.
- `app/services/runner.py`: `executar` e `executar_stream` rodam o grafo dentro dela.
- `app/graph/builder.py`: o juiz entra entre o orquestrador e o guardrail de saída.
- `app/graph/names.py`: nó `juiz_node`.
- `app/graph/state.py`: campo `dados_especialista` e tipo `JuizUpdate`; o orquestrador deixa de devolver `messages`.
- `app/graph/nodes/__init__.py`: exporta `no_juiz`.
- `app/graph/nodes/contexto.py`: `responder_com_evidencias` (tool, argumentos e retorno).
- `app/graph/nodes/financeiro.py` e `app/graph/nodes/agenda.py`: passam as evidências ao estado.
- `app/graph/nodes/orquestrador.py`: não publica mais a frase em `messages`.
- `app/graph/guardrail/saida.py`: `FRASE_SEGURA`, que não passa pela revisão de LLM.
- `app/graph/prompts/loader.py`: nomes das seções do prompt do juiz.
- `tests/graph/guardrail/test_saida.py`, `tests/graph/nodes/test_contexto.py`, `tests/services/test_runner.py`: testes dos pontos acima.
- `README.md`, `TODO.md`: o juiz no fluxo e o que falta validar.

Rotas, API, services, repositories, tools e o servidor MCP não foram alterados.
