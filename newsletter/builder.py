import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from .prompts import (
    get_sector_prompt,
    get_newsletter_prompt,
    get_news_items_summaries_prompt,
)

from .templates import render_newsletter


class NewsletterBuilder:
    """
    Constrói uma newsletter estruturada por setor usando um modelo LLM
    via OpenAI-compatible API.

    Fluxo:
    1. Divide notícias por setor.
    2. Chama o modelo para gerar análise por setor.
    3. Seleciona top 5 notícias de cada setor.
    4. Chama o modelo para gerar resumo editorial das top notícias.
    5. Chama o modelo para gerar introdução, conclusão e refinamentos gerais.
    6. Monta uma estrutura em dict.
    7. Converte essa estrutura em HTML.
    """

    def __init__(
        self,
        api_client=None,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment_name: str | None = None,
        env_path: str | Path | None = None,
    ):
        env_path = env_path or Path(__file__).resolve().parents[1] / "variaveis.env"
        load_dotenv(env_path, override=False)

        self.client = api_client
        self.endpoint = (endpoint or os.getenv("ENDPOINT_KIMI") or "").strip()
        self.api_key = (api_key or os.getenv("KIMI_API_KEY_FOUNDRY") or "").strip()
        self.deployment_name = (
            deployment_name or os.getenv("MODEL_NAME_GPT")
        ).strip()

        self.default_sectors = [
            "agronegócio",
            "comércio",
            "indústria",
            "serviços",
        ]

        self.sector_contents: Dict[str, Dict[str, Any]] = {}
        self.newsletter_structure: Dict[str, Any] = {}

        if self.client is None and self.endpoint and self.api_key:
            self.client = OpenAI(
                base_url=self.endpoint,
                api_key=self.api_key,
            )

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _normalize_text(self, value: Any) -> str:
        """
        Normaliza texto para comparação:
        lowercase, sem acentos e sem espaços extras.
        """
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        return text

    def _safe_value(self, value: Any) -> Any:
        """
        Converte valores não serializáveis em representações seguras.
        """

        if value is None:
            return ""

        if isinstance(value, pd.Timestamp):
            return value.isoformat()

        if isinstance(value, (list, dict)):
            return value

        if isinstance(value, float) and pd.isna(value):
            return ""

        try:
            if pd.isna(value):
                return ""
        except (TypeError, ValueError):
            pass

        return value

    def _clean_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Limpa um registro para uso em JSON/HTML.
        """
        return {
            key: self._safe_value(value)
            for key, value in record.items()
        }

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Tenta extrair JSON da resposta do modelo.

        Suporta:
        - JSON puro
        - JSON dentro de ```json ... ```
        - Texto antes/depois do JSON
        - JSON com quebras de linha dentro de strings, quando possível
        """
        if not text:
            raise ValueError("Resposta vazia do modelo.")

        cleaned = text.strip()

        fenced_match = re.search(
            r"```(?:json)?\s*(.*?)```",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )

        if fenced_match:
            cleaned = fenced_match.group(1).strip()

        # 1. Tenta carregar como JSON puro
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 2. Extrai do primeiro { ao último }
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("Nenhum objeto JSON encontrado na resposta do modelo.")

        json_candidate = cleaned[start: end + 1]

        # 3. Tenta JSON padrão
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass

        # 4. Tenta decoder menos rígido
        try:
            decoder = json.JSONDecoder(strict=False)
            parsed, _ = decoder.raw_decode(json_candidate)
            return parsed
        except json.JSONDecodeError:
            raise ValueError("Não foi possível interpretar o JSON retornado pelo modelo.")

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Faz parse da resposta do modelo.

        Se não conseguir JSON, preserva o texto bruto em `texto`.
        """
        try:
            parsed = self._extract_json_from_text(response)

            if isinstance(parsed, dict):
                return parsed

            return {"texto": str(parsed)}

        except Exception:
            return {"texto": response or ""}

    def _to_list(self, value: Any) -> List[str]:
        """
        Garante que o valor seja uma lista de strings.
        """
        if value is None:
            return []

        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        if isinstance(value, str):
            value = value.strip()
            return [value] if value else []

        return []

    def _get_ordered_sectors(
        self,
        dataframe: pd.DataFrame,
        sector_column: str,
    ) -> List[str]:
        """
        Retorna setores em ordem:
        1. Setores padrão conhecidos.
        2. Demais setores encontrados no DataFrame.
        """
        existing_sectors = [
            str(value).strip()
            for value in dataframe[sector_column].dropna().unique().tolist()
            if str(value).strip()
        ]

        normalized_existing = {
            self._normalize_text(sector): sector
            for sector in existing_sectors
        }

        ordered: List[str] = []

        for sector in self.default_sectors:
            norm = self._normalize_text(sector)

            if norm in normalized_existing:
                original_name = normalized_existing[norm]

                if original_name not in ordered:
                    ordered.append(original_name)

        for sector in existing_sectors:
            if sector not in ordered:
                ordered.append(sector)

        return ordered

    # ---------------------------------------------------------------------
    # Divisão e formatação de notícias
    # ---------------------------------------------------------------------

    def split_by_sector(
        self,
        dataframe: pd.DataFrame,
        sector_column: str = "setor",
    ) -> Dict[str, pd.DataFrame]:
        """
        Divide o DataFrame em grupos por setor.
        """
        if dataframe is None or dataframe.empty:
            raise ValueError("DataFrame vazio. Não há notícias para processar.")

        if sector_column not in dataframe.columns:
            raise ValueError(f"Coluna '{sector_column}' não encontrada no DataFrame.")

        sectors_dict: Dict[str, pd.DataFrame] = {}
        ordered_sectors = self._get_ordered_sectors(dataframe, sector_column)

        for sector in ordered_sectors:
            sector_df = dataframe[
                dataframe[sector_column].astype(str).str.strip() == str(sector).strip()
            ].copy()

            if not sector_df.empty:
                if "ranking_score" in sector_df.columns:
                    sector_df = sector_df.sort_values(
                        by="ranking_score",
                        ascending=False,
                    )

                sectors_dict[sector] = sector_df.reset_index(drop=True)

        return sectors_dict

    def _format_news_for_prompt(self, sector_df: pd.DataFrame) -> str:
        """
        Formata notícias de um setor para uso no prompt setorial.
        """
        news_list = []

        for _, row in sector_df.iterrows():
            news_item = {
                "titulo": self._safe_value(row.get("title", "")),
                "resumo": self._safe_value(row.get("summary", "")),
                "url": self._safe_value(row.get("url", row.get("link", ""))),
                "fonte": self._safe_value(row.get("source", "")),
                "data": str(self._safe_value(row.get("published_at", ""))),
                "score": round(float(row.get("ranking_score", 0) or 0), 4),
            }

            news_list.append(news_item)

        return json.dumps(
            news_list,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    def _format_news_for_full_prompt(
        self,
        sectors_dict: Dict[str, pd.DataFrame],
        sector_contents: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        Formata todas as informações para o prompt principal da newsletter.
        Inclui análises setoriais e top notícias já resumidas.
        """
        payload: Dict[str, Any] = {
            "setores": {},
        }

        for sector, sector_df in sectors_dict.items():
            payload["setores"][sector] = {
                "analise_setorial": sector_contents.get(sector, {}).get("conteudo", ""),
                "destaques": sector_contents.get(sector, {}).get("destaques", []),
                "riscos": sector_contents.get(sector, {}).get("riscos", []),
                "oportunidades": sector_contents.get(sector, {}).get("oportunidades", []),
                "top_noticias": sector_contents.get(sector, {}).get("noticias", []),
                "total_noticias_setor": int(len(sector_df)),
            }

        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    def _get_news_records_for_sector(
        self,
        sector_df: pd.DataFrame,
    ) -> List[Dict[str, Any]]:
        """
        Extrai registros originais de notícias com colunas relevantes
        para auditoria/JSON.

        Não chama LLM aqui para evitar custo duplicado.
        """
        desired_columns = [
            "title",
            "summary",
            "url",
            "link",
            "source",
            "published_at",
            "ranking_score",
            "setor",
            "confianca_setor",
            "peso_fonte",
        ]

        available_columns = [
            column for column in desired_columns
            if column in sector_df.columns
        ]

        records = sector_df[available_columns].to_dict(orient="records")

        return [
            self._clean_record(record)
            for record in records
        ]

    # ---------------------------------------------------------------------
    # Chamada LLM
    # ---------------------------------------------------------------------

    def call_llm(self, prompt: str) -> str:
        """
        Chama o modelo LLM com o prompt informado.
        """
        if self.client is None:
            raise RuntimeError(
                "Cliente do modelo não inicializado. "
                "Verifique ENDPOINT_KIMI e KIMI_API_KEY_FOUNDRY no arquivo variaveis.env."
            )

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.7,
                max_tokens=2048,
            )

            return response.choices[0].message.content or ""

        except Exception as exc:
            raise RuntimeError(f"Erro ao chamar o modelo: {exc}") from exc

    # ---------------------------------------------------------------------
    # Resumo das top notícias por setor
    # ---------------------------------------------------------------------

    def summarize_top_news_for_sector(
        self,
        sector: str,
        sector_df: pd.DataFrame,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Seleciona as top N notícias do setor e gera um resumo editorial
        para cada notícia usando LLM.
        """
        if sector_df.empty:
            return []

        df_top = sector_df.copy()

        if "ranking_score" in df_top.columns:
            df_top = df_top.sort_values(
                by="ranking_score",
                ascending=False,
            )

        df_top = df_top.head(top_n).reset_index(drop=True)

        news_payload: List[Dict[str, Any]] = []

        for _, row in df_top.iterrows():
            news_payload.append(
                {
                    "title": self._safe_value(row.get("title", "")),
                    "summary": self._safe_value(row.get("summary", "")),
                    "url": self._safe_value(row.get("url", row.get("link", ""))),
                    "link": self._safe_value(row.get("link", row.get("url", ""))),
                    "source": self._safe_value(row.get("source", "")),
                    "published_at": str(self._safe_value(row.get("published_at", ""))),
                    "ranking_score": round(float(row.get("ranking_score", 0) or 0), 4),
                    "setor": sector,
                }
            )

        if not news_payload:
            return []

        news_json = json.dumps(
            news_payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        prompt = get_news_items_summaries_prompt(
            sector=sector,
            news_json=news_json,
            max_items=top_n,
        )

        try:
            raw_response = self.call_llm(prompt)
            parsed_response = self._parse_llm_response(raw_response)

            summarized_items = parsed_response.get("noticias", [])

            if not isinstance(summarized_items, list):
                summarized_items = []

        except Exception:
            summarized_items = []

        final_news: List[Dict[str, Any]] = []

        for index, original_news in enumerate(news_payload):
            summarized = summarized_items[index] if index < len(summarized_items) else {}

            newsletter_summary = ""

            if isinstance(summarized, dict):
                newsletter_summary = (
                    summarized.get("newsletter_summary")
                    or summarized.get("resumo")
                    or summarized.get("summary")
                    or ""
                )

            if not newsletter_summary:
                newsletter_summary = original_news.get("summary", "")

            final_news.append(
                {
                    "title": original_news.get("title", ""),
                    "summary": original_news.get("summary", ""),
                    "newsletter_summary": newsletter_summary,
                    "url": original_news.get("url") or original_news.get("link") or "#",
                    "link": original_news.get("link") or original_news.get("url") or "#",
                    "source": original_news.get("source", ""),
                    "published_at": original_news.get("published_at", ""),
                    "ranking_score": original_news.get("ranking_score", 0),
                    "setor": sector,
                }
            )

        return final_news

    # ---------------------------------------------------------------------
    # Processamento por setor
    # ---------------------------------------------------------------------

    def process_sector(
        self,
        sector: str,
        sector_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Processa notícias de um setor através do LLM.

        Retorna:
        - análise setorial;
        - destaques;
        - riscos;
        - oportunidades;
        - top 5 notícias com resumo editorial feito pelo LLM.
        """
        news_formatted = self._format_news_for_prompt(sector_df)
        prompt = get_sector_prompt(sector, news_formatted)

        try:
            raw_response = self.call_llm(prompt)
            parsed_response = self._parse_llm_response(raw_response)

            if not isinstance(parsed_response, dict):
                parsed_response = {"analise": raw_response}

            titulo = (
                parsed_response.get("titulo")
                or parsed_response.get("title")
                or f"Análise - {sector.capitalize()}"
            )

            analise = (
                parsed_response.get("analise")
                or parsed_response.get("conteudo")
                or parsed_response.get("summary")
                or parsed_response.get("resumo")
                or parsed_response.get("texto")
                or raw_response
                or ""
            )

            destaques = self._to_list(
                parsed_response.get("destaques")
                or parsed_response.get("principais_destaques")
                or []
            )

            riscos = self._to_list(parsed_response.get("riscos", []))
            oportunidades = self._to_list(parsed_response.get("oportunidades", []))

            erro = None

        except Exception as exc:
            titulo = f"Análise - {sector.capitalize()}"
            analise = (
                f"Não foi possível gerar análise automática para o setor {sector}. "
                "As principais notícias foram preservadas para leitura."
            )
            destaques = []
            riscos = []
            oportunidades = []
            erro = str(exc)

        noticias = self.summarize_top_news_for_sector(
            sector=sector,
            sector_df=sector_df,
            top_n=5,
        )

        return {
            "setor": sector,
            "titulo": titulo,
            "quantidade_noticias": int(len(sector_df)),
            "conteudo": analise,
            "destaques": destaques,
            "riscos": riscos,
            "oportunidades": oportunidades,
            "noticias": noticias,
            "erro": erro,
        }

    # ---------------------------------------------------------------------
    # Construção da estrutura
    # ---------------------------------------------------------------------

    def build_newsletter(
        self,
        dataframe: pd.DataFrame,
        sector_column: str = "setor",
        include_intro: bool = True,
        include_closing: bool = True,
    ) -> Dict[str, Any]:
        """
        Constrói a estrutura completa da newsletter.

        Retorna um dict estruturado com:
        - metadata;
        - introducao;
        - setores;
        - conclusao;
        - originais_por_setor.
        """
        sectors_dict = self.split_by_sector(
            dataframe=dataframe,
            sector_column=sector_column,
        )

        if not sectors_dict:
            raise ValueError("Nenhuma notícia encontrada para processar.")

        self.sector_contents = {}

        for sector, sector_df in sectors_dict.items():
            self.sector_contents[sector] = self.process_sector(
                sector=sector,
                sector_df=sector_df,
            )

        self.newsletter_structure = {
            "metadata": {
                "data_geracao": pd.Timestamp.now().isoformat(),
                "total_noticias": int(len(dataframe)),
                "setores_cobertos": list(sectors_dict.keys()),
            },
            "conteudo": {
                "introducao": "",
                "setores": self.sector_contents,
                "principais_tendencias": [],
                "oportunidades": [],
                "riscos": [],
                "conclusao": "",
                "originais_por_setor": {
                    sector: self._get_news_records_for_sector(sector_df)
                    for sector, sector_df in sectors_dict.items()
                },
            },
        }

        try:
            full_news_json = self._format_news_for_full_prompt(
                sectors_dict=sectors_dict,
                sector_contents=self.sector_contents,
            )

            full_prompt = get_newsletter_prompt(full_news_json)
            raw_response = self.call_llm(full_prompt)
            generated_content = self._parse_llm_response(raw_response)

            introducao = (
                generated_content.get("introducao")
                or generated_content.get("intro")
                or generated_content.get("abertura")
                or ""
            )

            conclusao = (
                generated_content.get("conclusao")
                or generated_content.get("encerramento")
                or generated_content.get("fechamento")
                or ""
            )

            generated_sectors = generated_content.get("setores", {})

            if include_intro:
                self.newsletter_structure["conteudo"]["introducao"] = introducao

            if include_closing:
                self.newsletter_structure["conteudo"]["conclusao"] = conclusao

            self.newsletter_structure["conteudo"]["principais_tendencias"] = self._to_list(
                generated_content.get("principais_tendencias", [])
            )

            self.newsletter_structure["conteudo"]["oportunidades"] = self._to_list(
                generated_content.get("oportunidades", [])
            )

            self.newsletter_structure["conteudo"]["riscos"] = self._to_list(
                generated_content.get("riscos", [])
            )

            if isinstance(generated_sectors, dict) and generated_sectors:
                self._merge_generated_sectors(generated_sectors)

            self.newsletter_structure["conteudo"]["modelo_resposta_bruta"] = raw_response

        except Exception as exc:
            self.newsletter_structure["conteudo"]["erro"] = str(exc)

        return self.newsletter_structure

    def _merge_generated_sectors(
        self,
        generated_sectors: Dict[str, Any],
    ) -> None:
        """
        Mescla o conteúdo setorial retornado pelo prompt principal
        com o conteúdo já gerado por get_sector_prompt().

        Importante:
        - Não sobrescreve as top notícias já resumidas.
        - Atualiza apenas título, análise, destaques, riscos e oportunidades.
        """
        current_sectors = self.newsletter_structure["conteudo"].get("setores", {})

        normalized_current = {
            self._normalize_text(sector): sector
            for sector in current_sectors.keys()
        }

        for generated_sector_name, generated_data in generated_sectors.items():
            normalized_name = self._normalize_text(generated_sector_name)

            original_sector_name = normalized_current.get(
                normalized_name,
                generated_sector_name,
            )

            if original_sector_name not in current_sectors:
                current_sectors[original_sector_name] = {
                    "setor": original_sector_name,
                    "titulo": f"Análise - {str(original_sector_name).capitalize()}",
                    "quantidade_noticias": 0,
                    "conteudo": "",
                    "destaques": [],
                    "riscos": [],
                    "oportunidades": [],
                    "noticias": [],
                    "erro": None,
                }

            if isinstance(generated_data, dict):
                generated_title = (
                    generated_data.get("titulo")
                    or generated_data.get("title")
                    or ""
                )

                generated_analysis = (
                    generated_data.get("analise")
                    or generated_data.get("conteudo")
                    or generated_data.get("summary")
                    or generated_data.get("resumo")
                    or ""
                )

                generated_highlights = self._to_list(
                    generated_data.get("destaques")
                    or generated_data.get("principais_destaques")
                    or []
                )

                generated_risks = self._to_list(generated_data.get("riscos", []))
                generated_opportunities = self._to_list(
                    generated_data.get("oportunidades", [])
                )

                if generated_title:
                    current_sectors[original_sector_name]["titulo"] = generated_title

                if generated_analysis:
                    current_sectors[original_sector_name]["conteudo"] = generated_analysis

                if generated_highlights:
                    current_sectors[original_sector_name]["destaques"] = generated_highlights

                if generated_risks:
                    current_sectors[original_sector_name]["riscos"] = generated_risks

                if generated_opportunities:
                    current_sectors[original_sector_name]["oportunidades"] = generated_opportunities

            elif isinstance(generated_data, str):
                current_sectors[original_sector_name]["conteudo"] = generated_data

        self.newsletter_structure["conteudo"]["setores"] = current_sectors

    # ---------------------------------------------------------------------
    # HTML
    # ---------------------------------------------------------------------

    def build_newsletter_html(
        self,
        dataframe: pd.DataFrame,
        sector_column: str = "setor",
        title: str | None = None,
        include_intro: bool = True,
        include_closing: bool = True,
        include_observatory_cta: bool = True,
        observatory_url: str = "https://www.sebrae-sc.com.br/observatorio",

    ) -> str:
        """
        Constrói a newsletter em HTML.

        Retorna uma string HTML pronta para salvar em arquivo ou enviar por e-mail.
        """
        newsletter_structure = self.build_newsletter(
            dataframe=dataframe,
            sector_column=sector_column,
            include_intro=include_intro,
            include_closing=include_closing,
        )

        conteudo = newsletter_structure.get("conteudo", {})
        setores = conteudo.get("setores", {})

        news_list: List[Dict[str, Any]] = []

        introducao = conteudo.get("introducao")

        if include_intro and introducao:
            news_list.append(
                {
                    "title": "Introdução",
                    "summary": introducao,
                    "source": "Newsletter",
                    "published_at": "",
                    "url": "#",
                }
            )

        principais_tendencias = conteudo.get("principais_tendencias", [])

        if principais_tendencias:
            news_list.append(
                {
                    "title": "Principais tendências",
                    "summary": "\n".join(f"• {item}" for item in principais_tendencias),
                    "source": "Newsletter",
                    "published_at": "",
                    "url": "#",
                }
            )

        oportunidades_gerais = conteudo.get("oportunidades", [])

        if oportunidades_gerais:
            news_list.append(
                {
                    "title": "Oportunidades gerais",
                    "summary": "\n".join(f"• {item}" for item in oportunidades_gerais),
                    "source": "Newsletter",
                    "published_at": "",
                    "url": "#",
                }
            )

        riscos_gerais = conteudo.get("riscos", [])

        if riscos_gerais:
            news_list.append(
                {
                    "title": "Riscos gerais",
                    "summary": "\n".join(f"• {item}" for item in riscos_gerais),
                    "source": "Newsletter",
                    "published_at": "",
                    "url": "#",
                }
            )

        for setor, setor_data in setores.items():
            if not isinstance(setor_data, dict):
                continue

            titulo_setor = (
                setor_data.get("titulo")
                or f"Análise - {str(setor).capitalize()}"
            )

            analise = setor_data.get("conteudo", "")
            destaques = setor_data.get("destaques", [])
            oportunidades = setor_data.get("oportunidades", [])
            riscos = setor_data.get("riscos", [])
            noticias = setor_data.get("noticias", [])

            # 1. Bloco de análise setorial
            if analise:
                news_list.append(
                    {
                        "title": titulo_setor,
                        "summary": analise,
                        "source": "Análise setorial",
                        "published_at": "",
                        "url": "#",
                        "setor": setor,
                    }
                )

            # 2. Destaques do setor
            if destaques:
                news_list.append(
                    {
                        "title": f"Destaques - {str(setor).capitalize()}",
                        "summary": "\n".join(f"• {item}" for item in destaques),
                        "source": "Análise setorial",
                        "published_at": "",
                        "url": "#",
                        "setor": setor,
                    }
                )

            # 3. Oportunidades do setor
            if oportunidades:
                news_list.append(
                    {
                        "title": f"Oportunidades - {str(setor).capitalize()}",
                        "summary": "\n".join(f"• {item}" for item in oportunidades),
                        "source": "Análise setorial",
                        "published_at": "",
                        "url": "#",
                        "setor": setor,
                    }
                )

            # 4. Riscos do setor
            if riscos:
                news_list.append(
                    {
                        "title": f"Riscos - {str(setor).capitalize()}",
                        "summary": "\n".join(f"• {item}" for item in riscos),
                        "source": "Análise setorial",
                        "published_at": "",
                        "url": "#",
                        "setor": setor,
                    }
                )

            # 5. Top 5 notícias resumidas pelo LLM
            for noticia in noticias[:5]:
                if not isinstance(noticia, dict):
                    continue

                title_value = (
                    noticia.get("title")
                    or noticia.get("titulo")
                    or "Notícia sem título"
                )

                summary_value = (
                    noticia.get("newsletter_summary")
                    or noticia.get("summary")
                    or noticia.get("resumo")
                    or ""
                )

                news_list.append(
                    {
                        "title": title_value,
                        "summary": summary_value,
                        "source": noticia.get("source") or noticia.get("fonte") or "",
                        "published_at": noticia.get("published_at") or noticia.get("data") or "",
                        "url": noticia.get("url") or noticia.get("link") or "#",
                        "link": noticia.get("link") or noticia.get("url") or "#",
                        "setor": setor,
                    }
                )
                        
        ## CTA Observatório de Negócios do Sebrae/SC
        if include_observatory_cta:
            news_list.append(
                {
                    "title": "Quer saber mais sobre inteligência nos pequenos negócios?",
                    "summary": (
                        "Acesse o Portal do Observatório de Negócios do Sebrae "
                        "e acompanhe estudos, dados, tendências e conteúdos estratégicos "
                        "para apoiar a tomada de decisão."
                    ),
                    "source": "",
                    "published_at": "",
                    "url": observatory_url,
                }
            )


        conclusao = conteudo.get("conclusao")

        if include_closing and conclusao:
            news_list.append(
                {
                    "title": "Encerramento",
                    "summary": conclusao,
                    "source": "Newsletter",
                    "published_at": "",
                    "url": "#",
                }
            )

        if not news_list:
            news_list.append(
                {
                    "title": "Newsletter sem conteúdo gerado",
                    "summary": (
                        "Nenhuma notícia foi adicionada ao HTML. "
                        "Verifique se o DataFrame possui as colunas esperadas: "
                        "title, summary, url, source, published_at, setor e ranking_score."
                    ),
                    "source": "Sistema",
                    "published_at": "",
                    "url": "#",
                }
            )

        newsletter_title = title or self._get_default_newsletter_title()

        return render_newsletter(
            title=newsletter_title,
            news_list=news_list,
        )

    ## Construir newsletter por setor em arquivos separados
    def _slugify_filename(self, value: str) -> str:
        """
        Gera um nome seguro para arquivo a partir do nome do setor.
        Exemplo: 'agronegócio' -> 'agronegocio'
        """
        text = self._normalize_text(value)
        text = text.replace(" ", "_")
        text = re.sub(r"[^a-z0-9_\\-]", "", text)
        return text or "setor"


    def _build_news_list_for_sector(
        self,
        setor: str,
        setor_data: Dict[str, Any],
        include_cta: bool = True,
        observatory_url: str = "https://observatorio.sebrae-sc.com.br",
        include_intro: bool = True,
        include_closing: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Monta a lista de blocos/notícias para uma newsletter específica de um setor.
        """

        news_list: List[Dict[str, Any]] = []

        titulo_setor = (
            setor_data.get("titulo")
            or f"Análise - {str(setor).capitalize()}"
        )
        introducao = setor_data.get("introducao", "")
        analise = setor_data.get("conteudo", "")
        destaques = setor_data.get("destaques", [])
        oportunidades = setor_data.get("oportunidades", [])
        riscos = setor_data.get("riscos", [])
        noticias = setor_data.get("noticias", [])
        conclusao = setor_data.get("conclusao", "")

        #Introdução do Setor
        if include_intro and introducao:
            news_list.append(
                {
                    "title": f"Introdução - {str(setor).capitalize()}",
                    "summary": introducao,
                    "source": "Análise setorial",
                    "published_at": "",
                    "url": "#",
                    "setor": setor,
                }
            )

        # 1. Análise setorial
        if analise:
            news_list.append(
                {
                    "title": titulo_setor,
                    "summary": analise,
                    "source": "Análise setorial",
                    "published_at": "",
                    "url": "#",
                    "setor": setor,
                }
            )

        # 2. Destaques
        if destaques:
            news_list.append(
                {
                    "title": f"Destaques - {str(setor).capitalize()}",
                    "summary": "\n".join(f"• {item}" for item in destaques),
                    "source": "Análise setorial",
                    "published_at": "",
                    "url": "#",
                    "setor": setor,
                }
            )

        # 3. Oportunidades
        if oportunidades:
            news_list.append(
                {
                    "title": f"Oportunidades - {str(setor).capitalize()}",
                    "summary": "\n".join(f"• {item}" for item in oportunidades),
                    "source": "Análise setorial",
                    "published_at": "",
                    "url": "#",
                    "setor": setor,
                }
            )

        # 4. Riscos
        if riscos:
            news_list.append(
                {
                    "title": f"Riscos - {str(setor).capitalize()}",
                    "summary": "\n".join(f"• {item}" for item in riscos),
                    "source": "Análise setorial",
                    "published_at": "",
                    "url": "#",
                    "setor": setor,
                }
            )

        # 5. Top 5 notícias do setor com resumo feito pelo LLM
        for noticia in noticias[:5]:
            if not isinstance(noticia, dict):
                continue

            title_value = (
                noticia.get("title")
                or noticia.get("titulo")
                or "Notícia sem título"
            )

            summary_value = (
                noticia.get("newsletter_summary")
                or noticia.get("summary")
                or noticia.get("resumo")
                or ""
            )

            news_list.append(
                {
                    "title": title_value,
                    "summary": summary_value,
                    "source": noticia.get("source") or noticia.get("fonte") or "",
                    "published_at": noticia.get("published_at") or noticia.get("data") or "",
                    "url": noticia.get("url") or noticia.get("link") or "#",
                    "link": noticia.get("link") or noticia.get("url") or "#",
                    "setor": setor,
                }
            )

        # 6. CTA institucional
        if include_cta:
            news_list.append(
                {
                    "title": "Quer saber mais sobre inteligência nos pequenos negócios?",
                    "summary": (
                        "Acesse o Portal do Observatório de Negócios do Sebrae "
                        "e acompanhe estudos, dados, tendências e conteúdos estratégicos "
                        "para apoiar a tomada de decisão."
                    ),
                    "source": "Sebrae/SC",
                    "published_at": "",
                    "url": observatory_url,
                    "setor": setor,
                }
            )

        # Conclusão do setor
        if include_closing and conclusao:
            news_list.append(
                {
                    "title": f"Conclusão - {str(setor).capitalize()}",
                    "summary": conclusao,
                    "source": "Análise setorial",
                    "published_at": "",
                    "url": "#",
                    "setor": setor,
                }
            )

        if not news_list:
            news_list.append(
                {
                    "title": f"Newsletter de {str(setor).capitalize()} sem conteúdo",
                    "summary": (
                        "Nenhuma notícia foi encontrada para este setor. "
                        "Verifique os dados classificados e os filtros aplicados."
                    ),
                    "source": "Sistema",
                    "published_at": "",
                    "url": "#",
                    "setor": setor,
                }
            )

        return news_list


    def build_sector_newsletter_html(
        self,
        setor: str,
        title: str | None = None,
        include_cta: bool = True,
        observatory_url: str = "https://sebrae-sc.com.br/observatorio",
    ) -> str:
        """
        Constrói uma newsletter HTML para um setor específico
        usando a estrutura já gerada por build_newsletter().
        """

        if not self.newsletter_structure:
            raise ValueError(
                "Newsletter ainda não foi construída. "
                "Execute build_newsletter() antes de gerar HTML por setor."
            )

        conteudo = self.newsletter_structure.get("conteudo", {})
        setores = conteudo.get("setores", {})

        if setor not in setores:
            setores_disponiveis = ", ".join(setores.keys())
            raise ValueError(
                f"Setor '{setor}' não encontrado na estrutura da newsletter. "
                f"Setores disponíveis: {setores_disponiveis}"
            )

        setor_data = setores[setor]

        news_list = self._build_news_list_for_sector(
            setor=setor,
            setor_data=setor_data,
            include_cta=include_cta,
            observatory_url=observatory_url,
        )

        newsletter_title = f"{title} - {str(setor).capitalize()}"

        return render_newsletter(
            title=newsletter_title,
            news_list=news_list,
        )


    def build_all_sector_newsletters_html(
        self,
        dataframe: pd.DataFrame,
        sector_column: str = "setor",
        title_prefix: str | None = None,
        include_cta: bool = True,
        observatory_url: str = "https://www.sebrae-sc.com.br/observatorio",
        include_intro: bool = True,
        include_closing: bool = True,
    ) -> Dict[str, str]:
        """
        Constrói uma newsletter HTML para cada setor encontrado no DataFrame.

        Retorna:
        {
            "agronegócio": "<html>...</html>",
            "comércio": "<html>...</html>",
            ...
        }
        """

        self.build_newsletter(
            dataframe=dataframe,
            sector_column=sector_column,
            include_intro=include_intro,
            include_closing=include_closing,
        )

        conteudo = self.newsletter_structure.get("conteudo", {})
        setores = conteudo.get("setores", {})

        newsletters_by_sector: Dict[str, str] = {}

        for setor, setor_data in setores.items():
            news_list = self._build_news_list_for_sector(
                setor=setor,
                setor_data=setor_data,
                include_cta=include_cta,
                observatory_url=observatory_url,
                include_intro=include_intro,
                include_closing=include_closing,
            )

            sector_title = f"{title_prefix} - {str(setor).capitalize()}"

            newsletters_by_sector[setor] = render_newsletter(
                title=sector_title,
                news_list=news_list,
            )

        return newsletters_by_sector

    def _get_default_newsletter_title(self) -> str:
        """
        Gera título padrão da newsletter.
        """
        data_atual = pd.Timestamp.now().strftime("%d/%m/%Y")
        return f"Newsletter Setorial - {data_atual}"

    def get_newsletter_structure(self) -> Dict[str, Any]:
        """
        Retorna a estrutura da newsletter já construída.
        """
        return self.newsletter_structure