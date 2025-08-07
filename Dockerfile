# Usa una imagen oficial de Python
FROM python:3.11-slim

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Crea el directorio de trabajo
WORKDIR /app

# Copia los archivos necesarios
COPY requirements.txt .
COPY proxy_server.py .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto 5000
EXPOSE 5000

# Ejecuta el servidor Flask
CMD ["python", "proxy_server.py"]
