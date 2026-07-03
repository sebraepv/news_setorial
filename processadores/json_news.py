import os
import json
from datetime import datetime


def salvar_json(df, usar_timestamp=True):

    os.makedirs("dados", exist_ok=True)

    df = (
        df
        .dropna(subset=["id"])
        .drop_duplicates(subset=["id"], keep="first")
        .reset_index(drop=True)
    )

    if "topics" in df.columns:
        df["topics"] = df["topics"].apply(
            lambda x: json.dumps(x, ensure_ascii=False)
            if isinstance(x, list) else x
        )

    # Definir caminho
    if usar_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d")
        path = f"dados/noticias_{timestamp}.json"
    else:
        path = "dados/noticias.json"

    df.to_json(
        path,
        orient="records",
        force_ascii=False,
        indent=2,
        date_format="iso"
    )

    print(f"[OK] {len(df)} notícias salvas em {path}")