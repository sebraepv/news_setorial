from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import re
import html as _html
import hashlib
import json

import feedparser


def load_feeds(config_path: str = "config/feeds.json") -> List[Dict[str, Any]]:
    """
    Carrega os feeds RSS a partir de um arquivo feeds.json.
    Retorna apenas os feeds ativos.
    """

    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    feeds = data.get("feeds", [])

    if not isinstance(feeds, list):
        raise ValueError("O arquivo feeds.json deve conter uma chave 'feeds' com uma lista de feeds.")

    active_feeds = [
        feed for feed in feeds
        if feed.get("ativo") is True
    ]

    validate_feeds(active_feeds)

    return active_feeds


def validate_feeds(feeds: List[Dict[str, Any]]) -> None:
    """
    Valida se os feeds possuem os campos obrigatórios.
    Também verifica IDs duplicados.
    """

    required_fields = [
        "id",
        "nome",
        "url",
        "categoria_base",
        "temas",
        "pais",
        "idioma",
        "ativo",
        "peso_fonte"
    ]

    seen_ids = set()

    for feed in feeds:
        for field in required_fields:
            if field not in feed:
                raise ValueError(
                    f"Feed inválido. Campo obrigatório ausente: '{field}'. "
                    f"Feed: {feed}"
                )

        feed_id = feed["id"]

        if feed_id in seen_ids:
            raise ValueError(f"ID duplicado encontrado no feeds.json: {feed_id}")

        seen_ids.add(feed_id)

        if not isinstance(feed["temas"], list):
            raise ValueError(f"O campo 'temas' deve ser uma lista no feed: {feed_id}")

        if not isinstance(feed["peso_fonte"], (int, float)):
            raise ValueError(f"O campo 'peso_fonte' deve ser numérico no feed: {feed_id}")

        if not 0 <= feed["peso_fonte"] <= 1:
            raise ValueError(f"O campo 'peso_fonte' deve estar entre 0 e 1 no feed: {feed_id}")


def generate_hash(title: str, published_at: Optional[datetime], source_id: str, link: str = "") -> str:
    """
    Cria um ID único para cada notícia usando fonte, título, data e link.
    """

    text = (
        f"{source_id}|"
        f"{title.strip().lower()}|"
        f"{published_at}|"
        f"{link.strip().lower()}"
    )

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_publication_date(entry) -> Optional[datetime]:
    """
    Converte a data do RSS para datetime UTC.
    """

    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

    if getattr(entry, "updated_parsed", None):
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

    return None


def get_entry_summary(entry) -> str:
    """
    Extrai resumo/descrição do item RSS.
    """
    raw = entry.get("summary", entry.get("description", "")) or ""

    # Remove conteúdo de tags que não são texto (ex: <script>, <style>)
    raw = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', '', raw)

    # Remove todas as tags HTML/XML
    text = re.sub(r'<[^>]+>', '', raw)

    # Remove palavras como "Leia mais", "Continue lendo", "Clique aqui", etc. e "Foto: [nome do fotógrafo]"
    text = re.sub(r'(?i)(Leia mais|Continue lendo|Clique aqui|Foto: [^<]+)', '', text)

    # Unescape entidades HTML e normalize espaços
    text = _html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def get_feed_news(feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Coleta notícias de um feed RSS usando a configuração vinda do feeds.json.
    """

    source_id = feed_config["id"]
    source_name = feed_config["nome"]
    feed_url = feed_config["url"]

    feed = feedparser.parse(feed_url)

    if getattr(feed, "bozo", False):
        print(f"[WARN] Feed possivelmente inválido: {source_name} ({feed_url})")

    if hasattr(feed, "status") and feed.status != 200:
        print(f"[WARN] HTTP {feed.status} para {source_name} ({feed_url})")

    news = []

    for entry in feed.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        summary = get_entry_summary(entry)
        published_at = parse_publication_date(entry)

        item = {
            "id": generate_hash(
                title=title,
                published_at=published_at,
                source_id=source_id,
                link=link
            ),

            # Dados da fonte
            "source_id": source_id,
            "source": source_name,
            "feed_url": feed_url,

            # Metadados de curadoria vindos do feeds.json
            "categoria_base": feed_config.get("categoria_base"),
            # "temas_fonte": feed_config.get("temas", []),
            "pais": feed_config.get("pais"),
            "idioma": feed_config.get("idioma"),
            "peso_fonte": feed_config.get("peso_fonte", 0.5),

            # Dados da notícia
            "title": title,
            "link": link,
            "summary": summary,
            "published_at": published_at,
            "collected_at": datetime.now(timezone.utc),

            # # Campos futuros para o pipeline
            # "categoria_classificada": None,
            # "relevancia": None,
            # "status_processamento": "coletado"
        }

        news.append(item)

    return news


def collect_all_news(config_path: str = "config/feeds.json") -> List[Dict[str, Any]]:
    """
    Coleta notícias de todos os feeds ativos no feeds.json.
    """

    feeds = load_feeds(config_path)

    all_news: List[Dict[str, Any]] = []

    for feed_config in feeds:
        source_name = feed_config["nome"]

        try:
            news = get_feed_news(feed_config)

            all_news.extend(news)

            print(f"[OK] {source_name}: {len(news)} notícias")

        except Exception as e:
            print(f"[ERRO] {source_name}: {e}")

    all_news.sort(
        key=lambda x: x["published_at"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )

    return all_news