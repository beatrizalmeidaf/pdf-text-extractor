FROM python:3.9-slim

WORKDIR /code

# instalar dependências do sistema e Java para o Apache Tika
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# copiar apenas o requirements.txt primeiro para aproveitar o cache do Docker
COPY ./requirements.txt /code/requirements.txt

# instalar dependências python
RUN pip install --no-cache-dir -r /code/requirements.txt

# copia o resto do código
COPY . /code/

# tornar os diretórios de upload e output
RUN mkdir -p /code/uploads /code/output && \
    chmod 777 /code/uploads /code/output

# porta que a Hugging Face usa
EXPOSE 7860

# executar a aplicação diretamente 
CMD ["python", "app.py"]

# adiciona healthcheck
HEALTHCHECK --interval=5s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7860/ || exit 1