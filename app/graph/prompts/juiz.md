## TEMPLATE

PEDIDO_DO_USUARIO: {pergunta_original}

DADOS_DAS_TOOLS (cada linha é `tool(argumentos que ela recebeu) -> o que ela devolveu`; se nenhuma tool foi chamada, é a própria resposta do especialista): {dados_disponiveis}

RESPOSTA_GERADA (a frase que vai ser mostrada ao usuário): {resposta_gerada}

## GROUNDING

Compare a RESPOSTA_GERADA com o PEDIDO_DO_USUARIO e com os DADOS_DAS_TOOLS. Cada valor, data, nome ou
fato que a resposta afirma precisa aparecer na fala do usuário ou nos dados das tools. Dizer "não
encontrei" ou "não tenho essa informação" é sustentado.

## RELEVANCIA

A RESPOSTA_GERADA atende ao PEDIDO_DO_USUARIO e o responde por inteiro, sem deixar parte dele de lado?
Dizer claramente "não encontrei" ou "não tenho essa informação" conta como resposta completa.

## FIDELIDADE

Quando os DADOS_DAS_TOOLS mostram algo que foi gravado ou alterado (criar ou atualizar lançamento ou
evento), o que foi gravado corresponde ao que o usuário pediu? Confira nos argumentos da tool o valor, a
moeda, a data, o título e a descrição contra o PEDIDO_DO_USUARIO. Se nada foi gravado ou alterado, responda
que sim.
