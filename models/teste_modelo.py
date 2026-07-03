import joblib

model = joblib.load("models/modelo_logreg_v1.pkl")
vectorizer = joblib.load("models/vectorizer_tfidf_v1.pkl")

novo_texto = ["A indústria aumnentou a produção de bens de consumo em 2023, impulsionada pela demanda crescente e avanços tecnológicos."]
novo_texto_tfidf = vectorizer.transform(novo_texto)

pred = model.predict(novo_texto_tfidf)
prob = model.predict_proba(novo_texto_tfidf)
print(pred)