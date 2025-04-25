import gradio as gr
import logging
from config.settings import PORT
from services.tika_service import wait_for_tika
from interfaces.main_interface import create_main_interface, extract_and_save
from interfaces.api_interface import create_api_interface

logger = logging.getLogger(__name__)

# verificar conexão com o servidor Tika
wait_for_tika()

# criar API endpoint
def create_api_endpoint():
    return gr.Interface(
        fn=extract_and_save,
        inputs=gr.File(label="PDF File"),
        outputs=[
            gr.Textbox(label="Texto Extraído"),
            gr.Textbox(label="Nome do Arquivo"),
            gr.Textbox(label="Conteúdo do Texto")
        ],
        title="PDF Text Extractor API",
        description="API para extração de texto de PDFs",
        allow_flagging="never",
        api_name="extract_text"  
    )

# iniciar o aplicativo 
if __name__ == "__main__":
    # criar interfaces
    main_interface = create_main_interface()
    api_interface = create_api_interface()
    api_endpoint = create_api_endpoint()
    
    # criar uma aplicação que contém as interfaces como abas
    demo = gr.TabbedInterface(
        [main_interface, api_interface],
        ["Interface Principal", "Interface API"]
    )

    api = create_api_endpoint()
    
    # adicionar fila de processamento
    demo.queue(max_size=20)
    
    # iniciar o servidor Gradio
    logger.info(f"Iniciando servidor na porta {PORT}")
    demo.launch(server_name="0.0.0.0", server_port=PORT)
    
    # iniciar API endpoint separadamente 
    api_port = PORT + 1
    logger.info(f"Iniciando API endpoint na porta {api_port}")
    api_endpoint.launch(server_name="0.0.0.0", server_port=api_port, share=False)