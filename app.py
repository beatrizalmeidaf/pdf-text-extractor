import gradio as gr
import logging
from config.settings import PORT
from services.tika_service import wait_for_tika
from interfaces.main_interface import create_main_interface
from interfaces.api_interface import create_api_interface

logger = logging.getLogger(__name__)

# verificar conexão com o servidor Tika
wait_for_tika()

# iniciar o aplicativo 
if __name__ == "__main__":
    # criar uma aplicação que contém ambas interfaces
    demo = gr.TabbedInterface(
        [create_main_interface(), create_api_interface()],
        ["Interface Principal", "Interface API"]
    )
    
    # iniciar o servidor Gradio
    logger.info(f"Iniciando servidor na porta {PORT}")
    demo.launch(server_name="0.0.0.0", server_port=PORT)