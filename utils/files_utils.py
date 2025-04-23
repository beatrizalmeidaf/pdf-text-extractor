import os
import shutil
import logging
from config.settings import TEMP_DIR

logger = logging.getLogger(__name__)

def save_temp_file(file_obj, filename=None):
    """
    Salva um arquivo temporariamente e retorna o caminho.
    """
    if not file_obj:
        return None
        
    try:
        if not filename:
            filename = os.path.basename(file_obj.name)
            
        temp_path = os.path.join(TEMP_DIR, filename)
        
        # Gradio disponibiliza o caminho do arquivo em file_obj.name
        shutil.copy(file_obj.name, temp_path)
        
        logger.info(f"Arquivo salvo temporariamente em: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo temporário: {str(e)}")
        return None

def create_text_file(text, filename):
    """
    Cria um arquivo de texto para download e retorna o caminho.
    """
    if not text or not filename:
        return None
    
    try:
        # criar arquivo temporário para download
        output_path = os.path.join(TEMP_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        logger.info(f"Arquivo de texto criado em: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erro ao criar arquivo TXT: {str(e)}")
        return None