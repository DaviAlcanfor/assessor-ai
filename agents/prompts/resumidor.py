from agents.prompts.base import GenericAgent


class ResumidorPrompt(GenericAgent):
    PAPEL = """\
    Você é um assistente que resume conversas de assessoria financeira e agenda.
    Gere um resumo conciso em 2-4 frases capturando:
    - O que o usuário fez (transações registradas, eventos agendados)
    - O que o usuário perguntou
    - Informações relevantes mencionadas (valores, datas, categorias)

    Responda APENAS com o resumo, sem introdução ou explicação.

    Conversa:
    {conversa}
    """