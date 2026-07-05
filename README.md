# Sistema de Curadoria e Geração de Newsletters Setoriais

## 📖 Visão Geral

Este projeto realiza a **coleta, processamento, classificação e geração automatizada de newsletters segmentadas por setor econômico**.

O fluxo da aplicação permite capturar notícias e conteúdos relevantes, enriquecê-los com análises voltadas para pequenos negócios e gerar newsletters em HTML direcionadas para diferentes segmentos da economia, como:

- 🌱 Agronegócio
- 🛒 Comércio
- 🏭 Indústria
- 🛠️ Serviços

---

## 🏗️ Arquitetura do Projeto

```text
.
├── coletor/
├── config/
├── dados/
├── models/
├── newsletter/
├── persistencia/
├── processadores/
├── tests/
└── main.py
```

---

## 📂 Estrutura de Diretórios

| Diretório | Descrição |
|-----------|-----------|
| **coletor/** | Responsável pela obtenção dos dados e notícias. |
| **config/** | Arquivos de configuração da aplicação. |
| **dados/** | Armazenamento temporário ou intermediário dos dados processados. |
| **models/** | Modelos de dados utilizados pelo sistema. |
| **newsletter/** | Geração do conteúdo final das newsletters. |
| **persistencia/** | Armazenamento permanente das informações. |
| **processadores/** | Regras de negócio, classificação e processamento dos conteúdos. |
| **tests/** | Testes automatizados do projeto. |

---

## 🔄 Fluxo de Processamento

```text
Coleta
    │
    ▼
Normalização
    │
    ▼
Processamento
    │
    ▼
Classificação por Setor
    │
    ▼
Agrupamento de Conteúdo
    │
    ▼
Geração da Newsletter usando LLM como 'editor'
    │
    ▼
Exportação em HTML
```

---

## 📄 Arquivos Gerados

Ao final do processamento, são produzidos os seguintes arquivos:

```text
newsletter_agronegocio.html
newsletter_comercio.html
newsletter_industria.html
newsletter_servico.html
```

---

## ▶️ Execução

Execute o sistema utilizando:

```bash
python main.py
```

---

## 🏢 Setores Suportados

O sistema gera newsletters específicas para os seguintes setores:

- 🌱 Agronegócio
- 🛒 Comércio
- 🏭 Indústria
- 🛠️ Serviços

---

## 🎯 Objetivos do Projeto

- Automatizar a curadoria de conteúdo.
- Reduzir o esforço operacional na produção de newsletters.
- Gerar informações segmentadas por setor econômico.
- Apoiar pequenos negócios na tomada de decisão.
- Facilitar a disseminação de tendências, oportunidades e informações relevantes.

---

## 🚀 Possíveis Evoluções

- Publicação automática por e-mail, exigindo integrações SMTP.
- Exportação das newsletters em PDF.
- Dashboard para monitoramento da execução.
- Métricas de leitura e engajamento.
- Agendamento automático da geração das newsletters.
- Integração com APIs de notícias e portais especializados.

---

## 👨‍💻 Autor
**Paulo Vitor Gonçalves** - Observatório de Negócios do Sebrae/SC.

Projeto desenvolvido para automação de processos de **Inteligência de Mercado**, **Curadoria de Conteúdo** e **Geração Automatizada de Newsletters Setoriais**.
