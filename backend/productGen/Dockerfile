FROM python:3.10-slim

# Evita buffer nos prints
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema (para Pillow + pandas)
RUN apt-get update && apt-get install -y \
    libjpeg-dev zlib1g-dev libpng-dev libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]