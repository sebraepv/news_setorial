"""
Prompts para geração da newsletter.

Este módulo centraliza os prompts utilizados pelo NewsletterBuilder.

Boas práticas aplicadas:
- Respostas em JSON válido sempre que possível.
- Estrutura compatível com o parser do builder.py.
- Prompts explícitos para reduzir alucinação.
- Instruções para não inventar informações.
- Linguagem executiva e objetiva.
"""


from typing import Union, Sequence


# ---------------------------------------------------------------------
# Prompts setoriais
# ---------------------------------------------------------------------

def get_sector_prompt(sector: str, news_data: str) -> str:
    """
    Retorna o prompt específico para processar notícias de um setor.

    Args:
        sector: Nome do setor. Ex: agronegócio, comércio, indústria, serviço.
        news_data: Notícias do setor em formato string/JSON.

    Returns:
        Prompt formatado para o LLM.
    """

    sector = (sector or "").strip().lower()

    sector_contexts = {
        "agronegócio": {
            "persona": "Você é um analista especializado em agronegócio, cadeias produtivas, commodities, clima, crédito rural e mercado agrícola.",
            "focus": [
                "principais movimentos do setor agropecuário",
                "impactos para produtores rurais, cooperativas e fornecedores",
                "efeitos sobre custos, produtividade, exportações e abastecimento",
                "perspectivas para os próximos dias",
            ],
        },
        "comércio": {
            "persona": "Você é um analista especializado em comércio, varejo, consumo, comportamento do consumidor e ambiente regulatório.",
            "focus": [
                "tendências de consumo e varejo",
                "impactos econômicos e regulatórios",
                "efeitos sobre pequenos negócios, lojistas e distribuidores",
                "oportunidades comerciais de curto prazo",
            ],
        },
        "indústria": {
            "persona": "Você é um analista especializado em indústria, manufatura, produtividade, inovação, infraestrutura e cadeias de suprimentos.",
            "focus": [
                "movimentos relevantes da indústria e manufatura",
                "avanços tecnológicos e produtivos",
                "desafios de oferta, demanda, crédito e custos",
                "perspectivas de crescimento e riscos operacionais",
            ],
        },
        "serviços": {
            "persona": "Você é um analista especializado no setor de serviços. Analise tendências, notícias e movimentos econômicos sob a perspectiva do empreendedor, identificando impactos no faturamento, custos, produtividade, experiência do cliente e crescimento do negócio.",
            "focus": [
                "inovações e transformação digital",
                "movimentos de mercado, investimentos e crédito",
                "efeitos para empresas prestadoras de serviço",
                "oportunidades e riscos para pequenos negócios",
            ],
        },
    }

    context = sector_contexts.get(
        sector,
        {
            "persona": "Você é um consultor  de negócios especializado em pequenos negócios, setores produtivos e tendências de mercado.",
            "focus": [
                "principais acontecimentos do setor",
                "impactos econômicos e empresariais",
                "riscos e oportunidades",
                "perspectivas de curto prazo",
            ],
        },
    )

    focus_items = "\n".join(
        f"{index + 1}. {item}"
        for index, item in enumerate(context["focus"])
    )

    return f"""
    {context["persona"]}

    Você receberá um conjunto de notícias do setor "{sector}".

    Sua tarefa é analisar as notícias e produzir uma síntese executiva setorial.

    IMPORTANTE:
    - Use somente as informações presentes nas notícias fornecidas.
    - Não invente fatos, números, empresas, datas ou projeções.
    - Se houver poucas informações, seja transparente e faça uma análise conservadora.
    - Evite repetir títulos de notícias literalmente.
    - Priorize impactos práticos para empresários, gestores, analistas e pequenos negócios.
    - Escreva em português do Brasil.
    - Use linguagem clara, objetiva e profissional.

    FOCOS DA ANÁLISE:
    {focus_items}

    FORMATO DA RESPOSTA:
    Retorne SOMENTE um JSON válido, sem markdown, sem comentários e sem texto fora do JSON.

    Use exatamente esta estrutura:

    {{
    "titulo": "Título curto e executivo para o setor",
    "analise": "Resumo executivo de 2 a 3 parágrafos sobre o setor.",
    "destaques": [
        "Destaque objetivo 1",
        "Destaque objetivo 2",
        "Destaque objetivo 3"
    ],
    "riscos": [
        "Risco relevante 1",
        "Risco relevante 2"
    ],
    "oportunidades": [
        "Oportunidade relevante 1",
        "Oportunidade relevante 2"
    ]
    }}

    NOTÍCIAS DO SETOR:
    {news_data}
    """.strip()


# ---------------------------------------------------------------------
# Prompts auxiliares
# ---------------------------------------------------------------------
def get_news_items_summaries_prompt(sector: str, news_json: str, max_items: int = 5) -> str:
    """
    Prompt para gerar resumos editoriais curtos das principais notícias de um setor.
    """

    return f"""
Você é um editor de newsletter executiva para empresários, gestores e pequenos negócios.

Você receberá até {max_items} notícias do setor "{sector}".

Sua tarefa é transformar o resumo original de cada notícia em um resumo editorial curto,
atrativo e informativo para compor uma newsletter.

REGRAS:
- Use somente as informações fornecidas.
- Não invente fatos, números, empresas ou conclusões.
- Não copie o texto original literalmente.
- Escreva em português do Brasil.
- Cada resumo deve ter no máximo 5 linhas.
- O texto deve despertar interesse para leitura da notícia completa.
- Não use markdown.
- Retorne SOMENTE um JSON válido.
- Preserve a ordem das notícias recebidas.

FORMATO OBRIGATÓRIO:

{{
  "noticias": [
    {{
      "title": "Título original da notícia",
      "newsletter_summary": "Resumo editorial curto, atrativo e informativo."
    }}
  ]
}}

NOTÍCIAS:
{news_json}
""".strip()


def get_newsletter_intro_prompt(sectors: Sequence[str]) -> str:
    """
    Retorna o prompt para criar uma introdução da newsletter.
    """

    sectors_str = ", ".join(str(sector) for sector in sectors)

    return f"""
Você é o editor de uma newsletter executiva de negócios.

Crie uma introdução atrativa para uma newsletter que cobre os setores:
{sectors_str}

A introdução deve:
1. Ser profissional e objetiva.
2. Contextualizar a importância de acompanhar esses setores.
3. Ter no máximo 2 parágrafos.
4. Não inventar fatos específicos.
5. Escrever em português do Brasil.

Retorne apenas o texto da introdução, sem título.
""".strip()


def get_newsletter_closing_prompt() -> str:
    """
    Retorna o prompt para criar um encerramento da newsletter.
    """

    return """
Você é o editor de uma newsletter executiva de negócios.

Crie um encerramento profissional e breve para a newsletter.

O encerramento deve:
1. Reforçar a importância do acompanhamento contínuo do ambiente de negócios.
2. Convidar o leitor a acompanhar as próximas edições.
3. Ter no máximo 1 parágrafo.
4. Não inventar informações.
5. Escrever em português do Brasil.

Retorne apenas o texto do encerramento, sem título.
""".strip()


# ---------------------------------------------------------------------
# Prompt principal da newsletter
# ---------------------------------------------------------------------

def get_newsletter_prompt(data: Union[list, tuple, str]) -> str:
    """
    Prompt principal para geração completa da newsletter.

    Comportamentos:
    - Se `data` for lista ou tupla, gera prompt de introdução.
    - Se `data == "closing"`, gera prompt de encerramento.
    - Se `data` for string, trata como JSON das notícias e análises setoriais.
    """

    if isinstance(data, (list, tuple)):
        return get_newsletter_intro_prompt(data)

    if data == "closing":
        return get_newsletter_closing_prompt()

    if not isinstance(data, str):
        raise TypeError(
            "get_newsletter_prompt aceita uma lista de setores, "
            "a string 'closing' ou uma string JSON com notícias."
        )

    news_json = data

    return f"""
    Você é o editor-chefe de uma newsletter executiva voltada para empresários donos de pequenos negócios,
    gestores públicos, lideranças setoriais e tomadores de decisão.

    Você receberá um JSON com notícias organizadas por setor.

    O JSON pode conter:
    - notícias originais;
    - análises setoriais previamente geradas;
    - destaques por setor;
    - scores de relevância;
    - fontes e datas.

    Sua tarefa é transformar esse conteúdo em uma newsletter estratégica.

    ========================
    REGRAS IMPORTANTES
    ========================

    1. Use somente as informações presentes no JSON recebido.
    2. Não invente fatos, números, nomes de empresas, datas ou projeções.
    3. Não cite notícias que não estejam no JSON.
    4. Elimine redundâncias.
    5. Priorize fatos com maior relevância estratégica.
    6. Relacione acontecimentos entre setores quando fizer sentido.
    7. Destaque tendências econômicas, riscos e oportunidades.
    8. Dê atenção especial a impactos para pequenos negócios.
    9. Escreva em português do Brasil.
    10. Use linguagem executiva, clara e objetiva.
    11. Retorne SOMENTE um JSON válido.
    12. Não use markdown.
    13. Não coloque comentários antes ou depois do JSON.

    ========================
    FORMATO OBRIGATÓRIO DA RESPOSTA
    ========================

    Retorne exatamente um JSON neste formato:

    {{
    "introducao": "Texto de abertura da newsletter em 1 ou 2 parágrafos.",

    "setores": {{
        "agronegócio": {{
        "titulo": "Título executivo do bloco de agronegócio",
        "analise": "Análise executiva do setor em 2 ou 3 parágrafos.",
        "destaques": [
            "Destaque objetivo 1",
            "Destaque objetivo 2",
            "Destaque objetivo 3"
        ],
        "riscos": [
            "Risco relevante 1",
            "Risco relevante 2",
            "Risco relevante 3"
        ],
        "oportunidades": [
            "Oportunidade relevante 1",
            "Oportunidade relevante 2",
            "Oportunidade relevante 3"
        ]
        }},

        "comércio": {{
        "titulo": "Título executivo do bloco de comércio",
        "analise": "Análise executiva do setor em 2 ou 3 parágrafos.",
        "destaques": [
            "Destaque objetivo 1",
            "Destaque objetivo 2",
            "Destaque objetivo 3"
        ],
        "riscos": [
            "Risco relevante 1",
            "Risco relevante 2",
            "Risco relevante 3"
        ],
        "oportunidades": [
            "Oportunidade relevante 1",
            "Oportunidade relevante 2",
            "Oportunidade relevante 3"
        ]
        }},

        "indústria": {{
        "titulo": "Título executivo do bloco de indústria",
        "analise": "Análise executiva do setor em 2 ou 3 parágrafos.",
        "destaques": [
            "Destaque objetivo 1",
            "Destaque objetivo 2",
            "Destaque objetivo 3"
        ],
        "riscos": [
            "Risco relevante 1",
            "Risco relevante 2",
            "Risco relevante 3"
        ],
        "oportunidades": [
            "Oportunidade relevante 1",
            "Oportunidade relevante 2",
            "Oportunidade relevante 3"
        ]
        }},

        "serviço": {{
        "titulo": "Título executivo do bloco de serviços",
        "analise": "Análise executiva do setor em 2 ou 3 parágrafos.",
        "destaques": [
            "Destaque objetivo 1",
            "Destaque objetivo 2",
            "Destaque objetivo 3"
        ],
        "riscos": [
            "Risco relevante 1",
            "Risco relevante 2",
            "Risco relevante 3"
        ],
        "oportunidades": [
            "Oportunidade relevante 1",
            "Oportunidade relevante 2",
            "Oportunidade relevante 3"
        ]
        }}
    }},

    "principais_tendencias": [
        "Tendência estratégica 1",
        "Tendência estratégica 2",
        "Tendência estratégica 3"
    ],

    "oportunidades": [
        "Oportunidade geral 1",
        "Oportunidade geral 2",
        "Oportunidade geral 3"
    ],

    "riscos": [
        "Risco geral 1",
        "Risco geral 2",
        "Risco geral 3"
    ],

    "conclusao": "Texto final da newsletter em 1 parágrafo."
    }}

    ========================
    REGRAS PARA SETORES AUSENTES
    ========================

    Se algum setor do formato obrigatório não tiver notícias no JSON recebido:

    - Mantenha a chave do setor.
    - Use strings vazias em "titulo" e "analise".
    - Use listas vazias em "destaques", "riscos" e "oportunidades".

    Exemplo:

    "setor_sem_noticias": {{
    "titulo": "",
    "analise": "",
    "destaques": [],
    "riscos": [],
    "oportunidades": []
    }}

    ========================
    JSON DE ENTRADA
    ========================

    {news_json}
    """.strip()