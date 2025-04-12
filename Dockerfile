FROM python:3.9-slim

WORKDIR /code

# Instalar dependências do sistema e Java para o Apache Tika
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre curl wget procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Baixar e instalar o servidor Tika
RUN mkdir -p /opt/tika && \
    wget https://archive.apache.org/dist/tika/2.6.0/tika-server-standard-2.6.0.jar -O /opt/tika/tika-server.jar

# Copiar requirements.txt
COPY requirements.txt /code/requirements.txt

# Instalar dependências Python
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copiar o resto do código
COPY . /code/

# Expor a porta para a Hugging Face
EXPOSE 7860

# Criar script de inicialização para garantir que o Tika Server esteja em execução
RUN echo '#!/bin/bash\n\
echo "Iniciando servidor Tika..."\n\
java -jar /opt/tika/tika-server.jar --host=0.0.0.0 --port=9998 > tika.log 2>&1 &\n\
TIKA_PID=$!\n\
echo "Aguardando Tika iniciar (PID: $TIKA_PID)..."\n\
sleep 10\n\
if ps -p $TIKA_PID > /dev/null; then\n\
    echo "Servidor Tika está rodando."\n\
    echo "Iniciando aplicação Python..."\n\
    python app.py\n\
else\n\
    echo "Falha ao iniciar o servidor Tika. Verifique os logs:"\n\
    cat tika.log\n\
    exit 1\n\
fi' > /code/start.sh && chmod +x /code/start.sh

# Usar o script de inicialização
CMD ["/code/start.sh"]