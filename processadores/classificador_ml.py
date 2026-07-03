import joblib
from pathlib import Path


class ClassificadorML:
    def __init__(
        self,
        caminho_modelo="models/modelo_logreg_v1.pkl",
        caminho_vectorizer="models/vectorizer_tfidf_v1.pkl"
    ):
        caminho_modelo = Path(caminho_modelo)
        caminho_vectorizer = Path(caminho_vectorizer)

        if not caminho_modelo.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {caminho_modelo}")

        if not caminho_vectorizer.exists():
            raise FileNotFoundError(f"Vectorizer não encontrado: {caminho_vectorizer}")

        self.modelo = joblib.load(caminho_modelo)
        self.vectorizer = joblib.load(caminho_vectorizer)

    def preparar_texto(self, title, text):
        title = title or ""
        text = text or ""
        return f"{title} {title} {text}".strip()

    def classificar_noticia(self, noticia: dict) -> dict:
        texto_final = self.preparar_texto(
            noticia.get("title", ""),
            noticia.get("text", "")
        )

        X_tfidf = self.vectorizer.transform([texto_final])

        noticia["setor"] = self.modelo.predict(X_tfidf)[0]

        if hasattr(self.modelo, "predict_proba"):
            noticia["confianca_setor"] = float(
                self.modelo.predict_proba(X_tfidf).max()
            )
        else:
            noticia["confianca_setor"] = None

        return noticia
