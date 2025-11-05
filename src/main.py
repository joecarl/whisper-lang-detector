#!/usr/bin/env python3
"""
Script principal para detectar el idioma de pistas de audio usando Whisper.
Devuelve información en formato JSON sobre las pistas de audio y los idiomas detectados.
"""

import argparse
import json
import sys
from typing import Any, Dict

from src.config import NO_LANGUAGE_CODES

from .video_processor import VideoProcessor


def print_summary(result: Dict[str, Any]) -> None:
    """Muestra un resumen legible de los resultados."""
    print("\n📊 Resumen de resultados:")
    print(f"Archivo: {result['file']}")
    print(f"Duración: {result['duration']:.1f}s" if result["duration"] else "Duración: desconocida")
    print(f"\nPistas de audio encontradas: {len(result['audio_tracks'])}")

    # Separar pistas ignoradas y procesadas
    ignored_tracks = [track for track in result["audio_tracks"] if track.get("should_ignore", False)]
    processed_tracks = [track for track in result["audio_tracks"] if not track.get("should_ignore", False)]

    # Mostrar pistas ignoradas
    if ignored_tracks:
        print(f"\n🚫 Pistas ignoradas ({len(ignored_tracks)}):")
        for track in ignored_tracks:
            print(f"  Pista {track['id']}:")
            print(f"    Codec: {track['codec']}")
            print(f"    Canales: {track['channels']}")
            print(f"    Título: {track.get('title', 'Sin título')}")
            print(f"    Razón: {track.get('ignore_reason', 'Marcada para ignorar')}")

    # Mostrar pistas procesadas
    if processed_tracks:
        print(f"\n🔍 Pistas procesadas ({len(processed_tracks)}):")
        for track in processed_tracks:
            # Determinar si el idioma coincide
            language_match = False
            if track["detected_language_iso"] and track["original_language_iso"]:
                language_match = track["detected_language_iso"].lower() == track["original_language_iso"].lower()

            # Verificar si el idioma original indica ausencia de contenido lingüístico
            original_is_no_language = track["original_language_iso"] and track["original_language_iso"].lower() in NO_LANGUAGE_CODES

            # Icono según coincidencia
            # ✅ si coincide el idioma, o si el original es "sin lenguaje" y no se detectó nada
            # ⚠️ si se detectó algo pero no coincide
            # ❌ si no se detectó nada y se esperaba un idioma
            if language_match and track["detected_language"]:
                status_icon = "✅"
            elif original_is_no_language and not track["detected_language"]:
                status_icon = "✅"  # Correcto: no hay lenguaje y no se detectó nada
            elif track["detected_language"]:
                status_icon = "⚠️"
            else:
                status_icon = "❌"

            print(f"\n  {status_icon} Pista {track['id']}:")
            print(f"    Codec: {track['codec']}")
            print(f"    Canales: {track['channels']}")
            if track.get("title"):
                print(f"    Título: {track['title']}")
            print(f"    Idioma original: {track['original_language'] or 'sin asignar'}")
            if track["detected_language"]:
                print(f"    Idioma detectado: {track['detected_language']} ({track['detected_language_iso']})")
                print(f"    Confianza: {track['confidence']:.2%}")
                print(f"    Necesita revisión: {'Sí' if track['needs_review'] else 'No'}")

                # Mostrar estadísticas del análisis si están disponibles
                if "analysis_stats" in track:
                    stats = track["analysis_stats"]
                    print("    📊 Estadísticas del análisis:")

                    # Icono según si todas las muestras fueron válidas
                    all_valid = stats["valid_samples"] == stats["total_samples_attempted"]
                    samples_icon = "✅" if all_valid else "⚠️"
                    print(f"       {samples_icon} Muestras válidas: {stats['valid_samples']}/{stats['total_samples_attempted']}")

                    print(f"       Método de análisis: {stats['analysis_method']}")

                    if stats["extended_analysis"]:
                        print("       ⚠️  Se requirió análisis extendido")
            else:
                print("    Idioma detectado: No se pudo detectar")

    # Resumen de pistas que necesitan revisión
    tracks_to_update = [t for t in processed_tracks if t["needs_review"]]
    if tracks_to_update:
        print(f"\n⚠️  {len(tracks_to_update)} pista(s) necesitan revisión de idioma:")
        for track in tracks_to_update:
            print(f"    - Pista {track['id']}: asignar '{track['detected_language_iso']}'")
    elif processed_tracks:
        print("\n✅ Ninguna de las pistas procesadas requiere revisión de idioma")

    if ignored_tracks:
        print(f"\nℹ️  {len(ignored_tracks)} pista(s) fueron ignoradas por contener palabras clave en el título")


def main() -> None:
    parser = argparse.ArgumentParser(description="Detecta idiomas de pistas de audio usando Whisper y devuelve información en JSON")
    parser.add_argument("video_path", help="Ruta al archivo de video")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large"], help="Modelo de Whisper a usar (default: base)")
    parser.add_argument("--json", action="store_true", help="Devolver salida solo en formato JSON (sin logs)")
    parser.add_argument("--debug", action="store_true", help="Modo debug: no borra archivos temporales y muestra sus rutas")
    parser.add_argument("--summary", action="store_true", help="Mostrar resumen del procesamiento")

    args = parser.parse_args()

    # Si se solicita JSON, redirigir prints a stderr

    # Guardar stdout original
    original_stdout = sys.stdout
    # Redirigir stdout a stderr temporalmente para los logs
    sys.stdout = sys.stderr

    processor = VideoProcessor(video_path=args.video_path, model=args.model, debug=args.debug)
    result = processor.process_video()

    # Mostrar resultado en formato legible
    if not args.json:
        sys.stdout = original_stdout

    print_summary(result)

    # Restaurar stdout y escribir JSON
    if args.json:
        sys.stdout = original_stdout
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"error": "Failed to process video"}, indent=2))

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
