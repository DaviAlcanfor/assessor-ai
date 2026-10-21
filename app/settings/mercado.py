from pydantic import BaseModel


class MercadoSettings(BaseModel):
    """Dados de mercado (cotação, indicadores). As três fontes são públicas: não há chave."""

    awesomeapi_base_url: str = "https://economia.awesomeapi.com.br"
    bcb_ptax_base_url: str = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
    bcb_sgs_base_url: str = "https://api.bcb.gov.br/dados/serie"

    timeout_s: float = 10.0
    # AwesomeAPI já cacheia 1 min do lado dela; indicadores e histórico mudam no máximo 1x por dia.
    ttl_atual_s: int = 60
    ttl_historico_s: int = 3600
