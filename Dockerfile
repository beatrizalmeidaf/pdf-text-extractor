FROM python:3.9-slim

WORKDIR /code

# instalar dependências do sistema e Java para o Apache Tika
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre curl wget procps netcat && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# baixar e instalar o servidor Tika
RUN mkdir -p /opt/tika && \
    wget https://archive.apache.org/dist/tika/2.6.0/tika-server-standard-2.6.0.jar -O /opt/tika/tika-server.jar

# copiar requirements.txt
COPY requirements.txt /code/requirements.txt

# instalar dependências Python
RUN pip install --no-cache-dir -r /code/requirements.txt

# copiar o resto do código
COPY . /code/

# expor a porta que o Railway vai usar
ENV PORT=7860
EXPOSE 7860
EXPOSE 9998

# criar script de inicialização para garantir que o Tika Server esteja em execução
RUN echo '#!/bin/bash\n\
echo "Iniciando servidor Tika..."\n\
java -jar /opt/tika/tika-server.jar --host=0.0.0.0 --port=9998 > /code/tika.log 2>&1 &\n\
TIKA_PID=$!\n\
echo "Aguardando Tika iniciar (PID: $TIKA_PID)..."\n\
\n\
# Verificar se o Tika está rodando usando netcat\n\
attempt=0\n\
max_attempts=30\n\
while [ $attempt -lt $max_attempts ]; do\n\
    if netcat -z 127.0.0.1 9998; then\n\
        echo "Servidor Tika está disponível na porta 9998!"\n\
        break\n\
    fi\n\
    attempt=$((attempt+1))\n\
    echo "Tentativa $attempt/$max_attempts - Tika ainda não está disponível..."\n\
    sleep 2\n\
done\n\
\n\
if [ $attempt -eq $max_attempts ]; then\n\
    echo "Falha ao iniciar o servidor Tika após $max_attempts tentativas. Verifique os logs:"\n\
    cat /code/tika.log\n\
    exit 1\n\
fi\n\
\n\
echo "Iniciando aplicação Python..."\n\
python app.py\n' > /code/start.sh && chmod +x /code/start.sh

# usar o script de inicialização
CMD ["/code/start.sh"]