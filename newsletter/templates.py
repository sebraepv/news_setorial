from typing import List, Dict, Any
from html import escape
from datetime import datetime
import os

import pandas as pd


# -----------------------------------------
# Constantes visuais
# -----------------------------------------

SEBRAE_BLUE = "#005EB8"
SEBRAE_DARK_BLUE = "#003F7D"
SEBRAE_LIGHT_BLUE = "#EAF4FF"
SEBRAE_GREEN = "#78BE20"
SEBRAE_TEXT = "#263238"
SEBRAE_MUTED = "#6B7280"
SEBRAE_BORDER = "#E5E7EB"
SEBRAE_BACKGROUND = "#F3F6FA"


# -----------------------------------------
# Helpers de HTML
# -----------------------------------------

def escape_html(text: Any) -> str:
    """Escapa caracteres HTML de forma segura."""
    if text is None:
        return ""

    return escape(str(text), quote=True)


def format_published_at(value: Any) -> str:
    """
    Formata published_at considerando dia, mês por extenso e ano.

    Exemplos:
    - 2026-06-30 -> 30 de junho de 2026
    - 2026-06-30 10:30:00 -> 30 de junho de 2026
    """

    if value is None or value == "":
        return ""

    month_names = {
        1: "janeiro",
        2: "fevereiro",
        3: "março",
        4: "abril",
        5: "maio",
        6: "junho",
        7: "julho",
        8: "agosto",
        9: "setembro",
        10: "outubro",
        11: "novembro",
        12: "dezembro",
    }

    try:
        parsed_date = pd.to_datetime(value, errors="coerce")

        if pd.isna(parsed_date):
            return escape_html(value)

        day = parsed_date.day
        month = month_names.get(parsed_date.month, "")
        year = parsed_date.year

        return f"{day} de {month} de {year}"

    except Exception:
        return escape_html(value)


def get_news_url(news: Dict) -> str:
    """Obtém a URL da notícia com fallback para link."""
    url = news.get("url") or news.get("link") or "#"
    return escape_html(url)


def render_text_block(text: Any) -> str:
    """
    Renderiza texto preservando quebras de linha simples como <br/>.
    Útil para análises geradas por LLM.
    """
    safe_text = escape_html(text)

    return safe_text.replace("\n", "<br/>")


# -----------------------------------------
# Componentes visuais
# -----------------------------------------

def render_preheader() -> str:
    """Texto invisível usado por clientes de e-mail como prévia."""
    return """
    <div style="display:none; max-height:0; overflow:hidden; opacity:0; color:transparent;">
        Principais notícias e análises setoriais selecionadas para apoiar decisões de negócios.
    </div>
    """


def render_header(title: str) -> str:
    """Renderiza cabeçalho visual da newsletter."""

    return f"""
    <tr>
        <td style="padding:0;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                <tr>
                    <td style="background:{SEBRAE_BLUE}; padding:22px 28px; border-radius:12px 12px 0 0;">
                        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                            <tr>
                                <td align="left">
                                    <div style="font-size:13px; color:#ffffff; font-weight:bold; letter-spacing:0.5px;">
                                        SEBRAE/SC
                                    </div>
                                    <div style="font-size:11px; color:#DDEEFF; margin-top:3px;">
                                        Observatório de Negócios
                                    </div>
                                </td>
                                <td align="right">
                                    <span style="
                                        display:inline-block;
                                        background:{SEBRAE_GREEN};
                                        color:#ffffff;
                                        font-size:11px;
                                        font-weight:bold;
                                        padding:6px 10px;
                                        border-radius:999px;
                                    ">
                                        Newsletter Setorial
                                    </span>
                                </td>
                            </tr>
                        </table>

                        <h1 style="
                            margin:22px 0 0 0;
                            font-size:26px;
                            line-height:32px;
                            color:#ffffff;
                            font-family:Arial, sans-serif;
                        ">
                            {escape_html(title)}
                        </h1>

                        <p style="
                            margin:10px 0 0 0;
                            font-size:14px;
                            line-height:20px;
                            color:#EAF4FF;
                            font-family:Arial, sans-serif;
                        ">
                            Curadoria de notícias, tendências e impactos para pequenos negócios.
                        </p>
                    </td>
                </tr>

                <tr>
                    <td style="height:6px; background:{SEBRAE_GREEN}; font-size:0; line-height:0;">
                        &nbsp;
                    </td>
                </tr>
            </table>
        </td>
    </tr>
    """


def render_section_label(label: str) -> str:
    """Renderiza uma etiqueta visual para seções especiais."""
    return f"""
    <div style="
        display:inline-block;
        background:{SEBRAE_LIGHT_BLUE};
        color:{SEBRAE_DARK_BLUE};
        font-size:11px;
        font-weight:bold;
        text-transform:uppercase;
        letter-spacing:0.4px;
        padding:5px 9px;
        border-radius:999px;
        margin-bottom:8px;
    ">
        {escape_html(label)}
    </div>
    """

def render_news_image(image_url: str, alt_text: str) -> str:
    if not image_url:
        return ""

    return f"""
    <tr>
        <td>
            <img
                src="{escape_html(image_url)}"
                alt="{escape_html(alt_text)}"
                width="100%"
                style="
                    display:block;
                    width:100%;
                    max-width:100%;
                    height:auto;
                    border-radius:10px 10px 0 0;
                    border:0;
                "
            />
        </td>
    </tr>
    """

def render_banner(image_url: str, link_url: str = "") -> str:
    if not image_url:
        return ""

    image_tag = f"""
    <img
        src="{escape_html(image_url)}"
        alt="Banner institucional"
        width="640"
        style="
            display:block;
            width:100%;
            height:auto;
            border:0;
        "
    />
    """

    if link_url:
        image_tag = f"""
        <a href="{escape_html(link_url)}" target="_blank">
            {image_tag}
        </a>
        """

    return f"""
    <tr>
        <td>
            {image_tag}
        </td>
    </tr>
    """


def render_news_item(news: Dict) -> str:
    """Renderiza um card/item de notícia ou bloco editorial."""

    title = escape_html(news.get("title", ""))
    summary = render_text_block(news.get("summary", ""))
    url = get_news_url(news)
    source = escape_html(news.get("source", ""))
    published_at = format_published_at(news.get("published_at", ""))
    setor = escape_html(news.get("setor", ""))

    is_editorial_block = source in {
        "Newsletter",
        "Análise setorial",
        "Sistema",
    }

    label = ""
    if is_editorial_block:
        label = render_section_label(source)
    elif setor:
        label = render_section_label(setor)

    metadata_parts = [
        part for part in [source, published_at]
        if part
    ]

    metadata = " • ".join(metadata_parts)

    if is_editorial_block or url == "#":
        title_html = f"""
        <div style="
            font-size:17px;
            line-height:23px;
            font-weight:bold;
            color:{SEBRAE_DARK_BLUE};
            font-family:Arial, sans-serif;
        ">
            {title}
        </div>
        """
    else:
        title_html = f"""
        <a href="{url}" target="_blank" style="
            font-size:17px;
            line-height:23px;
            font-weight:bold;
            color:{SEBRAE_BLUE};
            text-decoration:none;
            font-family:Arial, sans-serif;
        ">
            {title}
        </a>
        """

    link_button = ""
    if not is_editorial_block and url != "#":
        link_button = f"""
        <div style="margin-top:12px;">
            <a href="{url}" target="_blank" style="
                display:inline-block;
                background:{SEBRAE_BLUE};
                color:#ffffff;
                font-size:13px;
                font-weight:bold;
                text-decoration:none;
                padding:9px 14px;
                border-radius:6px;
                font-family:Arial, sans-serif;
            ">
                Ler mais
            </a>
        </div>
        """

    return f"""
    <tr>
        <td style="padding:0 0 14px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" style="
                border-collapse:collapse;
                background:#ffffff;
                border:1px solid {SEBRAE_BORDER};
                border-radius:10px;
            ">
                <tr>
                    <td style="padding:18px 20px;">
                        {label}

                        {title_html}

                        <p style="
                            margin:10px 0 0 0;
                            font-size:14px;
                            line-height:21px;
                            color:{SEBRAE_TEXT};
                            font-family:Arial, sans-serif;
                        ">
                            {summary}
                        </p>

                        <div style="
                            margin-top:10px;
                            font-size:12px;
                            line-height:17px;
                            color:{SEBRAE_MUTED};
                            font-family:Arial, sans-serif;
                        ">
                            {escape_html(metadata)}
                        </div>

                        {link_button}
                    </td>
                </tr>
            </table>
        </td>
    </tr>
    """


def render_news_section(news_list: List[Dict]) -> str:
    """Renderiza a lista de notícias."""

    if not news_list:
        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
            <tr>
                <td style="
                    padding:20px;
                    background:#ffffff;
                    border:1px solid {SEBRAE_BORDER};
                    border-radius:10px;
                    color:{SEBRAE_MUTED};
                    font-size:14px;
                    font-family:Arial, sans-serif;
                ">
                    Nenhuma notícia relevante hoje.
                </td>
            </tr>
        </table>
        """

    items_html = "".join(render_news_item(news) for news in news_list)

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        {items_html}
    </table>
    """


def render_footer() -> str:
    """Renderiza rodapé padrão com identidade Sebrae/SC."""

    current_year = datetime.now().year

    return f"""
    <tr>
        <td style="padding:20px 28px 28px 28px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="
                border-collapse:collapse;
                border-top:1px solid {SEBRAE_BORDER};
            ">
                <tr>
                    <td align="center" style="padding-top:18px;">
                        <div style="
                            font-size:13px;
                            font-weight:bold;
                            color:{SEBRAE_DARK_BLUE};
                            font-family:Arial, sans-serif;
                        ">
                            Sebrae/SC
                        </div>

                        <div style="
                            margin-top:4px;
                            font-size:12px;
                            line-height:18px;
                            color:{SEBRAE_MUTED};
                            font-family:Arial, sans-serif;
                        ">
                            Você está recebendo esta newsletter automaticamente.<br/>
                            Conteúdo gerado pelo Observatório de Negócios do Sebrae/SC <br/> 
                            para apoiar análise de mercado e tomada de decisão.
                        </div>

                        <div style="
                            margin-top:10px;
                            font-size:11px;
                            color:#9CA3AF;
                            font-family:Arial, sans-serif;
                        ">
                            © {current_year} Sebrae/SC
                        </div>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
    """


# -----------------------------------------
# Template principal
# -----------------------------------------

def render_newsletter(
    title: str,
    news_list: List[Dict],
    # banner_url: str = "",
    # banner_link: str = ""

) -> str:
    """Monta o HTML completo da newsletter."""

    preheader = render_preheader()
    header = render_header(title) 
    # banner = render_banner(
    #     banner_url,
    #     banner_link
    # )
    news_section = render_news_section(news_list)
    footer = render_footer()

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>{escape_html(title)}</title>
    </head>

    <body style="
        margin:0;
        padding:0;
        font-family:Arial, sans-serif;
        background-color:{SEBRAE_BACKGROUND};
    ">
        {preheader}

        <table width="100%" cellpadding="0" cellspacing="0" style="
            border-collapse:collapse;
            background-color:{SEBRAE_BACKGROUND};
            padding:24px 0;
        ">
            <tr>
                <td align="center" style="padding:24px 12px;">
                    <table width="640" cellpadding="0" cellspacing="0" style="
                        width:640px;
                        max-width:100%;
                        border-collapse:collapse;
                        background:#ffffff;
                        border-radius:12px;
                        overflow:hidden;
                        box-shadow:0 4px 18px rgba(0,0,0,0.08);
                    ">
                        {header}
                        <tr>
                            <td style="padding:24px 28px 8px 28px;">
                                {news_section}
                            </td>
                        </tr>

                        {footer}
                    </table>
                </td>
            </tr>
        </table>
    </body>
</html>
    """.strip()


# -----------------------------------------
# Salvar HTML em arquivo
# -----------------------------------------

def save_newsletter_to_file(html_content: str, filename: str) -> None:
    """Salva o conteúdo HTML da newsletter em um arquivo."""

    if not filename:
        raise ValueError("Filename must be provided")

    if not isinstance(html_content, str):
        raise TypeError(
            f"html_content precisa ser str, recebido: {type(html_content).__name__}"
        )

    directory = os.path.dirname(os.path.abspath(filename))

    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(html_content)
    except OSError as error:
        raise OSError(f"Não foi possível salvar o arquivo '{filename}': {error}") from error