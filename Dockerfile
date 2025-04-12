FROM python:3.9-slim

WORKDIR /code

# Instalar dependências do sistema e Java para o Apache Tika
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar apenas o requirements.txt primeiro para aproveitar o cache do Docker
COPY ./requirements.txt /code/requirements.txt

# Instalar dependências Python
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copiar o resto do código
COPY . /code/

# Tornar os diretórios de upload e output
RUN mkdir -p /code/uploads /code/output && \
    chmod 777 /code/uploads /code/output

# Porta que a Hugging Face usa
EXPOSE 7860

# Criar um script de inicialização
RUN echo '#!/bin/bash\nuvicorn app:app --host 0.0.0.0 --port 7860' > /code/start.sh && \
    chmod +x /code/start.sh

# Usar o script de inicialização
CMD ["/code/start.sh"]

# Adicionar healthcheck
HEALTHCHECK --interval=5s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7860/ || exit 1