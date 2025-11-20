FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema y herramientas de compilación
RUN apt update && apt install -y \
    ffmpeg \
    mkvtoolnix \
    mediainfo \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt clean

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app

COPY src/ /app/src/
COPY download_model.py /app/
COPY entrypoint.sh /app/
COPY pyproject.toml /app/

# Instalar dependencias de Python
RUN pip install --no-cache-dir .

# Precargar modelo de Whisper (base recomendado)
# Esto evita que se descargue en runtime
ENV WHISPER_MODEL_DIR=/app/models
RUN mkdir -p /app/models && \
    python3 download_model.py base --dir /app/models && \
    rm -rf /root/.cache
# Si prefieres copiar un modelo local, descomenta la siguiente línea y comenta las anteriores
#COPY whisper_models/base.pt /app/models/base.pt 

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
