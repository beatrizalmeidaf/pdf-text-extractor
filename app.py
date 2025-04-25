import gradio as gr
import logging
from config.settings import PORT
from services.tika_service import wait_for_tika
from interfaces.main_interface import create_main_interface, extract_and_save
from interfaces.api_interface import create_api_interface

logger = logging.getLogger(__name__)

# verificar conexão com o servidor Tika
wait_for_tika()

# iniciar o aplicativo 
if __name__ == "__main__":
    # criar uma aplicação usando Blocks para ter mais controle
    with gr.Blocks() as demo:
        # criar uma aplicação que contém ambas interfaces como abas
        tabs = gr.TabbedInterface(
            [create_main_interface(), create_api_interface()],
            ["Interface Principal", "Interface API"]
        )
    
    # adicionar fila de processamento
    demo.queue(max_size=20)
    
    # iniciar o servidor Gradio
    logger.info(f"Iniciando servidor na porta {PORT}")
    

    app = gr.mount_gradio_app(gr.App.create_app(demo), "/")
    
    @app.post("/api/extract_text")
    async def api_extract_text_endpoint(pdf_file):
        return extract_and_save(pdf_file)
    
    # iniciar o servidor
    demo.launch(server_name="0.0.0.0", server_port=PORT)