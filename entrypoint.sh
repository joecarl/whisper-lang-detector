#!/bin/bash

# Verificar que se pasó un archivo como argumento
if [ $# -eq 0 ]; then
    echo "❌ Error: Debes especificar la ruta del video"
    echo "Uso: docker run --rm --gpus all -v /media:/media whisper-lang-detector <ruta-video>"
    echo "Ejemplo: docker run --rm --gpus all -v /media:/media whisper-lang-detector /media/movies/ejemplo.mkv"
    exit 1
fi

# Ejecutar el script de Python con todos los argumentos
exec python3 -m src.main "$@" --json
