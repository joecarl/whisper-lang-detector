"""
Configuración y constantes para el detector de idiomas.
"""

import os
import tempfile
from datetime import datetime

# Mapeo de códigos de idioma de Whisper (ISO 639-1) a ISO 639-2/T (terminológico)
# Usamos códigos terminológicos que son los estándares actuales
WHISPER_TO_ISO639_2 = {
    "en": "eng",  # Inglés
    "es": "spa",  # Español
    "fr": "fra",  # Francés - No "fre" (bibliográfico)
    "de": "deu",  # Alemán - No "ger" (bibliográfico)
    "it": "ita",  # Italiano
    "pt": "por",  # Portugués
    "ru": "rus",  # Ruso
    "ja": "jpn",  # Japonés
    "ko": "kor",  # Coreano
    "zh": "zho",  # Chino - No "chi" (bibliográfico)
    "ar": "ara",  # Árabe
    "ca": "cat",  # Catalán
    "cs": "ces",  # Checo - No "cze" (bibliográfico)
    "da": "dan",  # Danés
    "nl": "nld",  # Holandés - No "dut" (bibliográfico)
    "fi": "fin",  # Finlandés
    "el": "ell",  # Griego - No "gre" (bibliográfico)
    "he": "heb",  # Hebreo
    "hi": "hin",  # Hindi
    "hu": "hun",  # Húngaro
    "id": "ind",  # Indonesio
    "no": "nor",  # Noruego
    "pl": "pol",  # Polaco
    "ro": "ron",  # Rumano - No "rum" (bibliográfico)
    "sv": "swe",  # Sueco
    "th": "tha",  # Tailandés
    "tr": "tur",  # Turco
    "uk": "ukr",  # Ucraniano
    "vi": "vie",  # Vietnamita
    "sq": "sqi",  # Albanés
    "hy": "hye",  # Armenio
    "eu": "eus",  # Vasco
    "my": "mya",  # Birmano
    "ka": "kat",  # Georgiano
    "is": "isl",  # Islandés
    "mk": "mkd",  # Macedonio
    "mi": "mri",  # Maorí
    "ms": "msa",  # Malayo
    "fa": "fas",  # Persa
    "sk": "slk",  # Eslovaco
    "bo": "bod",  # Tibetano
    "cy": "cym",  # Galés
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
    "alb": "sqi",  # Albanés
    "arm": "hye",  # Armenio
    "baq": "eus",  # Vasco
    "bur": "mya",  # Birmano
    "geo": "kat",  # Georgiano
    "ice": "isl",  # Islandés
    "mac": "mkd",  # Macedonio
    "mao": "mri",  # Maorí
    "may": "msa",  # Malayo
    "per": "fas",  # Persa
    "slo": "slk",  # Eslovaco
    "tib": "bod",  # Tibetano
    "wel": "cym",  # Galés
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
