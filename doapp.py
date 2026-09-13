import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

python = sys.executable

cmd = [
    python, "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "LyrenaAI",

    "--collect-all", "vosk",
    "--collect-all", "edge_tts",
    "--collect-all", "piper",
    "--collect-all", "audioop_lts",


    "--add-binary",
    r"C:\Users\1tekn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages\_sounddevice_data\libportaudio64bit.dll;_sounddevice_data",

    "--add-data",
    f"{BASE_DIR / 'actions'};actions",

    "--add-data",
    f"{BASE_DIR / 'webui'};webui",

    "--add-data",
    f"{BASE_DIR / 'config'};config",

    "--add-data",
    f"{BASE_DIR / 'voicemodel'};voicemodel",

    "--add-data",
    f"{BASE_DIR / 'assets'};assets",

    str(BASE_DIR / "main.py")
]

print("LyrenaAI build başlatılıyor...\n")

try:
    subprocess.run(cmd, check=True)

    print("\n==============================")
    print("BUILD BAŞARILI!")
    print("==============================")
    print("EXE: dist/LyrenaAI.exe")

except subprocess.CalledProcessError as e:
    print("\nBUILD BAŞARISIZ!")
    print(f"PyInstaller hata kodu: {e.returncode}")

except FileNotFoundError:
    print("PyInstaller bulunamadı.")
    print("Şunu çalıştır: pip install pyinstaller")