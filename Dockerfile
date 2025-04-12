FROM python:3.9-slim

WORKDIR /code

# Instalar dependências do sistema e Java para o Apache Tika
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre curl wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Baixar e instalar o servidor Tika (se necessário)
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

# Iniciar o Tika Server e depois a aplicação
CMD ["bash", "-c", "java -jar /opt/tika/tika-server.jar --host=localhost --port=9998 & python app.py"]