FROM python:3.11-slim

WORKDIR /app

# Copiar archivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exponer puerto
EXPOSE $PORT

# Comando para ejecutar la app
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
