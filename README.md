# Whisper Language Detector

Herramienta de análisis de audio que usa Whisper para detectar automáticamente el idioma de pistas de audio en archivos de video. Analiza las pistas, verifica si el idioma asignado es correcto y proporciona sugerencias del idioma detectado en formato JSON o texto legible.

**Nota importante:** Esta herramienta NO modifica archivos. Solo analiza y proporciona sugerencias.

## Estructura del Proyecto

```
whisper-lang-detector/
├── src/
│   ├── __init__.py              # Inicialización del paquete
│   ├── config.py                # Configuración y constantes
│   ├── audio_tools.py           # Extracción de audio y procesamiento VAD
│   ├── language_detector.py     # Modelo Whisper y detección de idioma
│   ├── track_analyzer.py        # Análisis de pistas de audio
│   ├── video_processor.py       # Lógica principal de procesamiento
│   └── main.py                  # Interfaz CLI y punto de entrada
├── whisper_models/              # Directorio para modelos de Whisper
│   └── base.pt                  # Modelo base de Whisper
├── Dockerfile                   # Definición de imagen Docker
├── pyproject.toml              # Configuración del proyecto Python
├── download_model.py           # Script para descargar modelos de Whisper
├── entrypoint.sh               # Script de entrada del contenedor
├── build.sh                    # Script de construcción Docker
├── test.sh                     # Script de pruebas
├── batch_analyze.sh            # Script para procesamiento por lotes
└── README.md                   # Este archivo
```

### Descripción de Módulos

- **config.py**: Contiene todas las constantes de configuración, mapeos de idiomas (ISO 639-1 a ISO 639-2), y parámetros por defecto
- **audio_tools.py**: Maneja la extracción de pistas de audio de videos y aplica Voice Activity Detection (VAD)
- **language_detector.py**: Gestiona la carga del modelo Whisper y la detección de idioma
- **track_analyzer.py**: Analiza las pistas de audio del video y verifica si el idioma asignado coincide con el detectado
- **video_processor.py**: Orquesta el proceso completo de análisis de video, incluyendo estrategias de muestreo múltiple
- **main.py**: Interfaz CLI y formateo de salida (JSON y formato legible)

## Características

- 🤖 Usa OpenAI Whisper para detección precisa de idiomas
- 🎯 Analiza pistas de audio y verifica el idioma asignado
- � Proporciona sugerencias del idioma detectado
- 📄 Salida en formato JSON o texto legible
- 🎙️ Aplica VAD (Voice Activity Detection) para filtrar silencios
- 🔍 Múltiples muestras de diferentes posiciones del video (15%, 25%, 35%, 50%, 65%)
- ⏱️ Muestras de 90 segundos para mayor precisión
- 🚀 Soporta aceleración GPU con CUDA
- 📊 Muestra confianza de detección
- 🔒 No modifica archivos, solo analiza y sugiere

## Desarrollo con DevContainer

El proyecto incluye una configuración de DevContainer para desarrollo en VS Code.

### Requisitos

- Docker
- NVIDIA Container Toolkit

### Configuración inicial

Antes de levantar el DevContainer, debes configurar el punto de montaje en `.devcontainer/devcontainer.json`:

```jsonc
"mounts": [
    "source=/<your_drive>,target=/<your_drive>,type=bind"
],
```

Reemplaza `<your_drive>` con la ruta real de tu unidad o directorio. Por ejemplo:

```jsonc
"mounts": [
    "source=/media,target=/media,type=bind"
],
```

### Levantar el DevContainer

1. Abre el proyecto en VS Code
2. Presiona `F1` o `Ctrl+Shift+P`
3. Selecciona "Dev Containers: Reopen in Container"
4. El contenedor se construirá y se instalarán las dependencias automáticamente


## Construcción de imagen docker

```bash
cd /home/criatura/dockers/whisper-lang-detector
docker build -t whisper-lang-detector .
```

O usando el script de construcción:

```bash
./build.sh
```

## Uso

### Comando básico

```bash
docker run --rm --gpus all -v /media:/media whisper-lang-detector /media/movies/ejemplo.mkv
```

### Con opciones adicionales

```bash
# Salida en formato JSON
docker run --rm --gpus all -v /media:/media whisper-lang-detector /media/movies/ejemplo.mkv --json

# Usar modelo más preciso (más lento)
docker run --rm --gpus all -v /media:/media whisper-lang-detector /media/movies/ejemplo.mkv --model medium

# Combinación: JSON con modelo small
docker run --rm --gpus all -v /media:/media whisper-lang-detector /media/movies/ejemplo.mkv --model small --json
```

## Modelos disponibles

- `tiny`: Más rápido, menos preciso
- `base`: Balance velocidad/precisión (por defecto)
- `small`: Más preciso, más lento
- `medium`: Muy preciso, bastante lento
- `large`: Máxima precisión, muy lento

## Ejemplo con tu archivo

```bash
docker run --rm --gpus all -v /media:/media whisper-lang-detector "/media/movies/Shrek.mkv"
```

## Procesamiento por lotes

Para procesar múltiples archivos desde un archivo de texto:

```bash
# Usar el script batch_analyze.sh (solo debug)
./batch_analyze.sh /media

# O manualmente:
cat listado_de_videos.txt | while read video; do
  docker run --rm --gpus all -v /media:/media whisper-lang-detector "$video"
done
```

## Formatos soportados

- Todos los formatos de video soportados por ffmpeg (MKV, MP4, AVI, MOV, WMV, FLV, etc.)
- Extrae y analiza las pistas de audio sin modificar el archivo original

## Formato de salida

### Salida estándar (por defecto)
Muestra información legible con:
- Ruta del archivo analizado
- Duración del video
- Pistas de audio encontradas con su información (codec, canales, título)
- Idioma asignado originalmente
- Idioma detectado por Whisper
- Nivel de confianza de la detección
- Indicador si necesita revisión (needs_review)
- Estadísticas del análisis

### Salida JSON (--json)
Proporciona la información en formato JSON estructurado para procesamiento automatizado:
```json
{
  "file": "/media/movies/ejemplo.mkv",
  "duration": 1366.308141,
  "audio_tracks": [
    {
      "id": 0,
      "stream_order": null,
      "codec": "AAC",
      "channels": 2,
      "title": "Castellano DDP 2.0",
      "original_language": "es",
      "original_language_iso": "spa",
      "detected_language": "es",
      "detected_language_iso": "spa",
      "confidence": 0.9836201667785645,
      "needs_review": false,
      "transcription": "",
      "should_ignore": false,
      "analysis_stats": {
        "valid_samples": 5,
        "total_samples_attempted": 5,
        "extended_analysis": false,
        "analysis_method": "sampling"
      }
    }
  ]
}
```

**Campos importantes:**
- `needs_review`: `true` si el idioma detectado difiere del asignado originalmente
- `confidence`: Nivel de confianza de la detección (0-1)
- `analysis_stats`: Información sobre el proceso de análisis realizado

## Proceso de detección

La herramienta utiliza un proceso de análisis en múltiples etapas:

1. **Extracción de información**: Lee los metadatos del video y las pistas de audio
2. **Muestreo inteligente**: Toma 5 muestras de 90 segundos en diferentes posiciones (15%, 25%, 35%, 50%, 65%)
3. **VAD (Voice Activity Detection)**: Filtra silencios y ruido, quedándose solo con segmentos con voz
4. **Detección con Whisper**: Analiza el audio para detectar el idioma real
5. **Verificación**: Compara el idioma detectado con el idioma asignado en los metadatos
6. **Reportes**: Genera sugerencias si hay discrepancias (confianza > 50%)

## Idiomas soportados

La herramienta soporta detección automática de más de 25 idiomas incluyendo:
- Español (spa)
- Inglés (eng)
- Francés (fre)
- Alemán (ger)
- Italiano (ita)
- Portugués (por)
- Y muchos más...

## Notas

- La herramienta **no modifica archivos**, solo analiza y proporciona sugerencias
- Analiza todas las pistas de audio del video
- Compara el idioma asignado en metadatos con el idioma detectado por Whisper
- Se requiere una confianza > 50% para reportar una sugerencia de cambio
- La primera ejecución tardará más porque descarga el modelo de Whisper
- Los archivos temporales de audio se limpian automáticamente después del análisis
