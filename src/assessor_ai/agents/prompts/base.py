from datetime import UTC, datetime


class GenericAgent:
    PERSONA_SISTEMA = """
    ### PERSONA
    Você é o Assessor.AI — um assistente pessoal de compromissos e finanças. Você é especialista em gestão financeira e
    organização de rotina. Sua principal característica é a objetividade e a confiabilidade. Você é empático, direto e
    responsável, sempre buscando fornecer as melhores informações e conselhos sem ser prolixo. Seu objetivo é ser um parceiro
    confiável para o usuário, auxiliando-o a tomar decisões financeiras conscientes e a manter a vida organizada.
    """

    @staticmethod
    def contexto_temporal() -> str:
      """
      Bloco de data/hora, calculado na hora da chamada — nunca no import.

      `graph/agents.py` compila os agentes no import do módulo, então qualquer
      data embutida no system_prompt congela junto com o processo. No terminal
      e na TUI isso passa despercebido (reiniciam a cada uso); a API fica com
      "hoje" travado na data do deploy. Por isso o bloco vai no contexto de
      cada turno (`contexto_do_turno`), não no system_prompt dos agentes.
      """

      agora = datetime.now(UTC).astimezone()
      formatada = agora.strftime("%A, %d de %B de %Y — %H:%M:%S %Z")

      return f"""### CONTEXTO TEMPORAL
    Data e hora atual (fornecida pelo sistema): {formatada}
    Use esta referência para interpretar "hoje", "ontem", "semana passada",
    calcular datas relativas e preencher timestamps nas operações."""

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
      base  = f"{cls.PERSONA_SISTEMA}\n\n### PAPEL\n{cls.PAPEL}"
      shots = cls._coletar_shots()

      if not shots:
          return base

      return f"{base}\n\n{shots}"


def contexto_do_turno(perfil_usuario: str = "", pergunta_original: str = "") -> str:
    """
    Contexto que muda a cada turno e por isso não cabe no system_prompt: os
    agentes são compilados uma única vez, no import de `graph/agents.py`.
    Entra como mensagem de sistema extra no invoke do nó.
    """

    blocos = [GenericAgent.contexto_temporal()]

    if perfil_usuario:
        blocos.append(f"### PERFIL DO USUÁRIO\n{perfil_usuario}")

    if pergunta_original:
        blocos.append(f"### PERGUNTA ENCAMINHADA PELO ROTEADOR\n{pergunta_original}")

    return "\n\n".join(blocos)
