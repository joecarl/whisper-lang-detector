"""
Lógica principal de procesamiento de videos y análisis de pistas de audio.
"""

import os
from typing import Any, Dict, Optional

from whisper.model import Whisper

from .audio_tools import AudioTools
from .config import get_temp_dir
from .language_detector import load_whisper_model
from .track_analyzer import TrackAnalyzer


class VideoProcessor:
    """Clase para procesar videos y detectar idiomas en pistas de audio."""

    def __init__(self, video_path: str, model: str = "base", debug: bool = False):
        """
        Inicializa el procesador de video.

        Args:
            video_path: Ruta al archivo de video a procesar
            model: Nombre del modelo Whisper a usar
            debug: Si es True, no borra archivos temporales y muestra sus rutas
        """

        if not os.path.exists(video_path):
            print("❌ Error: El archivo no existe")
            return None

        self.video_path = video_path
        self.model = model
        self.debug = debug
        self.temp_dir = get_temp_dir()  # Directorio temporal único para esta ejecución
        self.whisper_model: Optional[Whisper] = None
        self.audio_tools = AudioTools(video_path, debug=debug, temp_dir=self.temp_dir)
        self.video_duration: Optional[float] = self.audio_tools.get_video_duration()

        if debug:
            print(f"  🐛 [DEBUG] Directorio temporal: {self.temp_dir}")

    def process_video(self) -> Optional[Dict[str, Any]]:
        """Procesa el video y devuelve información sobre las pistas de audio detectadas."""
        print(f"\n{'=' * 80}")
        print(f"🎬 Procesando: {self.video_path}")
        print(f"{'=' * 80}\n")

        # Obtener pistas de audio
        audio_tracks = self.audio_tools.get_audio_tracks()

        if not audio_tracks:
            print("❌ No se encontraron pistas de audio")
            return None

        # Mostrar duración del video (ya calculada en __init__)
        if self.video_duration:
            print(f"📏 Duración del video: {self.video_duration:.1f}s\n")

        # Cargar modelo Whisper
        print(f"🔄 Cargando modelo Whisper '{self.model}'...")
        self.whisper_model = load_whisper_model(self.model)
        print(f"✅ Modelo Whisper '{self.model}' cargado correctamente\n")

        # Resultado a devolver
        result = {"file": self.video_path, "duration": self.video_duration, "audio_tracks": []}

        # Procesar todas las pistas de audio
        for track in audio_tracks:
            # Crear analizador para esta pista específica
            track_analyzer = TrackAnalyzer(track, self)
            track_result = track_analyzer.analyze()
            result["audio_tracks"].append(track_result)

        print(f"\n{'=' * 80}")
        print("✅ Detección completada")
        print(f"{'=' * 80}\n")

        return result
