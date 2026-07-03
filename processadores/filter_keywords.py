import json
from pathlib import Path

import pandas as pd

# Caminho do arquivo de configuração
CONFIG_PATH = (
    Path(__file__).parent.parent
    / "config"
    / "keywords.json"
)

# Carrega o JSON apenas uma vez
with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    CONFIG = json.load(file)


def find_topics(text: str) -> dict:
    """
    Procura palavras-chave no texto e retorna
    os tópicos encontrados.
    """

    if pd.isna(text):
        text = ""

    text = text.lower()

    matches = []

    for item in CONFIG:
        topic = item.get("topic") or item.get("topico")
        values = item

        found_keywords = []

        for keyword in values["keywords"]:

            if keyword.lower() in text:
                found_keywords.append(keyword)

        if found_keywords:

            matches.append(
                {
                    "topic": topic,
                    "priority": values["priority"],
                    "keywords": found_keywords,
                }
            )

    return matches


def filter_keywords(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra notícias utilizando o arquivo keywords.json.

    Adiciona ao DataFrame:

    - text
    - topics
    - matched
    - priority
    """

    df = df.copy()

    # Junta título e resumo
    df["text"] = (
        df["title"].fillna("")
        + " "
        + df["summary"].fillna("")
    )

    # Procura tópicos
    df["topics"] = df["text"].apply(find_topics)

    # Possui pelo menos um tópico?
    df["matched"] = df["topics"].apply(
        lambda x: len(x) > 0
    )

    # Maior prioridade encontrada
    def get_priority(matches):

        if not matches:
            return None

        return max(
            item["priority"]
            for item in matches
        )

    df["priority"] = df["topics"].apply(
        get_priority
    )

    # Mantém somente notícias relevantes
    df = df[df["matched"]].reset_index(drop=True)

    return df