import pandas as pd
from typing import Dict, Optional


def calculate_recency_score(
    dataframe: pd.DataFrame,
    reference_time: Optional[pd.Timestamp] = None,
    max_age_days: int = 30,
) -> pd.Series:
    """Calcula score de recência com base na diferença em dias.

    Notícias mais recentes recebem score maior entre 0 e 1.
    """

    reference_time = reference_time or pd.Timestamp.now(tz="UTC")
    published_at = pd.to_datetime(dataframe["published_at"], errors="coerce")
    age_days = (reference_time - published_at).dt.total_seconds().div(86400).clip(lower=0)
    recency_score = (max_age_days - age_days).clip(lower=0) / max_age_days
    return recency_score.fillna(0.0)


def normalize_scores(score_series: pd.Series) -> pd.Series:
    """Normaliza uma série de scores entre 0 e 1."""

    if score_series.empty:
        return score_series

    minimum = score_series.min()
    maximum = score_series.max()
    if minimum == maximum:
        return pd.Series(1.0, index=score_series.index)

    return (score_series - minimum) / (maximum - minimum)


def combine_scores(
    recency_score: pd.Series,
    sector_confidence: pd.Series,
    source_weight: pd.Series,
    weights: Optional[Dict[str, float]] = None,
) -> pd.Series:
    """Combina recência, confiança do setor e peso da fonte em um score final."""

    weights = weights or {
        "recency": 0.5,
        "sector": 0.3,
        "source": 0.2,
    }

    normalized_recency = normalize_scores(recency_score)
    normalized_sector = normalize_scores(sector_confidence)
    normalized_source = normalize_scores(source_weight)

    return (
        normalized_recency * weights["recency"]
        + normalized_sector * weights["sector"]
        + normalized_source * weights["source"]
    )


def rank_news(
    dataframe: pd.DataFrame,
    sector_confidence_column: str = "sector_confidence",
    source_weight_column: str = "source_weight",
    recency_column: str = "recency_score",
    ranking_weights: Optional[Dict[str, float]] = None,
    reference_time: Optional[pd.Timestamp] = None,
    max_age_days: int = 30,
) -> pd.DataFrame:
    """Recebe um dataframe de notícias e retorna as notícias ordenadas por score."""

    df = dataframe.copy()
    df["recency_score"] = calculate_recency_score(
        df,
        reference_time=reference_time,
        max_age_days=max_age_days,
    )

    if sector_confidence_column not in df.columns:
        df[sector_confidence_column] = 0.0
    if source_weight_column not in df.columns:
        df[source_weight_column] = 0.0

    df["ranking_score"] = combine_scores(
        recency_score=df["recency_score"],
        sector_confidence=df[sector_confidence_column].astype(float),
        source_weight=df[source_weight_column].astype(float),
        weights=ranking_weights,
    )

    return df.sort_values(by="ranking_score", ascending=False).reset_index(drop=True)
