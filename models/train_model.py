import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
# from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix


# =========================================================
# 1. CARREGAR DADOS
# =========================================================

colunas = ["id", "source_id", "source", "title", "summary", "text", "setor"]

df_ml = pd.read_excel("dados/ml_data.xlsx")
df_ml = df_ml[colunas].copy()

# remove linhas sem rótulo
df_ml = df_ml.dropna(subset=["setor"])

# remove linhas sem texto
df_ml["title"] = df_ml["title"].fillna("")
df_ml["text"] = df_ml["text"].fillna("")

# junta título + texto
# o título é repetido 2x para ganhar mais peso
df_ml["texto_final"] = (
    df_ml["title"] + " " +
    df_ml["title"] + " " +
    df_ml["summary"]
)

# =========================================================
# 2. DEFINIR X E y
# =========================================================

X = df_ml["texto_final"]
y = df_ml["setor"]

# =========================================================
# 3. K-FOLD CROSS VALIDATION
# =========================================================

n_splits = 5
kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

# =========================================================
# 4. VETORIZAÇÃO TF-IDF + TREINO POR FOLD
# =========================================================

vectorizer_params = {
    "max_features": 5000,
    "ngram_range": (1, 2),   # unigramas + bigramas
    "min_df": 2,
    "max_df": 0.95
}

models = {
    "logistic_regression": LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42
    )
}

scores = {name: [] for name in models}
logistic_predictions = pd.Series(index=X.index, dtype=object)
logistic_confidence = pd.Series(index=X.index, dtype=float)

for fold, (train_idx, test_idx) in enumerate(kf.split(X, y), start=1):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    vectorizer = TfidfVectorizer(**vectorizer_params)
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    for name, model in models.items():
        model.fit(X_train_tfidf, y_train)
        y_pred = model.predict(X_test_tfidf)
        acc = accuracy_score(y_test, y_pred)
        scores[name].append(acc)

        print("=" * 80)
        print(f"FOLD {fold} - MODELO: {name}")
        print("=" * 80)
        print("ACURÁCIA")
        print("=" * 80)
        print(acc)
        print("\n" + "=" * 80)
        print("RELATÓRIO DE CLASSIFICAÇÃO")
        print("=" * 80)
        print(classification_report(y_test, y_pred))
        print("\n" + "=" * 80)
        print("MATRIZ DE CONFUSÃO")
        print("=" * 80)
        print(confusion_matrix(y_test, y_pred))
        print("\n" + "=" * 80)

        if name == "logistic_regression":
            logistic_predictions.iloc[test_idx] = y_pred
            if hasattr(model, "predict_proba"):
                logistic_confidence.iloc[test_idx] = model.predict_proba(X_test_tfidf).max(axis=1)

print("\n" + "=" * 80)
print("MÉDIA DE ACURÁCIA POR MODELO")
print("=" * 80)
for name, acc_list in scores.items():
    mean_acc = sum(acc_list) / len(acc_list)
    print(f"{name}: {mean_acc:.4f}")

# =========================================================
# 8. RESULTADO EM DATAFRAME
# =========================================================

if logistic_predictions.isnull().any():
    raise RuntimeError("Alguns índices não receberam previsão do logistic_regression durante o k-fold.")

if logistic_confidence.isnull().all():
    logistic_confidence = [None] * len(X)


df_resultado = pd.DataFrame({
    "texto": X.values,
    "real": y.values,
    "predito": logistic_predictions.values,
    "confianca": logistic_confidence.values
})

print("\nAmostra de previsões:")
print(df_resultado.head(10))

joblib.dump(model, "models/modelo_logreg_v1.pkl")
joblib.dump(vectorizer, "models/vectorizer_tfidf_v1.pkl")
