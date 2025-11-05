#!/bin/bash

# Script para analizar recursivamente todos los videos en una carpeta
# Uso: ./batch_analyze.sh <directorio>

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que se proporcionó un directorio
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Debes proporcionar un directorio como parámetro${NC}"
    echo "Uso: $0 <directorio>"
    exit 1
fi

DIRECTORY="$1"

# Verificar que el directorio existe
if [ ! -d "$DIRECTORY" ]; then
    echo -e "${RED}Error: El directorio '$DIRECTORY' no existe${NC}"
    exit 1
fi

# Extensiones de video comunes
VIDEO_EXTENSIONS="mp4|mkv|avi|mov|wmv|flv|webm|m4v|mpg|mpeg|3gp|ts|m2ts"

# Buscar todos los archivos de video recursivamente
echo -e "${BLUE}🔍 Buscando archivos de video en: $DIRECTORY${NC}"
echo ""

# Usar find para buscar archivos con extensiones de video (case insensitive)
mapfile -t video_files < <(find "$DIRECTORY" -type f -regextype posix-extended -iregex ".*\.(${VIDEO_EXTENSIONS})$" | sort)

# Contar archivos encontrados
total_files=${#video_files[@]}

if [ $total_files -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No se encontraron archivos de video en el directorio especificado${NC}"
    exit 0
fi

echo -e "${GREEN}✅ Se encontraron $total_files archivo(s) de video${NC}"
echo ""

# Contador de archivos procesados
processed=0
skipped=0

# Procesar cada archivo de video
for video_file in "${video_files[@]}"; do
    ((processed++))
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📹 Archivo $processed de $total_files${NC}"
    echo -e "${BLUE}📄 $video_file${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Ejecutar el análisis
    python3 -m src.main "$video_file" --summary 2>>log.txt
    
    # Guardar el código de salida
    exit_code=$?
    
    echo ""
    
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}❌ Error al analizar el archivo (código de salida: $exit_code)${NC}"
    else
        echo -e "${GREEN}✅ Análisis completado${NC}"
    fi
    
    echo ""
    
    # Mostrar progreso y continuar automáticamente
    if [ $processed -lt $total_files ]; then
        echo -e "${YELLOW}Quedan $((total_files - processed)) archivo(s) por procesar${NC}"
        echo -e "${GREEN}➡️  Continuando con el siguiente archivo...${NC}"
        echo ""
    fi
done

# Resumen final
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📊 Resumen del procesamiento por lotes${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Total de archivos encontrados: $total_files"
echo -e "Archivos procesados: $processed"
if [ $skipped -gt 0 ]; then
    echo -e "Archivos saltados: $skipped"
fi
echo -e "${GREEN}✅ Proceso completado${NC}"
