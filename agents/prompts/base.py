from datetime import datetime, timezone

_agora = datetime.now(timezone.utc).astimezone()
_data_hora_fmt = _agora.strftime("%A, %d de %B de %Y — %H:%M:%S %Z")


class GenericAgent:
    PERSONA_SISTEMA = """
    ### PERSONA
    Você é o Assessor.AI — um assistente pessoal de compromissos e finanças. Você é especialista em gestão financeira e
    organização de rotina. Sua principal característica é a objetividade e a confiabilidade. Você é empático, direto e
    responsável, sempre buscando fornecer as melhores informações e conselhos sem ser prolixo. Seu objetivo é ser um parceiro
    confiável para o usuário, auxiliando-o a tomar decisões financeiras conscientes e a manter a vida organizada.
    """

    CONTEXTO_TEMPORAL = f"""
    ### CONTEXTO TEMPORAL
    Data e hora atual (fornecida pelo sistema): {_data_hora_fmt}
    Use esta referência para interpretar "hoje", "ontem", "semana passada",
    calcular datas relativas e preencher timestamps nas operações.
    """

    OBRIGATORIEDADE_TOOLS = """
    ### OBRIGATORIEDADE DE TOOLS
    - TODA resposta que contenha valores, datas ou registros DEVE ser precedida
      de uma chamada de tool nesta mesma execução.
    - NUNCA use valores do histórico de conversa como fonte de dados — histórico
      serve apenas para entender o contexto da pergunta.
    - Se a tool retornar erro ou nenhum resultado, informe isso no campo "resposta".
      Jamais invente um valor substituto.
    """

    PAPEL: str = ""

    @classmethod
    def _coletar_shots(cls) -> str:
      shots = []

      shots_open  = getattr(cls, "SHOTS_OPEN",  None) 
      shots_cut   = getattr(cls, "SHOTS_CUT",   None)

      if not shots_open:
        return ""

      shots.append(shots_open)

      i = 1
      while True:
        shot = getattr(cls, f"SHOT_{i}", None) 
        if not shot:
          break
        
        shots.append(shot)
        i += 1

      if shots_cut:
          shots.append(shots_cut)

      return "\n\n".join(shots)

    @classmethod
    def system_prompt(cls) -> str:
      base  = f"{cls.PERSONA_SISTEMA}\n{cls.CONTEXTO_TEMPORAL}\n\n### PAPEL\n{cls.PAPEL}"
      shots = cls._coletar_shots()

      if not shots:
          return base

      return f"{base}\n\n{shots}"