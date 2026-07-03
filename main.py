import pandas as pd

from coletor.rss_feed import collect_all_news

from processadores.dataframe_news import create_dataframe
from processadores.deduplicador import deduplicate_news
from processadores.filter_keywords import filter_keywords
from processadores.json_news import salvar_json
from processadores.classificador_ml import ClassificadorML
from processadores.ranking_news import rank_news
from processadores.select_newsletter import select_newsletter_candidates

from newsletter.builder import NewsletterBuilder
from newsletter.sender import NewsletterSender
from newsletter.templates import save_newsletter_to_file


def main():
    # --------------------------------------------------
    # 1. Coleta das notícias
    # --------------------------------------------------
    news = collect_all_news("config/feeds.json")
    total_coletadas = len(news)

    print(f"Total de notícias coletadas: {total_coletadas}")

    # --------------------------------------------------
    # 2. Criação do DataFrame
    # --------------------------------------------------
    df = create_dataframe(news)

    # --------------------------------------------------
    # 3. Deduplicação e filtro inicial
    # --------------------------------------------------
    df = deduplicate_news(df)
    df = filter_keywords(df)

    total_apos_filtros = len(df)

    print(f"Total após deduplicação e filtro por palavras-chave: {total_apos_filtros}")

    if df.empty:
        print("Nenhuma notícia encontrada após os filtros iniciais.")
        return

    # --------------------------------------------------
    # 4. Classificação das notícias
    # --------------------------------------------------
    classificador_ml = ClassificadorML()

    registros = df.to_dict(orient="records")
    registros_classificados = []

    for noticia in registros:
        noticia_classificada = classificador_ml.classificar_noticia(noticia)
        registros_classificados.append(noticia_classificada)

    df = pd.DataFrame(registros_classificados)

    if df.empty:
        print("Nenhuma notícia classificada.")
        return

    # --------------------------------------------------
    # 5. Remover setores irrelevantes antes do ranking
    # --------------------------------------------------
    if "setor" not in df.columns:
        raise ValueError("Coluna 'setor' não encontrada após classificação.")

    setores_excluidos = ["não se aplica", "outros"]
    df = df[~df["setor"].isin(setores_excluidos)].copy()

    if df.empty:
        print("Nenhuma notícia relevante após remoção de setores excluídos.")
        return

    # --------------------------------------------------
    # 6. Ranking das notícias
    # --------------------------------------------------
    ranking_weights = {
        "recency": 0.5,
        "sector": 0.3,
        "source": 0.2,
    }

    df = rank_news(
        df,
        sector_confidence_column="confianca_setor",
        source_weight_column="peso_fonte",
        ranking_weights=ranking_weights,
    )

    # --------------------------------------------------
    # 7. Seleção das candidatas para newsletter
    # --------------------------------------------------
    df_newsletter = select_newsletter_candidates(
        df,
        top_n_per_sector=5,
        min_ranking_score=0.0,
        sector_confidence_column="confianca_setor",
        source_weight_column="peso_fonte",
        ranking_weights=ranking_weights,
    )

    if df_newsletter.empty:
        print("Nenhuma notícia selecionada para a newsletter.")
        return

    # --------------------------------------------------
    # 8. Gerar newsletter em HTML
    # --------------------------------------------------

    newsletter_builder = NewsletterBuilder()


    newsletters_by_sector = newsletter_builder.build_all_sector_newsletters_html(
        dataframe=df_newsletter,
        sector_column="setor",
        title_prefix="Radar Setorial do Observatório de Negócios",
        include_cta=True,
        observatory_url="https://sebrae-sc.com.br/observatorio",
    )

    for setor, html_content in newsletters_by_sector.items():
        filename = f"newsletter_{newsletter_builder._slugify_filename(setor)}.html"

        save_newsletter_to_file(
            html_content=html_content,
            filename=filename,
        )

        print(f"Newsletter salva: {filename}")


    # Recupera também a estrutura em dict criada internamente
    newsletter_structure = newsletter_builder.get_newsletter_structure()

    # --------------------------------------------------
    # 9. Salvar saídas locais
    # --------------------------------------------------

    # Salva DataFrame enriquecido
    df_newsletter.to_csv(
        "noticias_processadas.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Salva JSON estruturado das notícias
    salvar_json(df_newsletter, usar_timestamp=True)


    # Salvar também estrutura da newsletter como JSON
    import json

    with open("newsletter_structure.json", "w", encoding="utf-8") as file:
        json.dump(
            newsletter_structure,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    # # --------------------------------------------------
    # # 10. Envio por e-mail
    # # --------------------------------------------------
    # try:
    #     sender = NewsletterSender()
    #     sender.send_newsletter_html(
    #         subject="Newsletter Observatório de Negócios",
    #         html_content=newsletters_by_sector,
    #     )
    #     print("Newsletter enviada por e-mail com sucesso.")
    # except Exception as exc:
    #     print(f"Falha ao enviar a newsletter por e-mail: {exc}")

    # --------------------------------------------------
    # 11. Logs finais
    # --------------------------------------------------
    print("Pipeline finalizado com sucesso.")
    print(f"Total coletadas: {total_coletadas}")
    print(f"Após filtros iniciais: {total_apos_filtros}")
    print(f"Selecionadas para newsletter: {len(df_newsletter)}")

    print("Distribuição por setor:")
    print(df_newsletter["setor"].value_counts())

    print("Prévia das notícias selecionadas:")
    print(
        df_newsletter[
            [
                "title",
                "setor",
                "confianca_setor",
                "ranking_score",
            ]
        ].head()
    )


if __name__ == "__main__":
    main()