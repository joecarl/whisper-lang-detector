"""
Clase para analizar pistas de audio individuales.
"""

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from .config import (
    EXTENDED_DURATION_PERCENT,
    EXTENDED_MAX_DURATION,
    EXTENDED_START_PERCENT,
    MIN_CONFIDENCE,
    NO_LANGUAGE_CODES,
    NUM_SAMPLES,
    SAMPLE_DURATION,
    SAMPLE_POSITIONS,
    WHISPER_TO_ISO639_2,
)
from .language_detector import (
    detect_language_with_loaded_model,
    transcribe_with_loaded_model,
)

if TYPE_CHECKING:
    from .video_processor import VideoProcessor


class TrackAnalyzer:
    """Clase para analizar una pista de audio individual."""

    def __init__(self, track: Dict[str, Any], video_processor: "VideoProcessor"):
        """
        Inicializa el analizador para una pista específica.

        Args:
            track: Información de la pista de audio a analizar
            video_processor: Instancia del VideoProcessor para acceder a propiedades compartidas
        """
        self.track = track
        self.video_processor = video_processor
        self.debug = video_processor.debug
        self.audio_tools = video_processor.audio_tools
        self.video_duration = video_processor.video_duration
        self.whisper_model = video_processor.whisper_model

        # Estadísticas del análisis
        self.valid_samples_count: int = 0  # Número de muestras válidas obtenidas
        self.total_samples_attempted: int = 0  # Total de muestras intentadas
        self.extended_analysis_performed: bool = False  # Si se realizó análisis extendido
        self.analysis_method: str = ""  # Método usado: "sampling", "extended", "hybrid"

    def __perform_extended_analysis(self) -> Tuple[Optional[str], float, str]:
        """
        Realiza un análisis extendido del audio (10% - 90% de la duración).

        Returns:
            Tupla (detected_lang, confidence, transcription) o (None, 0, '') si falla
        """
        print("  🔍 Analizando pista casi completa (10% - 90%)...")

        # Calcular duración y posición para análisis extendido
        if self.video_duration:
            extended_start = int(self.video_duration * EXTENDED_START_PERCENT)
            extended_duration = int(self.video_duration * EXTENDED_DURATION_PERCENT)
            # Limitar duración máxima para no sobrecargar
            extended_duration = min(extended_duration, EXTENDED_MAX_DURATION)
        else:
            extended_start = 0
            extended_duration = EXTENDED_MAX_DURATION

        print(f"  📍 Extrayendo desde {extended_start}s por {extended_duration}s")

        extended_sample = self.audio_tools.extract_audio_sample(self.track["id"], extended_duration, extended_start)

        if not extended_sample:
            print("  ❌ No se pudo extraer audio para análisis extendido")
            return None, 0, ""

        try:
            vad_audio, voice_percentage = self.audio_tools.apply_vad(extended_sample)

            # Rechazar si no hay suficiente voz
            if not vad_audio:
                print(f"  ❌ Muestra rechazada por falta de voz ({voice_percentage:.1f}%)")
                return None, 0, ""

            detected_lang, confidence = detect_language_with_loaded_model(vad_audio, self.whisper_model)

            # Marcar que se realizó análisis extendido
            self.extended_analysis_performed = True

            # Obtener transcripción solo en modo debug
            transcription = ""
            if self.debug:
                transcription = transcribe_with_loaded_model(vad_audio, self.whisper_model, language=detected_lang)

            # Rechazar si la confianza es muy baja
            if confidence < MIN_CONFIDENCE:
                print(f"  ⚠️  Confianza muy baja ({confidence:.2%}), rechazando análisis extendido")
                return None, 0, ""

            print(f"  ✅ Análisis extendido completado: {detected_lang} (confianza: {confidence:.2%})")

            return detected_lang, confidence, transcription
        finally:
            if not self.debug:
                if os.path.exists(extended_sample):
                    os.remove(extended_sample)
                if vad_audio and vad_audio != extended_sample and os.path.exists(vad_audio):
                    os.remove(vad_audio)

    def analyze(self) -> Dict[str, Any]:
        """
        Analiza la pista de audio mediante múltiples muestreos.

        Returns:
            Diccionario con información de la pista y detección de idioma
        """
        print(f"\n--- Procesando pista {self.track['id']} ---")

        track_result = {
            "id": self.track["id"],
            "stream_order": self.track["stream_order"],
            "codec": self.track["codec"],
            "channels": self.track["channels"],
            "title": self.track.get("title"),
            "original_language": self.track["language"],
            "original_language_iso": None,
            "detected_language": None,
            "detected_language_iso": None,
            "confidence": None,
            "needs_review": False,
            "transcription": None,
            "should_ignore": self.track.get("should_ignore", False),
        }

        # Verificar si la pista debe ser ignorada
        if track_result.get("should_ignore"):
            print(f"  🚫 Pista marcada para ignorar debido a su título: '{self.track.get('title', 'Sin título')}'")
            track_result["ignore_reason"] = f"Título contiene palabras clave para ignorar: '{self.track.get('title', 'Sin título')}'"
            return track_result

        # Convertir idioma original a ISO 639-2 si existe
        original_language_iso = None
        if self.track["language"] and self.track["language"] != "und":
            original_language_iso = WHISPER_TO_ISO639_2.get(self.track["language"], self.track["language"])

        track_result["original_language_iso"] = original_language_iso

        # Verificar si ya tiene idioma asignado
        has_assigned_language = self.track["language"] and self.track["language"] != "und"
        if has_assigned_language:
            print(f"  ℹ️  Pista ya tiene idioma asignado: {self.track['language']}")
            print(f"  🔍 Verificando idioma con {NUM_SAMPLES} muestreos...")
        else:
            print(f"  🔍 Pista sin idioma asignado, realizando {NUM_SAMPLES} muestreos...")

        all_detections = []  # Lista de tuplas (idioma, confianza, transcripcion)

        # Realizar muestreos
        for sample_num in range(1, NUM_SAMPLES + 1):
            self.total_samples_attempted += 1
            detection = self.__process_single_sample(sample_num)
            if detection:
                all_detections.append(detection)
                self.valid_samples_count += 1

        # Procesar resultados
        detected_lang, confidence, final_transcription = self.__process_detections(all_detections, has_assigned_language)

        # Agregar estadísticas del análisis
        track_result["analysis_stats"] = {
            "valid_samples": self.valid_samples_count,
            "total_samples_attempted": self.total_samples_attempted,
            "extended_analysis": self.extended_analysis_performed,
            "analysis_method": self.analysis_method,
        }

        if detected_lang:
            print(f"\n  🎯 Resultado final: {detected_lang} (confianza: {confidence:.2%})")

            # Convertir a código ISO 639-2 (3 letras) para compatibilidad
            iso_lang_2 = WHISPER_TO_ISO639_2.get(detected_lang, detected_lang)
            print(f"  📋 Código Whisper (ISO 639-1): {detected_lang}")
            print(f"  📋 Código ISO 639-2: {iso_lang_2}")

            track_result["detected_language"] = detected_lang
            track_result["detected_language_iso"] = iso_lang_2
            track_result["confidence"] = confidence
            track_result["transcription"] = final_transcription

            # Determinar si necesita revisión
            if not self.track["language"] or self.track["language"] == "und":
                track_result["needs_review"] = True
                print(f"  📝 Pista SIN idioma -> Se debería asignar: {detected_lang} ({iso_lang_2})")
            elif self.track["language"] == detected_lang:
                print("  ✅ Idioma asignado coincide con el detectado")
                track_result["needs_review"] = False
            else:
                print(f"  ⚠️  Idioma asignado ({self.track['language']}) difiere del detectado ({detected_lang})")
                track_result["needs_review"] = True
        elif self.track["language"] in NO_LANGUAGE_CODES:
            print(f"\n  ✅ La pista está marcada como sin idioma ({self.track['language']}) y no se detectó ninguno")
        else:
            track_result["needs_review"] = True
            print("\n  ❌ No se pudo detectar el idioma")

        return track_result

    def __process_single_sample(self, sample_num: int) -> Optional[Tuple[str, float, str]]:
        """
        Procesa un único muestreo del audio de la pista.

        Args:
            sample_num: Número del muestreo (1-indexed)

        Returns:
            Tupla (idioma, confianza, transcripción) si el muestreo es válido, None si se rechaza
        """
        print(f"\n  🔄 Muestreo {sample_num}/{NUM_SAMPLES}")

        # Calcular tiempo de inicio para esta muestra
        if self.video_duration and self.video_duration > SAMPLE_DURATION:
            position_percent = SAMPLE_POSITIONS[sample_num - 1]
            start_time = int(self.video_duration * position_percent)
            if start_time + SAMPLE_DURATION > self.video_duration:
                start_time = max(0, int(self.video_duration - SAMPLE_DURATION))
            print(f"  📍 Extrayendo desde {position_percent:.0%} del video (tiempo: {start_time}s)")
        else:
            start_time = 0
            print("  📍 Video corto, extrayendo desde el inicio")

        # Extraer muestra de audio
        audio_sample = self.audio_tools.extract_audio_sample(self.track["id"], SAMPLE_DURATION, start_time)

        if not audio_sample:
            print(f"  ⚠️  No se pudo extraer audio en el muestreo {sample_num}")
            return None

        try:
            # Aplicar VAD para filtrar silencios y ruido
            vad_audio, voice_percentage = self.audio_tools.apply_vad(audio_sample)

            # Si no hay suficiente voz, omitir este muestreo
            if not vad_audio:
                print(f"  ❌  Muestreo rechazado por falta de voz ({voice_percentage:.1f}%)")
                return None

            # Detectar idioma (el modelo ya está cargado en VideoProcessor)
            detected_lang, confidence = detect_language_with_loaded_model(vad_audio, self.whisper_model)

            # Obtener transcripción solo en modo debug
            transcription = ""
            if self.debug:
                try:
                    transcription = transcribe_with_loaded_model(vad_audio, self.whisper_model, language=detected_lang)
                except Exception as e:
                    print(f"  ⚠️ [DEBUG] Omitiendo transcripción por error: {e}")
                    transcription = ""

            # Rechazar si la confianza es muy baja
            if confidence < MIN_CONFIDENCE:
                print(f"  ❌  Confianza muy baja ({confidence:.2%}), descartando muestreo")
                return None

            # # Si la transcripción está vacía (por alucinación o error), descartar muestreo
            # if not transcription:
            #     print("  ❌  Muestreo descartado: transcripción vacía o alucinación detectada")
            #     return None

            # Retornar detección válida
            return (detected_lang, confidence, transcription)

        finally:
            # Limpiar archivos temporales
            if not self.debug:
                if os.path.exists(audio_sample):
                    os.remove(audio_sample)
                if vad_audio and vad_audio != audio_sample and os.path.exists(vad_audio):
                    os.remove(vad_audio)

    def __process_detections(
        self,
        all_detections: List[Tuple[str, float, str]],
        has_assigned_language: bool,
    ) -> Tuple[Optional[str], float, str]:
        """
        Procesa los resultados de las detecciones y determina el idioma final.

        Args:
            all_detections: Lista de tuplas (idioma, confianza, transcripción)
            has_assigned_language: Si la pista tiene idioma asignado

        Returns:
            Tupla (detected_lang, confidence, transcription)
        """
        # Si no hay ninguna detección válida, realizar análisis extendido
        if not all_detections:
            print("\n  ⚠️  No se obtuvieron muestras válidas después de los filtros")
            print("\n  🔄 Realizando análisis extendido como último recurso...")
            self.analysis_method = "extended"
            return self.__perform_extended_analysis()

        if has_assigned_language:
            # Caso: Ya hay idioma asignado
            return self.__process_with_assigned_language(all_detections)
        else:
            # Caso: No hay idioma asignado
            return self.__process_without_assigned_language(all_detections)

    def __process_with_assigned_language(
        self,
        all_detections: List[Tuple[str, float, str]],
    ) -> Tuple[Optional[str], float, str]:
        """Procesa detecciones cuando la pista ya tiene idioma asignado."""
        print(f"\n  📊 Analizando resultados de los {NUM_SAMPLES} muestreos...")

        # Buscar si algún muestreo coincide con el idioma asignado con confianza aceptable
        matching_detections = [(lang, conf, text) for lang, conf, text in all_detections if lang == self.track["language"] and conf >= MIN_CONFIDENCE]

        if matching_detections:
            # Al menos uno coincide con confianza aceptable
            detected_lang = self.track["language"]
            best_match = max(matching_detections, key=lambda t: t[1])
            confidence = best_match[1]
            final_transcription = best_match[2]
            print(f"  ✅ {len(matching_detections)} muestreo(s) coinciden con idioma asignado '{detected_lang}'")
            print(f"  🎯 Usando idioma asignado (máxima confianza: {confidence:.2%})")
            self.analysis_method = "sampling"
            return detected_lang, confidence, final_transcription
        else:
            # Ninguno coincide con confianza aceptable -> Analizar casi toda la pista
            print(f"  ⚠️  Ningún muestreo coincide con idioma asignado '{self.track['language']}' " f"con confianza aceptable")

            self.analysis_method = "extended"
            detected_lang, confidence, transcription = self.__perform_extended_analysis()
            if not detected_lang:
                print("  ❌ No se pudo realizar análisis extendido")
            return detected_lang, confidence, transcription or ""

    def __process_without_assigned_language(
        self,
        all_detections: List[Tuple[str, float, str]],
    ) -> Tuple[Optional[str], float, str]:
        """Procesa detecciones cuando la pista no tiene idioma asignado."""
        print(f"\n  📊 Determinando idioma más probable de los {NUM_SAMPLES} muestreos...")

        # Contar frecuencia de cada idioma
        language_scores = {}  # {idioma: puntuación}

        for lang, conf, text in all_detections:
            if lang not in language_scores:
                language_scores[lang] = {"count": 0, "total_confidence": 0, "max_confidence": 0}

            language_scores[lang]["count"] += 1
            language_scores[lang]["total_confidence"] += conf
            language_scores[lang]["max_confidence"] = max(language_scores[lang]["max_confidence"], conf)

        # Calcular puntuación combinada
        for lang, scores in language_scores.items():
            count = scores["count"]
            avg_confidence = scores["total_confidence"] / count
            max_confidence = scores["max_confidence"]

            # Puntuación: (frecuencia * 2) + (confianza_promedio * 3) + (confianza_máxima * 1)
            score = (count * 2) + (avg_confidence * 3) + (max_confidence * 1)
            scores["score"] = score

            print(f"    • {lang}: {count} veces, conf.promedio: {avg_confidence:.2%}, " f"conf.máxima: {max_confidence:.2%}, puntuación: {score:.2f}")

        # Seleccionar el idioma con mayor puntuación
        best_lang = max(language_scores, key=lambda k: language_scores[k]["score"])
        detected_lang = best_lang
        confidence = language_scores[best_lang]["max_confidence"]
        print(f"  🎯 Idioma más probable de muestreos: {detected_lang} (confianza máxima: {confidence:.2%})")

        # Seleccionar la transcripción asociada a la confianza máxima para ese idioma
        best_text = ""
        for lang, conf, text in all_detections:
            if lang == best_lang and conf == language_scores[best_lang]["max_confidence"]:
                best_text = text
                break
        final_transcription = best_text

        # Si la confianza no es aceptable, hacer análisis semicompleto
        if confidence < MIN_CONFIDENCE:
            print(f"  ⚠️  Confianza insuficiente ({confidence:.2%} < {MIN_CONFIDENCE:.0%})")
            detected_lang, confidence, transcription = self.__perform_extended_analysis()
            final_transcription = transcription or final_transcription
            if not detected_lang:
                print("  ⚠️  No se pudo realizar análisis extendido, usando mejor resultado de muestreos")
                self.analysis_method = "sampling"
            else:
                print(f"  ✅ Resultado tras análisis semicompleto: {detected_lang} (confianza: {confidence:.2%})")
                self.analysis_method = "hybrid"
        else:
            print("  ✅ Confianza aceptable, usando resultado de muestreos")
            self.analysis_method = "sampling"

        return detected_lang, confidence, final_transcription
