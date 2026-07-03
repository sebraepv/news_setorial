import pandas as pd
from typing import List, Dict, Any


def create_dataframe(noticias: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Converte lista de notícias em DataFrame.
    """

    df = pd.DataFrame(noticias)
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    df["collected_at"] = pd.to_datetime(df["collected_at"], errors="coerce")
    df["mes_noticia"] = df["published_at"].dt.to_period("M").astype(str)
    df["ano_noticia"] = df["published_at"].dt.year.astype("Int64")

    return df