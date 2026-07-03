def classificar_setor(row):

    texto = (str(row["title"]) + " " + str(row["text"])).lower()

    # AGRONEGÓCIO
    if any(p in texto for p in [
        "soja", "milho", "café", "pecuária", "gado", "agricultura",
        "safra", "plantio", "colheita", "CONAB", "agro", "agronegócio"
    ]):
        return "agronegócio"

    # INDÚSTRIA
    if any(p in texto for p in [
        "indústria", "produção", "fábrica", "manufatura",
        "mineração", "minério", "energia", "petróleo"
    ]):
        return "indústria"

    # COMÉRCIO
    if any(p in texto for p in [
        "comércio", "varejo", "atacado",
        "exportação", "importação", "tarifa",
        "e-commerce", "consumo", "franchising", "loja"
    ]):
        return "comércio"

    # SERVIÇO
    if any(p in texto for p in [
        "banco", "juros", "crédito", "investimento",
        "tecnologia", "startup", "trabalho",
        "serviços", "financeiro"
    ]):
        return "serviço"

    return "não se aplica"
