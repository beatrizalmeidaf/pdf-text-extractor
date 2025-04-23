FROM python:3.9-slim

WORKDIR /code

# instalar dependências do sistema e Java para o Apache Tika
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre curl wget procps netcat-openbsd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# baixar e instalar o servidor Tika
RUN mkdir -p /opt/tika && \
    wget https://archive.apache.org/dist/tika/2.6.0/tika-server-standard-2.6.0.jar -O /opt/tika/tika-server.jar

# criar diretórios necessários para a aplicação
RUN mkdir -p /code/config /code/services /code/utils /code/interfaces

# copiar requirements.txt
COPY requirements.txt /code/requirements.txt

# instalar dependências Python
RUN pip install --no-cache-dir -r /code/requirements.txt

# copiar o resto do código
COPY config/ /code/config/
COPY services/ /code/services/
COPY utils/ /code/utils/
COPY interfaces/ /code/interfaces/
COPY app.py /code/app.py
COPY start.sh /code/start.sh

# expor a porta que o Railway vai usar
ENV PORT=7860
EXPOSE 7860
EXPOSE 9998

# permissão de execução para o script de inicialização
RUN chmod +x /code/start.sh

# usar o script de inicialização
CMD ["/code/start.sh"]