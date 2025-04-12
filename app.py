import gradio as gr
import os
import shutil
import re
import tempfile
import logging
from tika import parser

# configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# configuração Tika
os.environ['TIKA_CLIENT_ONLY'] = 'True'
logger.info("Iniciando aplicação com Apache Tika")

# criar diretórios temporários
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
    try:
        # tenta usar Tika
        parsed_pdf = parser.from_file(pdf_path)
        text_content = parsed_pdf.get('content', '') or ''
        
        if not text_content:
            logger.warning("Nenhum texto extraído do PDF.")
            return "Não foi possível extrair texto desse PDF."
        
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
        
        # salva o arquivo temporariamente
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

# interface gradio
with gr.Blocks(title="PDF Text Extractor") as demo:
    gr.Markdown("# PDF Text Extractor")
    gr.Markdown("Faça upload de um arquivo PDF para extrair o texto.")
    
    pdf_input = gr.File(label="Arquivo PDF")
    output_filename = gr.State(value=None)
    
    with gr.Row():
        extract_btn = gr.Button("Extrair Texto", variant="primary")
    
    text_output = gr.Textbox(label="Texto Extraído", lines=20)
    
    with gr.Row():
        download_btn = gr.Button("Baixar como TXT", variant="secondary")
    
    file_output = gr.File(label="Arquivo para Download", visible=False)
    
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
        
        return create_txt_file(text, filename)
    
    download_btn.click(
        fn=prepare_download,
        inputs=[text_output, output_filename],
        outputs=[file_output]
    )

# iniciar o aplicativo
if __name__ == "__main__":
    # configuração é vital para o funcionamento na Hugging Face Spaces
    demo.launch(server_name="0.0.0.0", server_port=7860)