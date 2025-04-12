FROM python:3.9-slim

WORKDIR /code

# instalar dependências do sistema e Java para o Apache Tika
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


COPY ./requirements.txt /code/requirements.txt

# instalar dependências 
RUN pip install --no-cache-dir -r /code/requirements.txt

# copiar o resto do código
COPY . /code/

# tornar os diretórios de upload e output
RUN mkdir -p /code/uploads /code/output && \
    chmod 777 /code/uploads /code/output

# porta que a Hugging Face usa
EXPOSE 7860

# iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]