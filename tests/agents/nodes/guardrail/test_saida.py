from assessor_ai.agents.nodes.guardrail.saida import _redigir_pii, desanonimizar_saida
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
