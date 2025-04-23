import os
import time
import requests
import logging
from tika import parser
from config.settings import MAX_FILE_SIZE

logger = logging.getLogger(__name__)

def check_tika_server():
    """
    Verifica se o servidor Tika está rodando.
    """
    try:
        response = requests.get("http://127.0.0.1:9998/tika", timeout=10)
        if response.status_code == 200:
            logger.info("Servidor Tika está funcionando!")
            return True
    except Exception as e:
        logger.error(f"Erro ao verificar servidor Tika: {str(e)}")
    return False

def wait_for_tika(max_retries=5, wait_time=10):
    """
    Tenta conectar ao servidor Tika com várias tentativas.
    """
    for i in range(max_retries):
        if check_tika_server():
            return True
        logger.warning(f"Tentativa {i+1}/{max_retries} de conectar ao servidor Tika...")
        time.sleep(wait_time)
    return False

def extract_text_with_tika(file_path):
    """
    Extrai texto de um arquivo usando o Apache Tika.
    """
    if not check_tika_server():
        return "Erro: Servidor Tika não está disponível. Por favor, tente novamente mais tarde."
    
    try:
        # verificar o tamanho do arquivo
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"Arquivo muito grande: {file_size} bytes")
            return "Erro: O arquivo é muito grande para ser processado (limite de 100MB). Por favor, utilize um arquivo menor."
        
        # incrementar timeout para arquivos maiores
        timeout = max(300, int(file_size / 1024 / 1024 * 10))  # 10 segundos por MB com mínimo de 300s
        
        # tentar usar Tika com timeout calculado com base no tamanho do arquivo
        parsed_file = parser.from_file(file_path, requestOptions={'timeout': timeout})
        text_content = parsed_file.get('content', '') or ''
        
        if not text_content:
            logger.warning("Nenhum texto extraído do arquivo.")
            return "Não foi possível extrair texto deste arquivo."
            
        return text_content
        
    except Exception as e:
        logger.error(f"Erro na extração de texto: {str(e)}")
        return f"Erro ao extrair texto: {str(e)}"