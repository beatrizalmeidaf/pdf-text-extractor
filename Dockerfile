FROM python:3.9-slim

# diretório de trabalho no container
WORKDIR /code

# instalar dependências do sistema e Java para o Apache Tika
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        default-jre \
        curl \
        wget \
        procps \
        netcat-openbsd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# baixar o servidor Apache Tika
RUN mkdir -p /opt/tika && \
    wget https://archive.apache.org/dist/tika/2.6.0/tika-server-standard-2.6.0.jar \
    -O /opt/tika/tika-server.jar

# criar diretórios da estrutura do projeto
RUN mkdir -p /code/config /code/services /code/utils /code/interfaces

# copiar requirements e instalar dependências do Python
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# copiar o código da aplicação
COPY config/ /code/config/
COPY services/ /code/services/
COPY utils/ /code/utils/
COPY interfaces/ /code/interfaces/
COPY app.py /code/app.py
COPY start.sh /code/start.sh

# tornar o script executável
RUN chmod +x /code/start.sh

# definir variáveis de ambiente
ENV PORT=7860

# expor portas: 7860 (app), 9998 (Tika)
EXPOSE 7860
EXPOSE 9998

# comando para iniciar a aplicação e o Tika
CMD ["/code/start.sh"]
