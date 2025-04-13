import gradio as gr
import os
import shutil
import re
import tempfile
import logging
import time
import threading
import requests
from tika import parser

# configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# configuração Tika
os.environ['TIKA_CLIENT_ONLY'] = 'True'
os.environ['TIKA_SERVER_ENDPOINT'] = 'http://127.0.0.1:9998'

# verifica se o servidor Tika está rodando
def check_tika_server():
    try:
        response = requests.get("http://127.0.0.1:9998/tika", timeout=10)
        if response.status_code == 200:
            logger.info("Servidor Tika está funcionando!")
            return True
    except Exception as e:
        logger.error(f"Erro ao verificar servidor Tika: {str(e)}")
    return False

# tenta conectar ao servidor Tika
retries = 5
for i in range(retries):
    if check_tika_server():
        break
    logger.warning(f"Tentativa {i+1}/{retries} de conectar ao servidor Tika...")
    time.sleep(10)

# cria diretórios temporários
TEMP_DIR = tempfile.mkdtemp()
logger.info(f"Diretório temporário criado: {TEMP_DIR}")

def is_page_number_line(line: str, max_page_num: int = 1000) -> bool:
    """
    Determina se uma linha contém apenas um número de página.
    Considera números alinhados à direita como números de página.
    """
    # remove espaços no início e fim
    stripped_line = line.strip()
    
    # se a linha está vazia não é número de página
    if not stripped_line:
        return False
        
    # se é apenas um número e está dentro do limite razoável de páginas
    if stripped_line.isdigit() and int(stripped_line) <= max_page_num:
        # verifica se o número está alinhado à direita na linha original
        if line.rstrip() == line.rstrip().rjust(len(line)):
            return True
    
    return False

def clean_page_numbers(text: str) -> str:
    lines = text.split('\n')
    cleaned_lines = []
    previous_line = ''
    
    for i, line in enumerate(lines):
        # pula a linha se for um número de página isolado
        if is_page_number_line(line):
            continue
            
        # preserva números que fazem parte da estrutura do documento
        # remove apenas números que parecem ser números de página no final da linha
        cleaned_line = re.sub(r'\s+\d+\s*$', '', line)
        
        # se a linha anterior termina com hífen e esta linha começa com espaços,
        # mantém a formatação original
        if previous_line.rstrip().endswith('-'):
            cleaned_lines.append(cleaned_line)
        else:
            # remove qualquer ponto sozinho no início da linha
            cleaned_line = re.sub(r'^\s*\.\s*', '', cleaned_line)
            cleaned_lines.append(cleaned_line)
            
        previous_line = cleaned_line
    
    return '\n'.join(cleaned_lines)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrai texto do PDF usando Apache Tika"""
    logger.info(f"Extraindo texto do arquivo: {pdf_path}")

    if not check_tika_server():
        return "Erro: Servidor Tika não está disponível. Por favor, tente novamente mais tarde."
    
    try:
        # tentar usar Tika com timeout explícito
        parsed_pdf = parser.from_file(pdf_path, requestOptions={'timeout': 300})
        text_content = parsed_pdf.get('content', '') or ''
        
        if not text_content:
            logger.warning("Nenhum texto extraído do PDF.")
            return "Não foi possível extrair texto deste PDF."
        
        # divide o texto em páginas
        pages = text_content.split('\f')
        cleaned_pages = []
        
        for page in pages:
            # remove números de página mantendo a formatação
            cleaned_page = clean_page_numbers(page)
            if cleaned_page.strip():  
                cleaned_pages.append(cleaned_page.strip())
        
        # junta as páginas com uma quebra de linha dupla entre elas
        final_text = '\n\n'.join(cleaned_pages)
        logger.info("Texto extraído com sucesso")
        
        return final_text
    except Exception as e:
        logger.error(f"Erro na extração de texto: {str(e)}")
        return f"Erro ao extrair texto: {str(e)}"


def process_pdf(pdf_file):
    """Processa o arquivo PDF enviado e retorna o texto extraído"""
    if pdf_file is None:
        return "Nenhum arquivo enviado.", None
    
    try:
        logger.info(f"Processando arquivo: {pdf_file.name}")
        
        # salvar o arquivo temporariamente
        temp_path = os.path.join(TEMP_DIR, os.path.basename(pdf_file.name))
        
        # gradio disponibiliza o caminho do arquivo em pdf_file.name
        shutil.copy(pdf_file.name, temp_path)
        
        # extrair texto
        extracted_text = extract_text_from_pdf(temp_path)
        
        # gerar nome do arquivo de saída
        output_filename = os.path.splitext(os.path.basename(pdf_file.name))[0] + ".txt"
        
        return extracted_text, output_filename
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {str(e)}")
        return f"Erro ao processar o arquivo: {str(e)}", None

def create_txt_file(text, filename):
    """Cria um arquivo de texto para download"""
    if not text or not filename:
        return None
    
    try:
        # criar arquivo temporário para download
        output_path = os.path.join(TEMP_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        return output_path
    except Exception as e:
        logger.error(f"Erro ao criar arquivo TXT: {str(e)}")
        return None

# função para interface API e gradio
def process_pdf_interface(pdf_file):
    text, filename = process_pdf(pdf_file)
    output_file = None
    if text and not text.startswith("Erro") and filename:
        output_file = create_txt_file(text, filename)
    return text, output_file

# criar ambas as interfaces
blocks_interface = gr.Blocks(title="PDF Text Extractor")
with blocks_interface:
    gr.Markdown("# PDF Text Extractor")
    gr.Markdown("Faça upload de um arquivo PDF para extrair o texto.")
    
    pdf_input = gr.File(label="Arquivo PDF")
    output_filename = gr.State(value=None)
    
    with gr.Row():
        extract_btn = gr.Button("Extrair Texto", variant="primary")
    
    text_output = gr.Textbox(label="Texto Extraído", lines=20)
    
    with gr.Row():
        download_btn = gr.Button("Baixar como TXT", variant="secondary")
    
    file_output = gr.File(label="Arquivo para Download", visible=True)
    
    # status do servidor Tika
    tika_status = "Conectado" if check_tika_server() else "Desconectado"
    gr.Markdown(f"**Status do servidor Tika:** {tika_status}")
    
    # função de extração
    extract_btn.click(
        fn=process_pdf,
        inputs=[pdf_input],
        outputs=[text_output, output_filename]
    )
    
    # função de download
    def prepare_download(text, filename):
        if not text or text.startswith("Erro") or not filename:
            return None
        
        file_path = create_txt_file(text, filename)
        return file_path
    
    download_btn.click(
        fn=prepare_download,
        inputs=[text_output, output_filename],
        outputs=[file_output]
    )

# interface simplificada para API
api_interface = gr.Interface(
    fn=process_pdf_interface,
    inputs=gr.File(label="Envie seu PDF"),
    outputs=[
        gr.Textbox(label="Texto Extraído", lines=20),
        gr.File(label="Download .txt")
    ],
    title="PDF Text Extractor",
    description="Interface + API para extrair texto de arquivos PDF usando Apache Tika."
)

# iniciar o aplicativo com ambas interfaces
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))

    blocks_interface.launch(server_name="0.0.0.0", server_port=port)
    


