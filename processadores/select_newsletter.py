import pandas as pd
from typing import Dict, List, Optional

from .ranking_news import rank_news


def select_top_news(
    ranked_dataframe: pd.DataFrame,
    top_n: int = 10,
    min_ranking_score: float = 0.0,
    ranking_score_column: str = "ranking_score",
) -> pd.DataFrame:
    """Seleciona as principais notícias a partir de um DataFrame já ranqueado."""

    if ranking_score_column not in ranked_dataframe.columns:
        raise ValueError(
            f"Coluna de pontuação '{ranking_score_column}' não encontrada no DataFrame"
        )

    selected = ranked_dataframe.copy()
    selected = selected[selected[ranking_score_column] >= min_ranking_score]
    selected = selected.sort_values(by=ranking_score_column, ascending=False)

    return selected.head(top_n).reset_index(drop=True)


def select_top_news_by_sector(
    ranked_dataframe: pd.DataFrame,
    sector_column: str = "setor",
    sectors: Optional[List[str]] = None,
    top_n_per_sector: int = 5,
    min_ranking_score: float = 0.0,
    ranking_score_column: str = "ranking_score",
) -> pd.DataFrame:
    """Seleciona os top N de cada setor a partir de um DataFrame já ranqueado."""

    if ranking_score_column not in ranked_dataframe.columns:
        raise ValueError(
            f"Coluna de pontuação '{ranking_score_column}' não encontrada no DataFrame"
        )

    if sector_column not in ranked_dataframe.columns:
        raise ValueError(f"Coluna de setor '{sector_column}' não encontrada no DataFrame")

    selected = ranked_dataframe.copy()
    selected = selected[selected[ranking_score_column] >= min_ranking_score]
    selected = selected.sort_values(by=[sector_column, ranking_score_column], ascending=[True, False])

    if sectors is None:
        sectors = selected[sector_column].dropna().unique().tolist()

    grouped = (
        selected[selected[sector_column].isin(sectors)]
        .groupby(sector_column, group_keys=False)
        .head(top_n_per_sector)
    )

    return grouped.sort_values(by=[ranking_score_column, sector_column], ascending=[False, True]).reset_index(drop=True)


def select_newsletter_candidates(
    dataframe: pd.DataFrame,
    top_n_per_sector: int = 5,
    min_ranking_score: float = 0.0,
    ranking_weights: Optional[Dict[str, float]] = None,
    sector_confidence_column: str = "sector_confidence",
    source_weight_column: str = "source_weight",
    sector_column: str = "setor",
    sectors: Optional[List[str]] = None,
    reference_time: Optional[pd.Timestamp] = None,
    max_age_days: int = 30,
) -> pd.DataFrame:
    """Ranqueia as notícias e retorna as melhores candidatas para newsletter."""

    if sectors is None:
        sectors = ["agronegócio", "comércio", "indústria", "serviço"]

    ranked_df = rank_news(
        dataframe,
        sector_confidence_column=sector_confidence_column,
        source_weight_column=source_weight_column,
        ranking_weights=ranking_weights,
        reference_time=reference_time,
        max_age_days=max_age_days,
    )

    return select_top_news_by_sector(
        ranked_dataframe=ranked_df,
        sector_column=sector_column,
        sectors=sectors,
        top_n_per_sector=top_n_per_sector,
        min_ranking_score=min_ranking_score,
    )
