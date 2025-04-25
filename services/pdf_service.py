import os
import logging
from config.settings import BASE_URL
from services.tika_service import extract_text_with_tika
from utils.text_utils import process_extracted_text
from utils.file_utils import save_temp_file, create_text_file

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrai e processa texto de um arquivo PDF.
    """
    file_size_mb = os.path.getsize(pdf_path) / 1024 / 1024
    logger.info(f"Extraindo texto do arquivo: {pdf_path} (Tamanho: {file_size_mb:.2f}MB)")
    
    # extrai o texto usando Tika
    raw_text = extract_text_with_tika(pdf_path)
    
    # se ocorreu um erro retorna a mensagem de erro
    if raw_text.startswith("Erro"):
        return raw_text
        
    # verifica se conseguiu extrair algum texto
    if not raw_text or len(raw_text.strip()) < 10: 
        logger.warning(f"Texto extraído muito curto ou vazio: '{raw_text}'")
        return "Não foi possível extrair texto deste PDF. O texto extraído está vazio ou é muito curto."
    
    logger.info(f"Texto extraído com sucesso. Tamanho: {len(raw_text)} caracteres")
    
    # processa o texto extraído
    processed_text = process_extracted_text(raw_text)
    
    if not processed_text:
        return "Não foi possível processar o texto extraído deste PDF."
        
    logger.info("Texto extraído e processado com sucesso")
    return processed_text

def process_pdf_file(pdf_file):
    """
    Processa o arquivo PDF enviado e retorna o texto extraído e nome do arquivo.
    """
    if pdf_file is None:
        return "Nenhum arquivo enviado.", None
    
    try:
        logger.info(f"Processando arquivo: {pdf_file.name}")
        
        # salvar o arquivo temporariamente
        temp_path = save_temp_file(pdf_file)
        if not temp_path:
            return "Erro ao salvar o arquivo temporariamente.", None
        
        # extrair texto
        extracted_text = extract_text_from_pdf(temp_path)
        
        # gerar nome do arquivo de saída
        output_filename = os.path.splitext(os.path.basename(pdf_file.name))[0] + ".txt"
        
        return extracted_text, output_filename
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {str(e)}")
        return f"Erro ao processar o arquivo: {str(e)}", None

def generate_api_example_code(pdf_filename):
    """
    Gera código de exemplo para uso da API com o arquivo PDF especificado.
    """
    if not pdf_filename:
        return "Nenhum arquivo enviado. Carregue um PDF para gerar o exemplo de código."
    
    code_example = f"""import requests
import os

# Caminho do seu PDF
PDF_PATH = "{pdf_filename}"

# Etapa 1: Enviar o PDF para o servidor
upload_url = "{BASE_URL}/upload"
with open(PDF_PATH, 'rb') as f:
    files = {{'files': (os.path.basename(PDF_PATH), f, 'application/pdf')}}
    upload_response = requests.post(upload_url, files=files)

if upload_response.status_code != 200:
    print("Erro no upload:", upload_response.text)
    exit()

file_path = upload_response.json()[0]
file_url = f"{BASE_URL}/file={{file_path}}"

# Etapa 2: Solicitar extração do texto
predict_url = "{BASE_URL}/run/predict"
payload = {{
    "data": [{{
        "data": file_url,
        "name": file_path,
        "size": os.path.getsize(PDF_PATH),
        "orig_name": os.path.basename(PDF_PATH),
        "is_file": True
    }}],
    "event_data": None,
    "fn_index": 0,
    "session_hash": "t7xa5iimde"
}}

headers = {{
    "Content-Type": "application/json",
    "Referer": "{BASE_URL}/",
    "Origin": "{BASE_URL}",
    "User-Agent": "Mozilla/5.0"
}}

response = requests.post(predict_url, headers=headers, json=payload)

if response.status_code == 200:
    extracted_text = response.json()["data"][0]
    with open("texto_extraido.txt", "w", encoding="utf-8") as txt_file:
        txt_file.write(extracted_text)
    print("Texto extraído salvo em 'texto_extraido.txt'")
else:
    print("Erro na predição:", response.status_code, response.text)
"""
    return code_example