#!/usr/bin/env python3
"""
Script para predescargar modelos de Whisper.
Útil para preparar el entorno antes de procesar archivos.
"""

import argparse
import os
import sys

import whisper

AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]

MODEL_SIZES = {
    "tiny": "~39 MB",
    "base": "~74 MB",
    "small": "~244 MB",
    "medium": "~769 MB",
    "large": "~1550 MB",
    "large-v2": "~1550 MB",
    "large-v3": "~1550 MB",
}


def download_model(model_name: str, download_root: str = None):
    """Descarga un modelo de Whisper."""
    if model_name not in AVAILABLE_MODELS:
        print(f"❌ Modelo '{model_name}' no válido.")
        print(f"Modelos disponibles: {', '.join(AVAILABLE_MODELS)}")
        return False

    size = MODEL_SIZES.get(model_name, "tamaño desconocido")
    print(f"📥 Descargando modelo '{model_name}' ({size})...")

    if download_root:
        print(f"📁 Directorio de descarga: {download_root}")
        os.makedirs(download_root, exist_ok=True)
    else:
        default_dir = os.path.expanduser("~/.cache/whisper")
        print(f"📁 Directorio de descarga: {default_dir}")

    try:
        model = whisper.load_model(model_name, download_root=download_root)
        print(f"✅ Modelo '{model_name}' descargado y cargado correctamente")

        # Mostrar información del modelo
        print("\n📊 Información del modelo:")
        print(f"   - Dispositivo: {model.device}")
        print(f"   - Parámetros: {sum(p.numel() for p in model.parameters()):,}")

        return True
    except Exception as e:
        print(f"❌ Error al descargar el modelo: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Descarga modelos de Whisper para uso offline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s base                    # Descarga el modelo 'base'
  %(prog)s small --dir ./models    # Descarga 'small' en ./models
  %(prog)s --all                   # Descarga todos los modelos
  
Modelos disponibles (ordenados por tamaño):
  tiny      ~39 MB    - El más rápido, precisión básica
  base      ~74 MB    - Balance entre velocidad y precisión (recomendado)
  small     ~244 MB   - Buena precisión, velocidad aceptable
  medium    ~769 MB   - Alta precisión, más lento
  large     ~1550 MB  - Máxima precisión, muy lento
  large-v2  ~1550 MB  - Versión mejorada de large
  large-v3  ~1550 MB  - Versión más reciente de large

Variables de entorno:
  WHISPER_MODEL_DIR   Directorio donde buscar/guardar modelos
        """,
    )

    parser.add_argument("model", nargs="?", choices=AVAILABLE_MODELS, help="Nombre del modelo a descargar")

    parser.add_argument("--all", action="store_true", help="Descargar todos los modelos (requiere ~2.6 GB)")

    parser.add_argument("--dir", dest="download_root", help="Directorio donde descargar el modelo (default: ~/.cache/whisper/)")

    parser.add_argument("--recommended", action="store_true", help="Descargar solo los modelos recomendados (tiny, base, small)")

    args = parser.parse_args()

    # Usar variable de entorno si está definida
    download_root = args.download_root or os.environ.get("WHISPER_MODEL_DIR")

    if args.all:
        print("📦 Descargando TODOS los modelos (~2.6 GB)...")
        print("⚠️  Esto puede tardar varios minutos dependiendo de tu conexión\n")
        success_count = 0
        for model in AVAILABLE_MODELS:
            if download_model(model, download_root):
                success_count += 1
            print()
        print(f"✅ Descargados {success_count}/{len(AVAILABLE_MODELS)} modelos")

    elif args.recommended:
        recommended = ["tiny", "base", "small"]
        print(f"📦 Descargando modelos recomendados: {', '.join(recommended)}\n")
        success_count = 0
        for model in recommended:
            if download_model(model, download_root):
                success_count += 1
            print()
        print(f"✅ Descargados {success_count}/{len(recommended)} modelos")

    elif args.model:
        success = download_model(args.model, download_root)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
