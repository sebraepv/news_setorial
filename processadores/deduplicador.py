import pandas as pd


def deduplicate_news(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove notícias duplicadas em um DataFrame com base no campo "id".

    Mantém a primeira ocorrência de cada notícia e descarta linhas sem ID.
    """
    if "id" not in df.columns:
        return df.copy()

    return (
        df.dropna(subset=["id"])
          .drop_duplicates(subset=["id"], keep="first")
          .reset_index(drop=True)
    )