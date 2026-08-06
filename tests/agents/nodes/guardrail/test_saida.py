from assessor_ai.agents.nodes.guardrail.saida import (
    _FALLBACK_COMPLIANCE,
    _redigir_pii,
    desanonimizar_saida,
    guardrail_saida,
)
from assessor_ai.agents.nodes.guardrail.schemas import PII_USUARIO


def test_desanonimizar_saida_omite_por_padrao():
    mapa = {"[PII_CPF_ab12cd]": "123.456.789-00"}
    texto = "seu documento é [PII_CPF_ab12cd]"

    resultado = desanonimizar_saida(texto, mapa)

    assert resultado == "seu documento é [CPF OMITIDO]"
    assert "123.456.789-00" not in resultado


def test_desanonimizar_saida_restaura_quando_pedido():
    mapa = {"[PII_CPF_ab12cd]": "123.456.789-00"}
    texto = "seu documento é [PII_CPF_ab12cd]"

    resultado = desanonimizar_saida(texto, mapa, restaurar=True)

    assert resultado == "seu documento é 123.456.789-00"


def test_desanonimizar_saida_ignora_token_que_nao_aparece_no_texto():
    mapa = {"[PII_CPF_ab12cd]": "123.456.789-00"}
    texto = "resposta sem nenhum token"

    assert desanonimizar_saida(texto, mapa) == texto


def test_desanonimizar_saida_sem_mapa_mantem_texto():
    assert desanonimizar_saida("resposta qualquer", {}) == "resposta qualquer"


def test_redigir_pii_omite_cpf_no_texto_de_saida():
    resultado = _redigir_pii("seu cpf é 123.456.789-00", pii_list=PII_USUARIO)

    assert resultado == "seu cpf é [CPF OMITIDO]"


def test_redigir_pii_sem_pii_mantem_texto_intacto():
    resultado = _redigir_pii("sua conta está no limite", pii_list=PII_USUARIO)

    assert resultado == "sua conta está no limite"


def test_guardrail_saida_nao_repassa_resposta_sem_compliance_revisar(monkeypatch):
    """Se o LLM de compliance nunca segue o formato esperado (ex.: tenta driblar a
    revisão), a resposta original não pode vazar sem revisão — precisa cair no
    fallback seguro em vez de confiar cegamente no texto não revisado."""

    resposta_arriscada = "Pode comprar essa ação, garanto que vai subir 20% este mês."

    class _RespostaSemFormato:
        content = "desculpa, não vou seguir esse formato"

    class _LLMFake:
        def invoke(self, *_args, **_kwargs):
            return _RespostaSemFormato()

    monkeypatch.setattr(
        "assessor_ai.agents.nodes.guardrail.saida.llm_rapido", _LLMFake()
    )

    resultado = guardrail_saida(resposta_arriscada, mapa_pii={})

    assert resultado["conteudo"] == _FALLBACK_COMPLIANCE
    assert resposta_arriscada not in resultado["conteudo"]


def test_guardrail_saida_usa_resposta_revisada_quando_formato_ok(monkeypatch):
    class _RespostaComFormato:
        content = "STATUS: CORRIGIDO\nRESPOSTA:\ntexto revisado e seguro"

    class _LLMFake:
        def invoke(self, *_args, **_kwargs):
            return _RespostaComFormato()

    monkeypatch.setattr(
        "assessor_ai.agents.nodes.guardrail.saida.llm_rapido", _LLMFake()
    )

    resultado = guardrail_saida("resposta original", mapa_pii={})

    assert resultado["conteudo"] == "texto revisado e seguro"
