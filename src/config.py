"""
Configuración y constantes para el detector de idiomas.
"""

import os
import tempfile
from datetime import datetime

# Mapeo de códigos de idioma de Whisper (ISO 639-1) a ISO 639-2/T (terminológico)
# Usamos códigos terminológicos que son los estándares actuales
WHISPER_TO_ISO639_2 = {
    "en": "eng",
    "es": "spa",
    "fr": "fra",  # No "fre" (bibliográfico)
    "de": "deu",  # No "ger" (bibliográfico)
    "it": "ita",
    "pt": "por",
    "ru": "rus",
    "ja": "jpn",
    "ko": "kor",
    "zh": "zho",  # No "chi" (bibliográfico)
    "ar": "ara",
    "ca": "cat",
    "cs": "ces",  # No "cze" (bibliográfico)
    "da": "dan",
    "nl": "nld",  # No "dut" (bibliográfico)
    "fi": "fin",
    "el": "ell",  # No "gre" (bibliográfico)
    "he": "heb",
    "hi": "hin",
    "hu": "hun",
    "id": "ind",
    "no": "nor",
    "pl": "pol",
    "ro": "ron",  # No "rum" (bibliográfico)
    "sv": "swe",
    "th": "tha",
    "tr": "tur",
    "uk": "ukr",
    "vi": "vie",
}

# Mapeo de códigos bibliográficos obsoletos a terminológicos estándar
# Usado para normalizar códigos que vienen de diferentes fuentes
ISO639_2_BIBLIOGRAPHIC_TO_TERMINOLOGIC = {
    "fre": "fra",  # Francés
    "ger": "deu",  # Alemán
    "chi": "zho",  # Chino
    "cze": "ces",  # Checo
    "dut": "nld",  # Holandés
    "gre": "ell",  # Griego
    "rum": "ron",  # Rumano
}

# Configuración de detección
DEFAULT_MODEL = "base"
NUM_SAMPLES = 5
SAMPLE_DURATION = 90  # segundos
MIN_CONFIDENCE = 0.6  # Confianza mínima aumentada del 50% al 60%

# Códigos ISO 639-2 que indican ausencia de contenido lingüístico
NO_LANGUAGE_CODES = [
    "zxx",  # Sin contenido lingüístico (música, efectos de sonido)
    "und",  # Indefinido
    "mis",  # Misceláneo
    "mul",  # Múltiple (mezcla de idiomas sin uno predominante)
    "qaa",  # Código reservado/privado
]

# Posiciones proporcionales para extraer muestras
SAMPLE_POSITIONS = [0.15, 0.25, 0.35, 0.50, 0.65]

# Configuración de análisis extendido
EXTENDED_START_PERCENT = 0.10  # Iniciar al 10%
EXTENDED_DURATION_PERCENT = 0.80  # Duración del 80% (del 10% al 90%)
EXTENDED_MAX_DURATION = 60 * 60  # Máximo 1 hora

# Configuración de VAD
VAD_AGGRESSIVENESS = 2  # 0-3, siendo 3 el más agresivo
VAD_FRAME_DURATION = 30  # milisegundos
# Porcentaje mínimo de voz para considerar el audio válido
VAD_MIN_VOICE_PERCENTAGE = 10  # %

# Configuración de audio
AUDIO_SAMPLE_RATE = 16000  # Hz
AUDIO_CHANNELS = 1  # Mono

# Configuración de transcripción
MIN_AUDIO_FILE_SIZE = 1000  # bytes, archivos menores se consideran inválidos
# Caracteres mínimos para considerar una transcripción válida
MIN_TRANSCRIPTION_LENGTH = 10
# Ratio máximo de repetición para detectar alucinaciones
MAX_REPETITION_RATIO = 0.7


# Configuración de archivos temporales
def get_temp_dir() -> str:
    """Genera un directorio temporal único para cada ejecución."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_base = os.path.join(tempfile.gettempdir(), "whisper-lang-detector", timestamp)
    os.makedirs(temp_base, exist_ok=True)
    return temp_base
