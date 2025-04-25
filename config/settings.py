import os
import tempfile
import logging

# configuração de logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# configuração Tika
os.environ['TIKA_CLIENT_ONLY'] = 'True'
os.environ['TIKA_SERVER_ENDPOINT'] = 'http://127.0.0.1:9998'

# configuração de tamanho máximo para os arquivos (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB em bytes

# porta do servidor
PORT = int(os.environ.get("PORT", 7860))

# diretório temporário para arquivos
TEMP_DIR = tempfile.mkdtemp()
logger.info(f"Diretório temporário criado: {TEMP_DIR}")

# URL base da aplicação
API_BASE_URL = "https://pdf-text-extractor-production-ad51.up.railway.app"