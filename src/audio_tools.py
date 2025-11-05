"""
Funciones para procesamiento de audio: extracción, VAD, y análisis de pistas.
"""

import os
import subprocess
import tempfile
import wave
from typing import Any, Dict, List, Optional, Tuple

import webrtcvad
from pydub import AudioSegment
from pymediainfo import MediaInfo

from .config import (
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    VAD_AGGRESSIVENESS,
    VAD_FRAME_DURATION,
    VAD_MIN_VOICE_PERCENTAGE,
)


class AudioTools:
    """Clase para manejar el procesamiento de audio de archivos de video."""

    def __init__(self, video_path: str, debug: bool = False, temp_dir: Optional[str] = None):
        """
        Inicializa las herramientas de audio.

        Args:
            video_path: Ruta al archivo de video
            debug: Si es True, no borra archivos temporales y muestra sus rutas
            temp_dir: Directorio temporal para almacenar archivos
        """
        self.video_path = video_path
        self.debug = debug
        self.temp_dir = temp_dir

    @staticmethod
    def should_ignore_track(title: Optional[str]) -> bool:
        """
        Determina si una pista de audio debe ser ignorada basándose en su título.

        Args:
            title: Título de la pista de audio (puede ser None)

        Returns:
            bool: True si la pista debe ser ignorada, False en caso contrario
        """
        if not title:
            return False

        title_lower = title.lower()

        # Palabras clave que indican que la pista debe ser ignorada
        ignore_keywords = [
            "comment",
            "coment",
            "director",
            "interview",
            "entrevista",
            "behind",
            "making",
            "extras",
            "bonus",
            "special",
            "isolated",
            "music score",
            "soundtrack",
            "instrumental",
        ]

        for keyword in ignore_keywords:
            if keyword in title_lower:
                return True

        return False

    def get_audio_tracks(self) -> List[Dict[str, Any]]:
        """Obtiene información de las pistas de audio del video."""
        print(f"📹 Analizando archivo: {self.video_path}")

        media_info = MediaInfo.parse(self.video_path)
        audio_tracks = []
        audio_index = 0  # Contador para índice de audio en ffmpeg (0:a:X)

        for track in media_info.tracks:
            if track.track_type == "Audio":
                # Extraer título/nombre de la pista
                title = None
                if hasattr(track, "title") and track.title:
                    title = track.title
                elif hasattr(track, "tag_title") and track.tag_title:
                    title = track.tag_title
                elif hasattr(track, "tag_name") and track.tag_name:
                    title = track.tag_name
                elif hasattr(track, "name") and track.name:
                    title = track.name

                # Verificar si la pista debe ser ignorada
                should_ignore = self.should_ignore_track(title)

                track_info = {
                    "id": audio_index,  # Usar contador secuencial para ffmpeg
                    "stream_order": track.stream_order,
                    "language": track.language if hasattr(track, "language") else None,
                    "codec": track.format,
                    "channels": track.channel_s,
                    "title": title,
                    "should_ignore": should_ignore,
                }
                audio_tracks.append(track_info)

                lang_status = track_info["language"] if track_info["language"] else "sin idioma"
                title_info = f" - Título: {title}" if title else ""
                ignore_status = " [IGNORAR]" if should_ignore else ""
                print(f"  🔊 Pista {track_info['id']}: {track_info['codec']} - Idioma: {lang_status}{title_info}{ignore_status}")

                audio_index += 1

        return audio_tracks

    def get_video_duration(self) -> Optional[float]:
        """Obtiene la duración del video en segundos."""
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", self.video_path]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            try:
                return float(result.stdout.strip())
            except ValueError:
                return None
        return None

    def extract_audio_sample(self, audio_track_id: int, duration: int = 30, start_time: int = 0) -> Optional[str]:
        """Extrae una muestra de audio de la pista especificada."""
        print(f"  ⏺️  Extrayendo muestra de audio (pista {audio_track_id}, desde {start_time}s, duración {duration}s)...")

        # Usar directorio temporal específico si se proporciona
        if self.temp_dir:
            output_path = os.path.join(self.temp_dir, f"audio_track{audio_track_id}_t{start_time}s.wav")
        else:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                output_path = tmp_file.name

        if self.debug:
            print(f"  🐛 [DEBUG] Archivo temporal de audio creado: {output_path}")

        # Extraer muestra de audio usando ffmpeg
        cmd = [
            "ffmpeg",
            "-fflags",
            "+genpts",  # Generar timestamps si faltan
            "-ss",
            str(start_time),  # Tiempo de inicio
            "-i",
            self.video_path,
            "-map",
            f"0:a:{audio_track_id}",
            "-t",
            str(duration),
            "-ar",
            str(AUDIO_SAMPLE_RATE),  # Whisper usa 16kHz
            "-ac",
            str(AUDIO_CHANNELS),  # Mono
            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  ❌ Error al extraer audio: {result.stderr}")
            return None

        return output_path

    def apply_vad(self, audio_path: str, aggressiveness: int = VAD_AGGRESSIVENESS) -> Tuple[Optional[str], float]:
        """
        Aplica Voice Activity Detection para quedarse solo con segmentos con voz.

        Args:
            audio_path: Ruta al archivo de audio WAV
            aggressiveness: Nivel de agresividad del VAD (0-3, 3 más agresivo)

        Returns:
            Tupla (ruta_audio, porcentaje_voz) donde:
            - ruta_audio: Ruta al archivo con solo voz, o None si falla
            - porcentaje_voz: Porcentaje de frames con voz detectada
        """
        print("  🎙️  Aplicando VAD para filtrar silencios/ruido...")

        try:
            # Cargar el audio con pydub
            audio = AudioSegment.from_wav(audio_path)

            # Convertir a 16kHz mono si no lo está ya
            if audio.frame_rate != AUDIO_SAMPLE_RATE:
                audio = audio.set_frame_rate(AUDIO_SAMPLE_RATE)
            if audio.channels != AUDIO_CHANNELS:
                audio = audio.set_channels(AUDIO_CHANNELS)

            # Exportar temporalmente para procesar con webrtcvad
            if self.temp_dir:
                temp_normalized_path = os.path.join(self.temp_dir, f"vad_normalized_{os.path.basename(audio_path)}")
                temp_normalized = type("obj", (object,), {"name": temp_normalized_path})()
            else:
                temp_normalized = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                temp_normalized.close()

            audio.export(temp_normalized.name, format="wav")

            if self.debug:
                print(f"  🐛 [DEBUG] Archivo temporal normalizado creado: {temp_normalized.name}")

            # Leer el audio normalizado
            with wave.open(temp_normalized.name, "rb") as wf:
                sample_rate = wf.getframerate()
                audio_data = wf.readframes(wf.getnframes())

            # Inicializar VAD
            vad = webrtcvad.Vad(aggressiveness)

            # Procesar en frames de 30ms (requerido por webrtcvad)
            frame_size = int(sample_rate * VAD_FRAME_DURATION / 1000) * 2

            voiced_frames = []
            total_frames = 0
            voiced_count = 0

            # Procesar cada frame
            for i in range(0, len(audio_data), frame_size):
                frame = audio_data[i : i + frame_size]

                # Asegurarse de que el frame tiene el tamaño correcto
                if len(frame) < frame_size:
                    break

                total_frames += 1

                try:
                    # Detectar si hay voz en este frame
                    is_speech = vad.is_speech(frame, sample_rate)

                    if is_speech:
                        voiced_frames.append(frame)
                        voiced_count += 1
                except Exception:
                    # Si falla la detección, incluir el frame por defecto
                    voiced_frames.append(frame)

            # Calcular estadísticas
            voice_percentage = (voiced_count / total_frames * 100) if total_frames > 0 else 0
            voiced_duration = (voiced_count * VAD_FRAME_DURATION) / 1000  # segundos
            total_duration = (total_frames * VAD_FRAME_DURATION) / 1000  # segundos

            print(f"  📊 Voz detectada: {voice_percentage:.1f}% del audio ({voiced_count}/{total_frames} frames)")
            print(f"  ⏱️  Duración con voz: {voiced_duration:.1f}s de {total_duration:.1f}s totales")

            # Si no hay suficiente voz detectada, rechazar la muestra
            if voice_percentage < VAD_MIN_VOICE_PERCENTAGE:
                print(f"  ⚠️  Muy poca voz detectada (< {VAD_MIN_VOICE_PERCENTAGE}%), rechazando muestra")
                if not self.debug:
                    os.remove(temp_normalized.name)
                return None, voice_percentage

            # Si hay voz, crear nuevo archivo solo con los frames de voz
            if self.temp_dir:
                output_path = os.path.join(self.temp_dir, f"vad_output_{os.path.basename(audio_path)}")
            else:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
                    output_path = output_file.name

            if self.debug:
                print(f"  🐛 [DEBUG] Archivo temporal VAD creado: {output_path}")

            with wave.open(output_path, "wb") as wf_out:
                wf_out.setnchannels(1)
                wf_out.setsampwidth(2)  # 16-bit
                wf_out.setframerate(sample_rate)
                wf_out.writeframes(b"".join(voiced_frames))

            # Limpiar temporal
            if not self.debug:
                os.remove(temp_normalized.name)

            print("  ✅ VAD aplicado exitosamente")
            return output_path, voice_percentage

        except Exception as e:
            print(f"  ⚠️  Error al aplicar VAD: {e}")
            print("  ℹ️  Rechazando muestra por error en VAD")
            return None, 0
