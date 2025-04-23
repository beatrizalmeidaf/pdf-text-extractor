import gradio as gr
import os
import shutil
import re
import tempfile
import logging
import time
import requests
from tika import parser

# configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# configuração Tika
os.environ['TIKA_CLIENT_ONLY'] = 'True'
os.environ['TIKA_SERVER_ENDPOINT'] = 'http://127.0.0.1:9998'

# Configuração de tamanho máximo para os arquivos (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB em bytes

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
        # verificar o tamanho do arquivo
        file_size = os.path.getsize(pdf_path)
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"Arquivo muito grande: {file_size} bytes")
            return "Erro: O arquivo é muito grande para ser processado (limite de 100MB). Por favor, utilize um arquivo menor."
        
        # incrementar timeout para arquivos maiores
        timeout = max(300, int(file_size / 1024 / 1024 * 10))  # 10 segundos por MB com mínimo de 300s
        
        # tentar usar Tika com timeout calculado com base no tamanho do arquivo
        parsed_pdf = parser.from_file(pdf_path, requestOptions={'timeout': timeout})
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

# gera código de exemplo para uso da API
def generate_api_example_code(pdf_filename):
    if not pdf_filename:
        return "Nenhum arquivo enviado. Carregue um PDF para gerar o exemplo de código."
    
    code_example = f"""import requests
import os

# Caminho do seu PDF
PDF_PATH = "{pdf_filename}"

# Etapa 1: Enviar o PDF para o servidor
upload_url = "https://pdf-text-extractor-production-ad51.up.railway.app/upload"
with open(PDF_PATH, 'rb') as f:
    files = {{'files': (os.path.basename(PDF_PATH), f, 'application/pdf')}}
    upload_response = requests.post(upload_url, files=files)

if upload_response.status_code != 200:
    print("Erro no upload:", upload_response.text)
    exit()

file_path = upload_response.json()[0]
file_url = f"https://pdf-text-extractor-production-ad51.up.railway.app/file={{file_path}}"

# Etapa 2: Solicitar extração do texto
predict_url = "https://pdf-text-extractor-production-ad51.up.railway.app/run/predict"
payload = {{
    "data": [{{
        "data": file_url,
        "name": file_path,
        "size": os.path.getsize(PDF_PATH),
        "orig_name": os.path.basename(PDF_PATH),
        "is_file": True
    }}],
    "event_data": None,
    "fn_index": 2,
    "session_hash": "t7xa5iimde"
}}

headers = {{
    "Content-Type": "application/json",
    "Referer": "https://pdf-text-extractor-production-ad51.up.railway.app/",
    "Origin": "https://pdf-text-extractor-production-ad51.up.railway.app",
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

# criar interface principal
blocks_interface = gr.Blocks(title="PDF Text Extractor")
with blocks_interface:
    gr.Markdown("# PDF Text Extractor")
    gr.Markdown("Faça upload de um arquivo PDF para extrair o texto. Limite máximo: 100MB.")
    
    pdf_input = gr.File(label="Arquivo PDF")
    output_filename = gr.State(value=None)
    text_content = gr.State(value=None)
    
    with gr.Row():
        extract_btn = gr.Button("Extrair Texto", variant="primary")
    
    text_output = gr.Textbox(label="Texto Extraído", lines=20)
    
    with gr.Row():
        download_btn = gr.Button("Baixar como TXT", variant="secondary")
    
    # status do servidor Tika
    tika_status = "Conectado" if check_tika_server() else "Desconectado"
    gr.Markdown(f"**Status do servidor Tika:** {tika_status}")
    
    # função de extração
    def extract_and_save(pdf_file):
        text, filename = process_pdf(pdf_file)
        if text and not text.startswith("Erro") and filename:
            # Salvar o conteúdo internamente para download posterior
            file_path = create_txt_file(text, filename)
            return text, filename, text
        return text, None, None
    
    extract_btn.click(
        fn=extract_and_save,
        inputs=[pdf_input],
        outputs=[text_output, output_filename, text_content]
    )
    
    # função de download direto
    def prepare_download_file(text, filename):
        if not text or text.startswith("Erro") or not filename:
            return None
        
        file_path = create_txt_file(text, filename)
        return file_path
    
    download_btn.click(
        fn=prepare_download_file,
        inputs=[text_content, output_filename],
        outputs=gr.File(label="Download", visible=False, interactive=False, elem_id="download_file"),
        _js="""
        async function downloadFile(fileData) {
            if (!fileData) return null;
            
            const response = await fetch(fileData);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = fileData.split('/').pop();
            document.body.appendChild(a);
            a.click();
            
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            return null;
        }
        """
    )

# interface API com geração de código (simplificada)
api_interface = gr.Blocks(title="API PDF Text Extractor")
with api_interface:
    gr.Markdown("# API PDF Text Extractor")
    gr.Markdown("Faça upload de um arquivo PDF para gerar o código de exemplo para uso da API.")
    
    # upload e geração de código
    pdf_input_api = gr.File(label="Arquivo PDF")
    
    with gr.Row():
        generate_btn_api = gr.Button("Gerar Código de Exemplo", variant="primary")
    
    # código de exemplo
    gr.Markdown("## Como usar a API com seu PDF")
    gr.Markdown("Copie o código abaixo para usar a API via Python:")
    api_code_output = gr.Code(language="python", label="Código de Exemplo", lines=30)
    
    # função para gerar apenas o código de API
    def generate_api_code(pdf_file):
        if pdf_file is None:
            return "Nenhum arquivo enviado. Carregue um PDF para gerar o exemplo de código."
        
        pdf_filename = os.path.basename(pdf_file.name)
        return generate_api_example_code(pdf_filename)
    
    generate_btn_api.click(
        fn=generate_api_code,
        inputs=[pdf_input_api],
        outputs=[api_code_output]
    )

# iniciar o aplicativo com ambas interfaces
if __name__ == "__main__":
    # porta do ambiente Railway 
    port = int(os.environ.get("PORT", 7860))
    
    # criar uma aplicação que contém ambas interfaces
    demo = gr.TabbedInterface(
        [blocks_interface, api_interface],
        ["Interface Principal", "Interface API"]
    )
    
    demo.launch(server_name="0.0.0.0", server_port=port)