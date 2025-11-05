"""
Funciones para detección de idioma y transcripción con Whisper.
"""

import os
from typing import Optional, Tuple

import whisper
from whisper.model import Whisper

from .config import MIN_AUDIO_FILE_SIZE


def load_whisper_model(model_name: str = "base", download_root: Optional[str] = None):
    """
    Carga un modelo de Whisper.

    Args:
        model_name: Nombre del modelo (tiny, base, small, medium, large)
        download_root: Directorio donde descargar/buscar el modelo.
                      Si no se especifica, usa la variable de entorno WHISPER_MODEL_DIR
                      o el directorio por defecto ~/.cache/whisper/

    Returns:
        Modelo de Whisper cargado

    Nota:
        Los modelos se descargan desde https://openaipublic.azureedge.net/main/whisper/
        Puedes predescargar modelos con: whisper-lang-detector-download <model_name>
    """
    # Usar directorio personalizado si está configurado
    if download_root is None:
        download_root = os.environ.get("WHISPER_MODEL_DIR")

    print(f"  🤖 Cargando modelo Whisper '{model_name}'...")
    if download_root:
        print(f"     📁 Directorio de modelos: {download_root}")
        os.makedirs(download_root, exist_ok=True)

    try:
        model = whisper.load_model(model_name, download_root=download_root)
        print(f"  ✅ Modelo '{model_name}' cargado correctamente")
        return model
    except Exception as e:
        print(f"  ❌ Error al cargar el modelo '{model_name}': {e}")
        print("     💡 Tip: Intenta predescargar el modelo con:")
        print(f"        python -c \"import whisper; whisper.load_model('{model_name}')\"")
        raise


def is_transcription_repetitive(text: str, max_repetition_ratio: float = 0.3) -> bool:
    """
    Detecta si una transcripción es repetitiva (indicador de alucinación).

    Args:
        text: Texto de la transcripción
        max_repetition_ratio: Ratio máximo de texto repetido permitido (default 0.3 = 30%)

    Returns:
        bool: True si es repetitiva, False en caso contrario
    """
    if not text or len(text) < 20:
        return False

    # Normalizar el texto
    normalized = text.lower().strip()
    words = normalized.split()

    if len(words) < 5:
        return False

    # Detectar frases o palabras que se repiten consecutivamente
    # Buscar secuencias de 2-10 palabras que se repiten
    for seq_len in range(2, min(11, len(words) // 2 + 1)):
        for i in range(len(words) - seq_len * 2):
            sequence = " ".join(words[i : i + seq_len])
            remaining_text = " ".join(words[i:])

            # Contar cuántas veces se repite la secuencia consecutivamente
            count = 0
            pos = 0
            while pos < len(remaining_text):
                if remaining_text[pos : pos + len(sequence)] == sequence:
                    count += 1
                    pos += len(sequence) + 1  # +1 para el espacio
                else:
                    break

            # Si una secuencia se repite 3+ veces seguidas, es sospechoso
            if count >= 3:
                repetition_ratio = (count * len(sequence)) / len(normalized)
                if repetition_ratio > max_repetition_ratio:
                    print(f"  ⚠️ Repetición detectada: '{sequence[:50]}...' se repite {count} veces ({repetition_ratio:.1%})")
                    return True

    # Detectar si una frase corta domina más del 40% del texto
    for seq_len in range(3, min(8, len(words) // 3 + 1)):
        for i in range(len(words) - seq_len):
            sequence = " ".join(words[i : i + seq_len])
            count = normalized.count(sequence)
            if count > 1:
                repetition_ratio = (count * len(sequence)) / len(normalized)
                if repetition_ratio > 0.4:
                    print(f"  ⚠️ Frase dominante: '{sequence[:50]}...' aparece {count} veces ({repetition_ratio:.1%})")
                    return True

    return False


def detect_language_with_loaded_model(audio_path: str, whisper_model: Whisper) -> Tuple[str, float]:
    """
    Detecta el idioma usando un modelo Whisper ya cargado.
    Analiza múltiples segmentos del audio para mejor precisión.

    Args:
        audio_path: Ruta al archivo de audio
        whisper_model: Modelo de Whisper ya cargado

    Returns:
        Tupla (detected_lang, confidence)
    """
    print("  🔍 Detectando idioma (modelo ya cargado)...")
    audio = whisper.load_audio(audio_path)

    # Whisper analiza en chunks de 30s para detección de idioma
    # Vamos a analizar múltiples segmentos para mejor precisión
    chunk_size = 30 * 16000  # 30 segundos en samples (16kHz)
    num_chunks = max(1, len(audio) // chunk_size)

    # Limitar a los primeros 3 chunks para no hacerlo demasiado lento
    num_chunks = min(num_chunks, 3)

    language_votes = {}  # {idioma: [confianzas]}

    print(f"  🔍 Analizando {num_chunks} segmento(s) de audio...")

    for i in range(num_chunks):
        start = i * chunk_size
        end = min(start + chunk_size, len(audio))
        chunk = audio[start:end]

        # Pad o trim el chunk a exactamente 30s
        chunk = whisper.pad_or_trim(chunk)

        mel = whisper.log_mel_spectrogram(chunk).to(whisper_model.device)
        _, probs = whisper_model.detect_language(mel)

        detected_lang = max(probs, key=probs.get)
        confidence = probs[detected_lang]

        if detected_lang not in language_votes:
            language_votes[detected_lang] = []
        language_votes[detected_lang].append(confidence)

        print(f"    Segmento {i+1}: {detected_lang} ({confidence:.2%})")

    # Calcular idioma más votado con mejor confianza promedio
    best_lang = None
    best_score = 0

    for lang, confidences in language_votes.items():
        avg_conf = sum(confidences) / len(confidences)
        max_conf = max(confidences)
        # Score: promedio de confianza * número de votos + confianza máxima
        score = avg_conf * len(confidences) + max_conf

        if score > best_score:
            best_score = score
            best_lang = lang

    final_confidence = max(language_votes[best_lang])

    print(f"  ✅ Idioma detectado: {best_lang} (confianza: {final_confidence:.2%}, {len(language_votes[best_lang])} voto(s))")

    return best_lang, final_confidence


def transcribe_with_loaded_model(audio_path: str, whisper_model: Whisper, language: Optional[str] = None) -> str:
    """
    Transcribe audio using a pre-loaded Whisper model.

    Returns the transcription text (may be empty on error or hallucination).
    """
    try:
        print("  📝 [DEBUG] Transcribiendo audio...")

        # Validar que el archivo existe y tiene contenido
        if not os.path.exists(audio_path):
            print("  ⚠️ [DEBUG] Archivo de audio no existe para transcribir")
            return ""

        file_size = os.path.getsize(audio_path)
        if file_size < MIN_AUDIO_FILE_SIZE:
            print(f"  ⚠️ [DEBUG] Archivo muy pequeño ({file_size} bytes), omitiendo transcripción")
            return ""

        # Cargar y validar el audio
        try:
            audio = whisper.load_audio(audio_path)
            if len(audio) == 0:
                print("  ⚠️ [DEBUG] Audio vacío, omitiendo transcripción")
                return ""
        except Exception as e:
            print(f"  ⚠️ [DEBUG] Error al cargar audio: {e}")
            return ""

        options = {
            "language": language if language else None,
            "fp16": False,  # Desactivar fp16 para evitar problemas con NaN
            "temperature": (0.0, 0.2, 0.4),  # Usar temperatura 0 para más estabilidad
            "condition_on_previous_text": False,  # Evita sesgos de contexto anterior
            "no_speech_threshold": 0.8,  # Umbral para detectar segmentos sin habla
            # Parámetros anti-alucinación críticos:
            "patience": 1,  # opcional: ligeramente más exploración
            "beam_size": 5,  # beam search estable
            "compression_ratio_threshold": 1.8,  # Detecta repeticiones (más estricto que default 2.4)
            "logprob_threshold": -0.2,  # Rechaza transcripciones de baja confianza (más estricto que -1.0)
        }
        # Eliminar opciones None
        options = {k: v for k, v in options.items() if v is not None}

        # whisper's transcribe method accepts a file path and returns a dict with 'text'
        result = whisper_model.transcribe(audio_path, **options)
        text = result.get("text", "").strip() if isinstance(result, dict) else ""

        # Validar que la transcripción no sea una alucinación
        if text and is_transcription_repetitive(text):
            print("  ⚠️ [DEBUG] Transcripción rechazada: parece ser una alucinación de Whisper")
            snippet = text.replace("\n", " ")[:150]
            print(f"  🗑️ [DEBUG] Texto rechazado: {snippet}")
            return ""

        if text:
            snippet = text.replace("\n", " ")[:300]
            print(f"  🗣️ [DEBUG] Transcripción (primeros 300 chars): {snippet}")
        else:
            print("  🗣️ [DEBUG] Transcripción: (vacía)")
        return text
    except RuntimeError as e:
        if "nan" in str(e).lower() or "invalid values" in str(e).lower():
            print("  ⚠️ [DEBUG] Audio inválido (NaN en logits), omitiendo")
        else:
            print(f"  ⚠️ [DEBUG] Error de runtime al transcribir: {e}")
        return ""
    except Exception as e:
        print(f"  ⚠️ [DEBUG] Error al transcribir: {e}")
        return ""
