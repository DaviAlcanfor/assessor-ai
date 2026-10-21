# Dados de mercado (AwesomeAPI e Banco Central)

Cotação, PTAX, Selic/CDI/IPCA e simulação de investimento. Código em `infra/mercado/` (HTTP, cache,
métrica) e `services/mercado_service.py` (lógica) e `graph/tools/mercado/` (as 6 tools do agente financeiro). As três fontes são públicas e
sem chave. Tudo abaixo foi verificado contra as APIs reais; o que a documentação diz e o que elas
fazem divergem em vários pontos.

## O httpx quebra a query do OData do BCB (PTAX)

O endpoint da PTAX é OData. O httpx codifica `$format` como `%24format`, e o BCB responde 400
(`The system query option '$orderby' is not supported`). A query vai **crua na URL** em
`infra/mercado/bcb.py:PtaxClient.dolar` (argumento `query_crua`), nunca em `params=`. Também não usamos `$orderby`: ordena-se em
Python. As datas são `MM-DD-AAAA` entre aspas simples (`'10-13-2026'`). Fim de semana e feriado não
têm boletim: o período volta vazio (`ptax_dolar` busca o último fechamento anterior).

```python
# errado: httpx.get(url, params={"$format": "json"})  -> ?%24format=json -> 400
url = f"{base}/CotacaoDolarPeriodo(...)?@dataInicial='10-13-2026'&@dataFinalCotacao='10-16-2026'&$format=json"
```

## SGS: sempre janela de datas, nunca `/ultimos/N`

`/dados/ultimos/N` se comporta diferente por série: devolve em ordem crescente numa e **decrescente**
em outra, traz **datas futuras** (a meta Selic já tem a vigência da próxima reunião do Copom) e o BCB
o recusa em séries diárias desde 2025 (devolve uma página HTML com status de erro, não JSON). Use
`/dados?formato=json&dataInicial=dd/MM/aaaa&dataFinal=dd/MM/aaaa`, termine a janela em hoje e ordene
você mesmo (`serie_sgs` já devolve crescente). Séries usadas: 432 meta Selic (% a.a.), 4389 CDI
anualizado (% a.a.), 433 IPCA mensal, 13522 IPCA acumulado em 12 meses. A série mensal tem um ponto
por mês e o do mês corrente só sai por volta do dia 10 do seguinte, então a janela sobra um mês.

## O BCB bloqueia rajada e User-Agent padrão

Chamadas seguidas com o `User-Agent` padrão do curl/httpx foram recusadas (HTML "Requisição
inválida"). O cliente manda `assessor-ai/0.1` e há cache de 1 h para tudo do BCB. Em script de
teste ao vivo, espere ~1 s entre chamadas ao BCB.

## AwesomeAPI

- `/json/last/USD-BRL,EUR-BRL` devolve um objeto cujas chaves são o par **sem hífen** (`USDBRL`);
  números vêm como string (o pydantic converte). Par inexistente é 404.
- `/json/daily/USD-BRL/N?start_date=AAAAMMDD&end_date=AAAAMMDD` devolve uma cotação por dia que teve
  negociação, da mais recente pra mais antiga, e **só o primeiro item** traz `code`/`name`. `N` é o
  número de dias (máx. 360).
- Sem chave, a cotação atual é cacheada 1 min do lado deles: o `ttl_atual_s=60` daqui acompanha.
- `compra` = `bid`, `venda` = `ask`. `converter_moeda` usa o `bid`.

## Compliance: dado de mercado não é conselho

O guardrail de saída e o prompt do financeiro proíbem recomendar ativo. `simular_investimento` devolve
sempre o campo `aviso` (bruto, sem IR/IOF, taxa constante, sem garantia) e o prompt manda repassá-lo.
Não tire esse campo nem a regra do `financeiro.md`: uma simulação sem aviso vira "promessa de
rendimento" na boca do LLM.

## Clientes, cache e métrica

`infra/mercado/client.py:MercadoClient` é a base: GET JSON com cache (`cache.py:CacheTTL`, em memória,
FIFO de 128 entradas, indexado pela URL completa), `medir_externo(alvo)` e `MercadoError` com mensagem
segura (nunca a URL). Cada API é uma subclasse com métodos de negócio tipados: `AwesomeApiClient`
(`awesomeapi`), `PtaxClient` (`ptax`) e `SgsClient` (`sgs`). `_url()` monta a URL; `_objeto()` e
`_lista()` já validam o formato da resposta. Datas chegam parseadas (`date`/`datetime`) pelos schemas
— nada de string de data fora de `infra/mercado/schemas.py`.

Com mais de uma instância cada uma tem o seu cache; se a cota apertar, o próximo passo é Redis.
Métrica: `assessor_external_calls_total{target="awesomeapi"|"bcb", outcome}`.
