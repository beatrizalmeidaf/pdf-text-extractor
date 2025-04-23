import gradio as gr
import os
import logging
from services.pdf_service import generate_api_example_code

logger = logging.getLogger(__name__)

def create_api_interface():
    """
    Cria a interface da API da aplicação.
    """
    blocks = gr.Blocks(title="API PDF Text Extractor")
    
    with blocks:
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
    
    return blocks