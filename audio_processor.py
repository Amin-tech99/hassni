import os
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger(__name__)

# Check if FFmpeg is available
try:
    subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    FFMPEG_AVAILABLE = True
except (FileNotFoundError, subprocess.SubprocessError):
    logger.warning("FFmpeg not found. Audio processing functionality will be limited.")
    FFMPEG_AVAILABLE = False

# Initialize variables to avoid LSP errors
TORCH_AVAILABLE = False
torch = None
torchaudio = None
download_url_to_file = None

# Try to import torch and torchaudio, but provide fallbacks if they're not available
try:
    import torch
    from torch.hub import download_url_to_file
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("Torch/torchaudio not available. Audio processing functionality will be limited.")

def download_if_not_exists(url, target_path):
    """Download a file from URL if it doesn't exist"""
    if not TORCH_AVAILABLE:
        logger.warning("Torch not available, cannot download files")
        return False
        
    if not os.path.exists(target_path):
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        try:
            download_url_to_file(url, target_path)
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
    return True

def get_silero_vad_model():
    """Get the Silero VAD model, downloading if necessary"""
    if not TORCH_AVAILABLE:
        raise ImportError("Torch is not available, cannot use silero-vad model")
    try:
        vad_model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=False)
        (get_speech_timestamps, save_audio, read_audio, _, _) = utils
        return vad_model, get_speech_timestamps, save_audio, read_audio
    except Exception as e:
        logger.error(f"Error loading silero-vad model: {e}")
        # Try direct download from URL as a fallback
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'silero_vad.pt')
        
        model_url = "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.jit"
        if download_if_not_exists(model_url, local_path):
            try:
                vad_model = torch.jit.load(local_path)
                def get_speech_timestamps(audio, model, sampling_rate=16000, threshold=0.5, min_speech_duration_ms=250, **kwargs):
                    """Get speech timestamps using silero VAD model"""
                    model.eval()
                    
                    # Ensure audio is correct shape
                    if len(audio.shape) > 1:
                        audio = audio[0]  # Take first channel
                    
                    # Process in chunks to avoid memory issues
                    window_size_samples = sampling_rate * 30  # 30 seconds
                    speech_timestamps = []
                    
                    for i in range(0, len(audio), window_size_samples):
                        chunk = audio[i:i+window_size_samples]
                        # Move to same device as model
                        chunk = chunk.to(next(model.parameters()).device)
                        
                        # Get VAD predictions
                        with torch.no_grad():
                            speech_prob = model(chunk, sampling_rate)
                        
                        # Get timestamps where speech prob > threshold
                        mask = (speech_prob > threshold).int()
                        
                        # Find contiguous regions of speech
                        starts = []
                        ends = []
                        in_speech = False
                        for j, val in enumerate(mask):
                            if val == 1 and not in_speech:
                                starts.append(j)
                                in_speech = True
                            elif val == 0 and in_speech:
                                ends.append(j)
                                in_speech = False
                        
                        if in_speech:  # If audio ends during speech
                            ends.append(len(mask))
                        
                        # Convert to original audio index
                        for start, end in zip(starts, ends):
                            speech_timestamps.append({
                                'start': i + start,
                                'end': i + end
                            })
                    
                    # Merge overlapping segments
                    if speech_timestamps:
                        merged_timestamps = [speech_timestamps[0]]
                        for ts in speech_timestamps[1:]:
                            last_end = merged_timestamps[-1]['end']
                            if ts['start'] <= last_end:
                                merged_timestamps[-1]['end'] = max(last_end, ts['end'])
                            else:
                                # Only keep segments longer than min_speech_duration_ms
                                if (merged_timestamps[-1]['end'] - merged_timestamps[-1]['start']) * 1000 / sampling_rate >= min_speech_duration_ms:
                                    merged_timestamps.append(ts)
                        
                        # Check the last segment
                        if (merged_timestamps[-1]['end'] - merged_timestamps[-1]['start']) * 1000 / sampling_rate < min_speech_duration_ms:
                            merged_timestamps.pop()
                            
                        return merged_timestamps
                    
                    return []
                
                def read_audio(path, sampling_rate=16000):
                    """Read audio from file"""
                    audio, sr = torchaudio.load(path)
                    if sr != sampling_rate:
                        resampler = torchaudio.transforms.Resample(sr, sampling_rate)
                        audio = resampler(audio)
                    return audio.squeeze()
                
                def save_audio(path, tensor, sampling_rate=16000):
                    """Save audio tensor to file"""
                    torchaudio.save(path, tensor.unsqueeze(0), sampling_rate)
                
                return vad_model, get_speech_timestamps, save_audio, read_audio
            except Exception as e:
                logger.error(f"Error loading local model: {e}")
                raise
        else:
            raise ValueError("Failed to download silero-vad model")

def ensure_wav_format(file_path):
    """
    Convert audio file to WAV format if it's not already in WAV format
    Returns the path to the WAV file (either the original or converted file)
    """
    # If the file is already a WAV file, just return the path
    if file_path.lower().endswith('.wav'):
        return file_path
    
    if not FFMPEG_AVAILABLE:
        logger.warning("FFmpeg not available, cannot convert audio format")
        return file_path
    
    try:
        # Create a temporary directory for the converted file
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.basename(file_path)
        base_name = os.path.splitext(file_name)[0]
        wav_path = os.path.join(temp_dir, f"{base_name}.wav")
        
        # Use FFmpeg to convert the file to WAV format
        logger.info(f"Converting {file_path} to WAV format")
        subprocess.run([
            'ffmpeg', 
            '-i', file_path, 
            '-acodec', 'pcm_s16le',  # Linear PCM format, 16-bit depth
            '-ar', '44100',          # 44.1kHz sample rate
            '-ac', '1',              # Mono channel
            '-y',                    # Overwrite output file if it exists
            wav_path
        ], check=True, capture_output=True)
        
        logger.info(f"Converted to WAV: {wav_path}")
        return wav_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting to WAV: {e.stderr.decode() if e.stderr else str(e)}")
        return file_path
    except Exception as e:
        logger.error(f"Unexpected error in ensure_wav_format: {str(e)}")
        return file_path

def process_audio_file(file_path, audio_id, output_folder):
    """
    Process an audio file using silero-vad to extract speech segments
    """
    logger.info(f"Processing audio file: {file_path}")
    
    # Make sure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Create a subfolder for this audio's clips
    audio_folder = os.path.join(output_folder, f"audio_{audio_id}")
    os.makedirs(audio_folder, exist_ok=True)
    
    # Convert to WAV format if needed
    wav_file_path = ensure_wav_format(file_path)
    
    try:
        if not TORCH_AVAILABLE:
            # If torch is not available, just create a single clip as a copy of the original file
            logger.warning("Torch not available, creating single clip from entire file")
            clip_path = os.path.join(audio_folder, "clip_1.wav")
            shutil.copy(wav_file_path, clip_path)
            return [clip_path]
        
        # Load the Silero VAD model
        vad_model, get_speech_timestamps, save_audio, read_audio = get_silero_vad_model()
        
        # Load the audio file
        audio = read_audio(wav_file_path, sampling_rate=16000)
        
        # Get speech timestamps
        logger.info("Detecting speech segments...")
        timestamps = get_speech_timestamps(audio, vad_model, sampling_rate=16000)
        
        # Save each speech segment as a separate clip
        logger.info(f"Saving {len(timestamps)} speech segments...")
        clip_paths = []
        
        for i, ts in enumerate(timestamps):
            clip_path = os.path.join(audio_folder, f"clip_{i+1}.wav")
            save_audio(clip_path, audio[ts['start']:ts['end']], sampling_rate=16000)
            clip_paths.append(clip_path)
        
        logger.info(f"Audio processing complete. {len(clip_paths)} clips saved.")
        
        # Clean up temporary WAV file if it was created
        if wav_file_path != file_path and os.path.exists(wav_file_path):
            try:
                os.remove(wav_file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary WAV file: {str(e)}")
                
        return clip_paths
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        # As a fallback on error, create a dummy clip (in production this should handle differently)
        try:
            clip_path = os.path.join(audio_folder, "clip_error_fallback.wav")
            shutil.copy(wav_file_path, clip_path)
            logger.warning(f"Created fallback clip due to processing error: {clip_path}")
            
            # Clean up temporary WAV file if it was created
            if wav_file_path != file_path and os.path.exists(wav_file_path):
                try:
                    os.remove(wav_file_path)
                except Exception as clean_error:
                    logger.warning(f"Failed to clean up temporary WAV file: {str(clean_error)}")
                    
            return [clip_path]
        except Exception as copy_error:
            logger.error(f"Error creating fallback clip: {str(copy_error)}")
            raise e
