#!/bin/bash

echo "Iniciando servidor Tika..."
java -jar /opt/tika/tika-server.jar --host=0.0.0.0 --port=9998 > /code/tika.log 2>&1 &
TIKA_PID=$!
echo "Aguardando Tika iniciar (PID: $TIKA_PID)..."

# verificar se o Tika está rodando usando netcat
attempt=0
max_attempts=30
while [ $attempt -lt $max_attempts ]; do
    if nc -z 127.0.0.1 9998; then
        echo "Servidor Tika está disponível na porta 9998!"
        break
    fi
    attempt=$((attempt+1))
    echo "Tentativa $attempt/$max_attempts - Tika ainda não está disponível..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "Falha ao iniciar o servidor Tika após $max_attempts tentativas. Verifique os logs:"
    cat /code/tika.log
    exit 1
fi

echo "Iniciando aplicação Python..."
python app.py