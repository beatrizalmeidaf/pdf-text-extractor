# <p align="center">PDF Text Extractor 📄</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/ff637581-a9d4-472f-b7f1-92f8e90763c8" alt="Logo da aplicação" width="200"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python Badge"/>
  <img src="https://img.shields.io/badge/FastAPI-0.103.1-green" alt="FastAPI Badge"/>
  <img src="https://img.shields.io/badge/Docker-Ready-blue" alt="Docker Badge"/>
</p>

**PDF Text Extractor** é uma API para extração automatizada de texto de arquivos PDF, com limpeza inteligente de formatações indesejadas (como números de página), preservando a estrutura original do conteúdo.

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

## Uso da API com Python (via `requests`)

Você também pode integrar a API em qualquer script Python:

### 1. Instale a dependência:

```bash
pip install requests
```

### 2. Exemplo de uso:

```python
import requests
import os

# Caminho do seu PDF
PDF_PATH = "seuarquivo.pdf"

# Etapa 1: Enviar o PDF para o servidor
upload_url = "https://pdf-text-extractor-production-ad51.up.railway.app/upload"
with open(PDF_PATH, 'rb') as f:
    files = {'files': (os.path.basename(PDF_PATH), f, 'application/pdf')}
    upload_response = requests.post(upload_url, files=files)

if upload_response.status_code != 200:
    print("Erro no upload:", upload_response.text)
    exit()

file_path = upload_response.json()[0]
file_url = f"https://pdf-text-extractor-production-ad51.up.railway.app/file={file_path}"

# Etapa 2: Solicitar extração do texto
predict_url = "https://pdf-text-extractor-production-ad51.up.railway.app/run/predict"
payload = {
    "data": [{
        "data": file_url,
        "name": file_path,
        "size": os.path.getsize(PDF_PATH),
        "orig_name": os.path.basename(PDF_PATH),
        "is_file": True
    }],
    "event_data": None,
    "fn_index": 2,
    "session_hash": "t7xa5iimde"
}

headers = {
    "Content-Type": "application/json",
    "Referer": "https://pdf-text-extractor-production-ad51.up.railway.app/",
    "Origin": "https://pdf-text-extractor-production-ad51.up.railway.app",
    "User-Agent": "Mozilla/5.0"
}

response = requests.post(predict_url, headers=headers, json=payload)

if response.status_code == 200:
    extracted_text = response.json()["data"][0]
    with open("texto_extraido.txt", "w", encoding="utf-8") as txt_file:
        txt_file.write(extracted_text)
    print("Texto extraído salvo em 'texto_extraido.txt'")
else:
    print("Erro na predição:", response.status_code, response.text)
```

### Como obter o `session_hash`

Caso o valor `"t7xa5iimde"` não funcione, você pode:

1. Abrir a URL da aplicação: [https://pdf-text-extractor-production-ad51.up.railway.app](https://pdf-text-extractor-production-ad51.up.railway.app)  
2. Clicar com o botão direito > **Inspecionar (F12)**  
3. Procurar por `session_hash` no código-fonte da página  
4. Copiar o valor e substituir no seu script

---

## Execução com Docker

Para rodar a aplicação localmente:

```bash
docker build -t pdf-text-extractor .
docker run -p 7860:7860 pdf-text-extractor
```

Acesse em: [http://localhost:7860](http://localhost:7860)

---

## Tecnologias Utilizadas

- [FastAPI](https://fastapi.tiangolo.com/) – Backend moderno e performático  
- [Gradio](https://www.gradio.app/) – Interface web interativa para APIs e modelos ML  
- [Apache Tika](https://tika.apache.org/) – Extração robusta de texto de PDFs  
- [Uvicorn](https://www.uvicorn.org/) – ASGI server leve e rápido  
- [Gunicorn](https://gunicorn.org/) – Servidor WSGI confiável para produção  
- [python-multipart](https://andrew-d.github.io/python-multipart/) – Suporte a upload de arquivos  
- [Requests](https://docs.python-requests.org/) – Cliente HTTP simples e poderoso  
- [python-dotenv](https://pypi.org/project/python-dotenv/) – Carregamento de variáveis de ambiente via `.env`
