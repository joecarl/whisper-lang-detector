# Partir de la imagen base de devcontainer con Python ya configurado
FROM mcr.microsoft.com/devcontainers/python:3.11

# Cambiar a usuario root para instalar dependencias
USER root

# Variables de entorno
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema específicas del proyecto
RUN apt-get update && apt-get install -y \   
    ffmpeg \
    mkvtoolnix \
    mediainfo \
    && rm -rf /var/lib/apt/lists/*

# Instalar PyTorch con soporte CUDA
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

ENV WHISPER_MODEL_DIR=/workspaces/whisper-lang-detector/whisper_models

# Volver al usuario vscode (ya creado por la imagen base)
USER vscode
