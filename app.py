import gradio as gr
import logging
import threading
from config.settings import PORT
from services.tika_service import wait_for_tika
from interfaces.main_interface import create_main_interface, extract_and_save
from interfaces.api_interface import create_api_interface

logger = logging.getLogger(__name__)

# verificar conexão com o servidor Tika
wait_for_tika()

# iniciar o aplicativo 
if __name__ == "__main__":
    
    with gr.Blocks() as demo:
        with gr.Tabs():
            with gr.Tab("Interface Principal"):
                create_main_interface()
          
            # with gr.Tab("Interface API"):
            #     create_api_interface()

        gr.Interface(
            fn=extract_and_save,
            inputs=gr.File(label="PDF File"),
            outputs=[
                gr.Textbox(label="Texto Extraído"),
                gr.Textbox(label="Nome do Arquivo"),
                gr.Textbox(label="Conteúdo do Texto")
            ],
            api_name="extract_text",
            visible=False  
        )

    
    # adicionar fila de processamento
    demo.queue(max_size=20)
    
    # iniciar o servidor Gradio
    logger.info(f"Iniciando servidor na porta {PORT}")
    demo.launch(server_name="0.0.0.0", server_port=PORT)