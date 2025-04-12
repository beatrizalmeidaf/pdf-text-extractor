# PDF Text Extractor 📄

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103.1-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

**PDF Text Extractor** é uma API para extração automatizada de texto de arquivos PDF, com limpeza inteligente de formatações indesejadas como números de página, preservando a estrutura original do conteúdo.

---

## Funcionalidades

- Upload de arquivos PDF via interface web
- Extração de texto com limpeza automática
- Remoção de números de página e elementos redundantes
- Visualização do texto diretamente na aplicação
- Download do conteúdo extraído em `.txt`

---

## Acesso via Interface Web

1. Acesse: [https://pdf-text-extractor-production-ad51.up.railway.app](https://pdf-text-extractor-production-ad51.up.railway.app)
2. Faça o upload de um arquivo PDF
3. Clique em **Extrair Texto**
4. Visualize o conteúdo ou clique em **Baixar como TXT**

---

## Integração com Python

Você pode consumir a API diretamente em qualquer aplicação Python:

```python
import requests

API_URL = "https://pdf-text-extractor-production-ad51.up.railway.app/run/predict"
pdf_file_path = "seuarquivo.pdf"

with open(pdf_file_path, "rb") as f:
    files = {"data": (pdf_file_path, f, "application/pdf")}
    response = requests.post(API_URL, files=files)

if response.status_code == 200:
    result = response.json()
    texto_extraido = result["data"][0]
    nome_arquivo = result["data"][1]
    print(f"Texto extraído:\n{texto_extraido}")
else:
    print(f"Erro: {response.status_code} - {response.text}")
```

---

## Execução com Docker

Para rodar localmente:

```bash
docker build -t pdf-text-extractor .
docker run -p 7860:7860 pdf-text-extractor
```

Acesse em: [http://localhost:7860](http://localhost:7860)

---

## Tecnologias Utilizadas

- [FastAPI](https://fastapi.tiangolo.com/) – Backend rápido e moderno
- [Gradio](https://www.gradio.app/) – Interface web para aplicações de ML/API
- [Tika](https://tika.apache.org/) – Extração robusta de texto de PDFs
- [Uvicorn](https://www.uvicorn.org/) – ASGI server rápido e leve
- [Gunicorn](https://gunicorn.org/) – WSGI server para produção
- [python-multipart](https://andrew-d.github.io/python-multipart/) – Upload de arquivos
- [Requests](https://docs.python-requests.org/) – Cliente HTTP para integração
- [python-dotenv](https://pypi.org/project/python-dotenv/) – Gerenciamento de variáveis de ambiente
