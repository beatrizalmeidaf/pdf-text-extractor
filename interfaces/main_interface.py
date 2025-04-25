import gradio as gr
import logging
from services.pdf_service import process_pdf
from services.tika_service import check_tika_server
from utils.file_utils import create_txt_file

# obter logger
logger = logging.getLogger(__name__)

# função de extração 
def extract_and_save(pdf_file):
    """Extrai texto do PDF e salva em um arquivo temporário"""
    if pdf_file is None:
        return "Nenhum arquivo enviado.", None, None
    
    text, filename = process_pdf(pdf_file)
    if text and not text.startswith("Erro") and filename:
        # salvar o conteúdo internamente para download posterior
        file_path = create_txt_file(text, filename)
        return text, filename, text
    return text, None, None

def create_main_interface():
    """Cria a interface principal da aplicação"""
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
        
        # usar a função extract_and_save global
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
            outputs=gr.File(label="Clique para baixar")
        )
    
    return blocks_interface