# JeV (Decisions API do Vercel AI Gateway)

O JeV (TypeSafe) responde perguntas fechadas com probabilidade, sem gerar texto. Aqui ele é chamado
por `POST {gateway}/decisions` (`infra/jev/`) e decide o guardrail de entrada e o roteador, sempre
com o LLM de reserva. Portado do frigus-ai. Contrato: https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-decisions

**Nada disso foi exercitado contra o gateway real** (ver o primeiro item). O contrato vem da
documentação e dos testes com resposta simulada (`tests/infra/test_jev.py`).

## Contrato: as classes de `schemas.py` e o JSON equivalente

Cada classe é um objeto do JSON do mesmo nome. Pedido e resposta têm formas separadas.

```text
PedidoDecisao ──────────────► corpo do POST /decisions
  ├─ questions: list[Pergunta]       cada pergunta é um dos três tipos abaixo
  └─ provider_options                serializa como "providerOptions" (alias)

RespostaDecisao ◄────────────── corpo da resposta
  ├─ answers: list[Resposta]         na MESMA ordem das perguntas
  ├─ model                           quem respondeu de fato (JeV ou a reserva)
  └─ usage                           {"input_tokens": ...}
```

| Pergunta (pedido) | `type` | Resposta | `type` | O que traz |
|---|---|---|---|---|
| `PerguntaPredicado` | `predicate` | `Predicado` | `predicate` | `probability` de ser "sim" (`.sim` = 0,5 ou mais) |
| `PerguntaEscolha` | `choice` | `Escolha` | `choice` | `choice` (a opção) e `confidence` |
| `PerguntaNota` | `score` | `Nota` | `score` | `score` (média ponderada dos níveis) e `confidence` |
| qualquer uma | — | `Recusa` | `refusal` | só `name`: o modelo não quis responder |

**Pedido**: as três perguntas juntas, em Python e no JSON que vai pela rede.

```python
PedidoDecisao(
    model="typesafe-ai/jev",
    input="Quanto gastei esse mês e tenho reunião amanhã?",
    questions=[
        PerguntaPredicado(name="financeiro", instructions="Precisa do especialista financeiro?"),
        PerguntaEscolha(
            name="categoria",
            instructions="Classifique a mensagem.",
            choices={Categoria.APROVADO: "mensagem legítima", Categoria.POLITICO: "debate político"},
        ),
        PerguntaNota(
            name="urgencia",
            instructions="Quão urgente?",
            levels=[Nivel(label="baixa"), Nivel(label="alta", description="precisa de resposta já")],
        ),
    ],
    provider_options={"gateway": {"models": ["openai/gpt-6-luna-decisions"]}},
)
```

```json
{
  "model": "typesafe-ai/jev",
  "input": "Quanto gastei esse mês e tenho reunião amanhã?",
  "questions": [
    { "type": "predicate", "name": "financeiro", "instructions": "Precisa do especialista financeiro?" },
    { "type": "choice", "name": "categoria", "instructions": "Classifique a mensagem.",
      "choices": [
        { "value": "APROVADO", "description": "mensagem legítima" },
        { "value": "POLITICO", "description": "debate político" }
      ] },
    { "type": "score", "name": "urgencia", "instructions": "Quão urgente?",
      "levels": [
        { "label": "baixa" },
        { "label": "alta", "description": "precisa de resposta já" }
      ] }
  ],
  "providerOptions": { "gateway": { "models": ["openai/gpt-6-luna-decisions"] } }
}
```

Dois detalhes do que a classe faz por você: `choices` aceita `{opção: descrição}` e vira a lista de
`{"value", "description"}` sozinho, e os campos vazios (`description=None`) saem do JSON.

**Resposta**: uma resposta por pergunta, na mesma ordem; `answers[i]` responde `questions[i]`.

```json
{
  "model": "typesafe-ai/jev",
  "answers": [
    { "type": "predicate", "name": "financeiro", "probability": 0.93 },
    { "type": "choice", "name": "categoria", "choice": "APROVADO", "confidence": 0.98 },
    { "type": "score", "name": "urgencia", "score": 0.4, "confidence": 0.7 }
  ],
  "usage": { "input_tokens": 96, "output_tokens": 0 }
}
```

O `type` decide qual classe lê cada item: `{"type": "predicate", ...}` vira `Predicado`,
`{"type": "refusal", ...}` vira `Recusa`. Quem usa o resultado não mexe nessas classes: `decidir()`
devolve um `Decisoes`, e `decisoes.sim("financeiro")` ou `decisoes.escolha("categoria")` pegam o valor pelo
nome da pergunta.

## Toda chamada dá 403 até a conta Vercel ter cartão cadastrado

`GET /models` funciona com a chave, mas `/chat/completions` e `/decisions` voltam
`customer_verification_required`, até pros créditos gratuitos. Cadastrar o cartão não tira a conta do
plano gratuito; só **comprar** créditos tira. Enquanto isso, JeV e Luna respondem 403 e o código cai
nos LLMs normais (o JeV loga warning a cada turno; tire `LLM__GATEWAY__API_KEY` se incomodar).

## Três tipos de pergunta, e nome único por requisição

`predicate` (sim/não, devolve `probability`), `choice` (de 1 a 255 opções, devolve `choice`,
`confidence` e `probabilities`) e `score` (2 a 10 níveis, devolve `score`). As respostas voltam **na
ordem das perguntas**, e o nome de cada pergunta tem que ser único. `decidir()` faz várias perguntas
sobre a mesma entrada numa requisição só; hoje o guardrail e o roteador usam uma `choice` cada
(`escolher()`).

`choice` aceita só string ou bool como valor, então as opções precisam ser `StrEnum` (o
`PerguntaEscolha` aceita `{opção: descrição}` direto e converte). Opções que só existem em runtime
(IDs de transação, de evento) são strings, e o limite é 255 por pergunta: nunca mande o catálogo inteiro.

## Recusa é uma resposta, não um erro HTTP

Se o modelo se recusa a responder uma pergunta, ela volta como `{"type": "refusal"}` na posição dela
e as outras são respondidas normalmente (e a requisição é cobrada). `Recusa` está no contrato e
`_validar` a trata como falha, igual a uma opção fora da lista (`invalida`). Os dois contam em
`assessor_jev_decisions_total` e caem no fallback de quem chamou.

## O modelo é só texto: imagem dá 400

`typesafe-ai/jev` não aceita imagem. A reserva `openai/gpt-6-luna-decisions` aceita, mas nenhum uso
atual manda imagem. A reserva vai em `providerOptions.gateway.models`, e o gateway a usa sozinho se o
JeV falhar. A resposta traz o modelo que respondeu de fato (`model`), e é isso que a métrica
`modelo` mostra.

## O SDK `openai` (3.5.0) não tem `decisions`

`OpenAI().decisions` não existe nessa versão. O cliente usa `httpx` direto, o que também significa que
**tokens e custo não passam pelo callback do LangChain**: `decidir()` conta
`assessor_llm_tokens_total` por conta própria (`provider="gateway"`). Custo não é medido aqui (o
Frigus usa US$ 0,04 por milhão de tokens de entrada, saída grátis).

## Confiança não é probabilidade de acerto

`confidence=0,8` não quer dizer 80% de acerto (https://docs.typesafe.ai/confidence). O predicado
vira sim/não com o corte fixo de 0,5 (`Predicado.sim`), **não calibrado** com perguntas reais do
assessor. Nada aqui usa `confidence` (nem tem histograma dela); não coloque limiar nela sem exemplos medidos.

## O roteador só enxerga a última pergunta do usuário

O JeV recebe só o texto da última `HumanMessage`, sem histórico, e escolhe entre `financeiro`,
`agenda`, `faq` ou `nenhum` (`DESCRICAO_ROTA` em `graph/agents/nodes/router.py`). `nenhum` devolve a
vez pro roteador LLM, que tem o histórico e escreve a resposta (saudação, fora de escopo) — resposta que
só faz sentido com contexto ("sim", "o de ontem") deveria cair aí. O risco é um follow-up ambíguo
("pode marcar às 10h" depois de o assistente falar de um gasto) casar com o domínio errado, já que o
contexto que o desambiguaria não chega ao JeV. Se isso aparecer, mande também a mensagem anterior do
assistente. `pergunta_original` vira o texto cru da mensagem (o prompt do LLM já pedia "sem edições").

## Contrato em Pydantic: o `type` é o discriminador

`schemas.py` usa `Literal[TipoPergunta.X]` com o valor padrão em cada classe. Não junte os três tipos
num `Literal` só: o Pydantic usa esse campo pra saber se `{"type": "predicate", ...}` é um `Predicado`
ou uma `Escolha`, e perderia a separação. Os três aparecem juntos só nas uniões (`Pergunta`,
`Resposta`).

```python
class PerguntaPredicado(BaseModel):
    type: Literal[TipoPergunta.PREDICADO] = TipoPergunta.PREDICADO
    ...

type Pergunta = Annotated[PerguntaPredicado | PerguntaEscolha | PerguntaNota, Field(discriminator="type")]
```

## Cada uso novo passa o próprio `uso` e cuida da cardinalidade

`decidir(uso, ...)` separa as métricas por quem pergunta. A resposta entra como label em
`assessor_jev_decisions_total`, o que só serve pra opções fixas (8 categorias, 4 rotas, sim/não); opção dinâmica
(ID de transação) precisa de um rótulo genérico, senão a cardinalidade explode.
