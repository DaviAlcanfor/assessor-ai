# Decisão técnica: o juiz e a escrita no banco

## 1. Decisão tomada

Regra: se o turno for recusado, nenhuma escrita dele permanece.

A escrita só fica se o juiz aprovar o turno. Para isso, as tools deixam de dar commit: todas as escritas do turno entram numa única transação do Postgres, aberta pelo runner antes do grafo e fechada depois dele. Se o juiz aprovou, o runner faz commit. Em qualquer outro caso (recusa, juiz fora do ar, erro em qualquer nó, queda do processo) a transação é desfeita. O padrão é desfazer. É a família Transacionar.

Como surgiu: antes de olhar o código, escrevi este rascunho, do jeito que veio:

```text
tem que ver oq da pra fazer 

resumindo tem que adicionar o juiz já com safety de mudanças nas coisas
primeiro temos que mapear as classes pra isso:
- em quais objetos os dados vao circular
- em qual tipo de classe isso se encaixa

pensei numa solução mas ela tem que ser alinhada com as opções ditas pelo enunciado, então precisa ver se ela se encaixa com alguma:
- Interceptar: Algo julga a ação antes de a tool que escreve ser chamada.
- Adiar: A tool prepara a mudança. A confirmação permanente espera o veredito.
- Transacionar: O turno compartilha uma unidade de trabalho. Aprovar confirma. Recusar desfaz.
- Compensar: O efeito acontece e, na recusa, uma ação inversa desfaz o que ficou.

### O que eu pensei

jogar numa thread paralela as mudanças uncommited, de acordo com o veredito, ele pega isso e executa

- um objeto de aprovação
- ele joga num yield da vida esperando
- joga uma dependência com dishka/wireup
- aceitando ele commita

recusado ele desfaz tudo e reescreve a msg pro usuário?
da pra usar @retry no recusado ate ser aprovado e não der mais pra fazer

 *depois precisa ver qual se encaixa melhor nas 4 opções
```

Viajei bastante nesse primeiro rascunho. Depois fui debatendo ele com uma IA, passando pelo código do projeto e pelo juiz do Frigus, até chegar na solução acima. A ideia central era viável: é o Transacionar, com um objeto de aprovação que confirma ou desfaz. O resto não era:

- Thread paralela e yield: o fluxo já é sequencial e a sessão do SQLAlchemy não aceita uso por duas threads ao mesmo tempo. Bastou deixar a transação aberta durante o turno.
- @retry até aprovar: cada volta custa uma chamada de LLM e uma de JeV, dentro do SLO de 8 s, e só conserta a frase, não uma escrita errada. Recusado, o turno agora desfaz e devolve uma frase segura.
- wireup: eu queria muito usar, mas não daria. O ponto de uso da transação fica fora do container dele (explicação na seção 2).

Por que cabe neste grafo: todo acesso ao Postgres passa por PostgresConn.session(). Alterando só ele, as quatro escritas ficam cobertas, sem mexer em tool, service ou repository: add_transaction, update_transaction, add_event e update_event (esta existe no projeto, mas o enunciado não lista). A transação chega às tools por um ContextVar, o mesmo mecanismo do session_context, que já leva o usuário do turno.

Por que Transacionar e não as outras: a regra exige que o dado recusado nunca fique visível nem permanente. Só a transação garante isso sem exceção: enquanto o veredito não chega, a linha nem existe para outras consultas, e se o processo cair ela some sozinha. Interceptar julgaria a ação em vez da frase, e Adiar e Compensar deixam uma linha no banco durante o turno. O custo que aceitei foi a conexão presa até o fim do turno (medido na seção 3).

Antes:
modelo → tool grava e dá commit → orquestrador → guardrail de saída → chat

Depois:
modelo → tool grava (sem commit) → orquestrador → juiz → guardrail de saída → runner: commit se aprovado, senão rollback

O juiz faz uma chamada ao JeV com três perguntas sobre a frase: ela se sustenta na fala do usuário e no retorno das tools? Responde ao pedido? O que foi gravado (valor, moeda, data) bate com o que o usuário pediu? A terceira cobre o caso dos "2 dólares", em que a frase está coerente e o dado gravado, errado. Por isso o juiz recebe também os argumentos de cada tool (o retorno do add_transaction não repete o valor). Recusado, ele troca a frase por uma fixa e segura.

O que acontece em cada desfecho (valendo para as quatro escritas):
- Aprovado: o usuário vê a frase do orquestrador e o banco guarda a escrita, uma vez.
- Recusado: o usuário vê a frase segura e o banco fica igual a antes do turno.
- Juiz sem resposta, com escrita no turno: igual ao recusado.
- Erro em algum nó: o usuário vê o erro, como já era, e o banco fica igual a antes do turno.

## 2. Caminhos descartados

Interceptar (julgar antes da tool escrever). Vantagem: nunca há o que desfazer. Custo: o juiz atual julga a frase, que só existe depois das tools; antes delas só se julgaria a intenção, outro juiz, rodando uma vez por chamada de tool. Ficou de fora por trocar o que o juiz avalia e multiplicar as chamadas ao JeV.

Adiar (a tool grava como "pendente" e o veredito confirma). Vantagem: não prende conexão e sobrevive a queda. Custo: coluna de status e migration, e toda consulta e saldo teriam que ignorar pendentes; uma queda deixa pendentes órfãos. Ficou de fora por espalhar mudança no esquema, nos repositories e nas consultas.

Compensar (deixar gravar e desfazer na recusa). Vantagem: não prende conexão nem lock. Custo: a linha fica confirmada e visível até a correção, e uma queda nessa janela a deixa para sempre; o UPDATE ainda exigiria guardar o valor antigo. Ficou de fora por quebrar a regra: o dado errado chega a ser permanente.

Reescrever a frase até o juiz aprovar (o @retry do rascunho). Vantagem: as tools não rodam de novo, então não duplica escrita. Custo: cada volta é uma chamada de LLM mais uma de JeV, dentro do SLO de 8 s, e só conserta a frase, não uma escrita errada. Ficou de fora por custo e latência para pouco ganho.

Thread paralela. O fluxo já é sequencial, então basta a transação ficar aberta durante o turno. Uma thread só traria o risco de duas usarem a mesma sessão do SQLAlchemy ao mesmo tempo.

wireup. Eu queria usar: o escopo por turno dele é parecido com o que a transação precisa. Mas quem usa a transação é o PostgresConn.session(), que roda dentro dos repositories, dentro de to_thread, chamado por tools do LangChain. Nada disso passa pelo container, então o ContextVar continuaria necessário. Ficaria a biblioteca mais o ContextVar, para economizar umas vinte linhas. Se o projeto adotar injeção de dependência em tudo, a troca fica fácil.

## 3. Efeito nas métricas do SRE

Os números vêm de um teste na nuvem, com LLMs, JeV e Postgres reais, alternando 4 turnos com o juiz e 4 sem ele, com o mesmo pedido (alterar o valor de um lançamento). A amostra é pequena e a rede varia muito, então vale como ordem de grandeza. O mecanismo vem do código.

Transação do turno (escolhida):
- Latência e p95 (SLO 8 s): sobe pelo tempo de uma chamada ao JeV nos turnos de financeiro e agenda (o FAQ não passa pelo juiz). Medido: o nó do juiz leva de 0,31 s a 0,47 s por turno. O turno inteiro variou de 12 s a 57 s nas duas versões (mediana de 32 s sem o juiz e 40 s com), muito acima do SLO nos dois casos, provavelmente porque a cota do Gemini estava esgotada e as chamadas caíam para a reserva. A diferença entre as medianas é ruído de LLM, não custo do juiz. O teto da chamada ao JeV é timeout_curto_s = 15 s, maior que o SLO. Não há chamada extra de LLM de texto.
- Conexão presa: antes por milissegundos; agora da primeira operação no banco até o fim do grafo (orquestrador, juiz e guardrail de saída, que pode chamar o LLM até duas vezes). Medido: de 10,9 s a 37,7 s por turno (mediana de 20,8 s) nesses turnos lentos; com LLMs rápidos seria bem menos, mas cresce junto com o tempo do turno. O pool tem pool_size=10, então muitos turnos com escrita simultâneos podem esperar conexão. Um UPDATE também segura o lock da linha até o fim do turno.
- Taxa de erro (SLO 5%): turno recusado termina em frase segura, sem exceção, e conta como sucesso. Juiz fora do ar também não levanta exceção. Só conta erro se o grafo ou o commit levantar. Bloqueio do guardrail de entrada continua não sendo erro.
- Tokens e custo: o JeV soma os tokens de entrada em LLM_TOKENS. Medido: o juiz acrescenta cerca de 850 tokens de entrada no gateway por turno (média de 2067 com o juiz contra 1205 sem). O turno recusado gasta um pouco menos, porque a frase segura não passa pela revisão do guardrail de saída.
- Segundo efeito: nenhum. Cada tool roda uma vez e o commit acontece uma vez.

Compensar (descartada): não prende conexão nem lock, mas a recusa custa mais uma ida ao banco. Se o passo de desfazer falhar, a linha errada fica e o usuário vê uma frase segura, um erro que a métrica de erro não enxerga.

Interceptar (descartada): uma chamada de juiz por chamada de tool de escrita, em série, então a latência cresce com o número de tools do turno. Não prende conexão.

## 4. Outras decisões

- add_google_event: não existe neste projeto, então não entrou. Se existisse, ficaria fora da transação (o Postgres não desfaz um evento do Google) e seria chamado só depois da aprovação.
- salvar_mensagem: no código é o _salvar_mensagens do chat_service. Já roda depois do grafo, com a frase que o usuário viu (a segura, numa recusa), e o Mongo fica fora da transação. Risco aceito: se o Mongo falhar depois do commit, a escrita fica no Postgres sem a frase no histórico.
- Histórico do checkpoint: o orquestrador não publica mais a frase em messages. Antes, uma frase recusada ficava no checkpoint e o modelo a leria no turno seguinte como verdade. Só o guardrail de saída publica.
- Juiz sem resposta (sem chave, timeout, erro, recusa do JeV): com escrita no turno, desfaz e mostra a frase segura; num turno só de consulta, a resposta passa. O custo: sem a chave do gateway, nenhuma escrita do chat se mantém.
- Queda do processo entre dois passos: não resta nada. A transação nunca foi confirmada e o Postgres a desfaz quando percebe a conexão perdida (até lá, os locks podem ficar presos).
- Repetição do mesmo pedido: depois de uma recusa é uma tentativa limpa; depois de uma aprovação cria uma segunda linha, porque não há chave de idempotência (fora do escopo). No mesmo turno, cada tool roda uma vez.
- Falha numa tool não desfaz as outras: cada operação roda num SAVEPOINT. Duas tools simultâneas são serializadas por um Lock, porque a sessão do SQLAlchemy não aceita uso concorrente.
- MCP: chama as tools sem runner e sem juiz, então não há transação do turno e o commit continua imediato. A mudança vale para o chat (API, TUI e A2A passam pelo runner).

Evidência: cada tentativa usa um marcador único (`marcador-<uuid>` no source_text). Para rodar:
uv run pytest tests/tools/test_transacao_do_turno.py tests/graph/nodes/test_juiz.py -v

Testes de recusa (nada fica) e de aprovação (grava uma vez), por tool:
- add_transaction: test_add_transaction_recusado_nao_deixa_linha / test_add_transaction_aprovado_grava_uma_vez
- update_transaction: test_update_transaction_recusado_mantem_o_valor_antigo / test_update_transaction_aprovado_aplica_a_mudanca
- add_event: test_add_event_recusado_nao_deixa_evento / test_add_event_aprovado_grava_uma_vez
- update_event: test_update_event_recusado_mantem_o_titulo_antigo / test_update_event_aprovado_aplica_a_mudanca

Evidência no Postgres real (nuvem), com LLMs, JeV (gateway), grafo e runner reais, sem forçar nenhum veredito. O log do juiz sai com o rótulo [juiz]. Cada tentativa usa um marcador único:
- add_transaction, pedido normal (prova7790d2): [juiz] APROVADO, 0 → 1 linha.
- add_transaction, "2 dólares" (provae2d24a): [juiz] REPROVADO, 0 → 0 linhas, o usuário recebe a frase segura. É o caso da prática: o modelo gravou e o juiz recusou, e nada ficou.
- update_transaction (prova11b263): [juiz] APROVADO, valor 10 → 99.
- add_event (prova65df9b): [juiz] APROVADO, 0 → 1 linha.
- update_event (prova2e4cda): [juiz] APROVADO, local Sala 1 → Sala 2.

Recusa nas outras três tools: o juiz real só recusou o caso dos dólares, então para mostrar a recusa em update_transaction (provaadd60a), add_event (provad22238, prova34f3fd) e update_event (prova97a70c) o veredito foi forçado, com o resto real (LLMs, grafo, runner, banco). Resultado: valor 10 → 10, 0 → 0 linhas e local Sala 1 → Sala 1.

Sem a chave do gateway, o JeV real fica indisponível: add_transaction (prova0ce81e) → 0 linhas e frase segura, como decidido.

Ficaram no banco as linhas aprovadas e as pré-existentes criadas para os testes de alteração, todas com marcador "prova...".

Limites: o corte do juiz (0,5 nos predicados) não foi calibrado e a amostra real é pequena (5 turnos). Nos testes automáticos o banco é SQLite (o SAVEPOINT exigiu um ajuste de driver só neles). O frontend ainda não desenha o juiz_node. Achado fora do escopo: no Postgres real, update_transaction por texto e data falha com "operator does not exist: date = character varying" (o SQLite aceita); por isso a prova de alteração usou o id.

## 5. Arquivos

Criados:
- app/infra/postgres/transacao_do_turno.py: a transação do turno (sessão única, SAVEPOINT, lock, flag aprovada).
- app/graph/nodes/juiz.py: o nó do juiz.
- app/graph/prompts/juiz.md: as perguntas do juiz.
- tests/tools/test_transacao_do_turno.py: recusa e aprovação nas quatro escritas, erro e SAVEPOINT.
- tests/graph/nodes/test_juiz.py: vereditos e o efeito de cada um.
- decisao_tecnica.md

Modificados:
- app/infra/postgres/connection.py: session() usa a sessão da transação do turno, quando há uma, sem confirmar.
- app/infra/postgres/__init__.py: exporta a transação do turno.
- app/services/runner.py: executar e executar_stream rodam o grafo dentro dela.
- app/graph/builder.py: o juiz entra entre o orquestrador e o guardrail de saída.
- app/graph/names.py: nó juiz_node.
- app/graph/state.py: campo dados_especialista e tipo JuizUpdate; o orquestrador deixa de devolver messages.
- app/graph/nodes/__init__.py: exporta no_juiz.
- app/graph/nodes/contexto.py: responder_com_evidencias (tool, argumentos e retorno).
- app/graph/nodes/financeiro.py e app/graph/nodes/agenda.py: passam as evidências ao estado.
- app/graph/nodes/orquestrador.py: não publica mais a frase em messages.
- app/graph/guardrail/saida.py: FRASE_SEGURA, que não passa pela revisão de LLM.
- app/graph/prompts/loader.py: nomes das seções do prompt do juiz.
- tests/graph/guardrail/test_saida.py, tests/graph/nodes/test_contexto.py, tests/services/test_runner.py: testes dos pontos acima.
- README.md, TODO.md: o juiz no fluxo e o que falta validar.
