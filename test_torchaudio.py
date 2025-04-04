import os
import sys
import torch
import torchaudio

print("PyTorch version:", torch.__version__)
print("Torchaudio version:", torchaudio.__version__)
print("Python version:", sys.version)
print("\nEnvironment variables:")
print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'Not set')}")

print("\nChecking for FFmpeg libraries:")
os.system("ldconfig -p | grep libavdevice")
os.system("ldconfig -p | grep libavformat")
os.system("ldconfig -p | grep libavcodec")

print("\nChecking torchaudio FFmpeg availability...")
try:
    torchaudio.utils.ffmpeg_utils.get_video_metadata("nonexistent.mp4")
    print("FFmpeg libraries found by torchaudio")
except FileNotFoundError:
    print("File not found error - expected for nonexistent file")
except ImportError as e:
    print("ImportError:", str(e))
    print("\nDetailed library information:")
    os.system("find /usr -name \"libavdevice*\" -o -name \"libavformat*\" -o -name \"libavcodec*\"")
    exit(1)
except Exception as e:
    print("Other error:", str(e))
    if "FFmpeg" in str(e):
        print("\nDetailed library information:")
        os.system("find /usr -name \"libavdevice*\" -o -name \"libavformat*\" -o -name \"libavcodec*\"")
        exit(1)