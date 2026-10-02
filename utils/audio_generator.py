import os
import numpy as np
import soundfile as sf

def generate_sample_audio_files(output_dir: str = "samples") -> dict:
    """
    Generate synthetic test audio clips:
    1. authentic_sample.wav - A clean multi-tone synthetic speech-like recording with continuous ambient background noise.
    2. tampered_sample.wav - A modified recording with an abrupt cut/splice, an inserted high-frequency tone burst, and a dead digital silence gap.
    """
    os.makedirs(output_dir, exist_ok=True)
    sr = 22050
    duration = 5.0 # seconds
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Base audio: Smooth multi-tonal speech simulation
    base_signal = 0.5 * np.sin(2 * np.pi * 300 * t) + 0.25 * np.sin(2 * np.pi * 600 * t)
    # Continuous low-frequency speech envelope (no abrupt step drops)
    envelope = 0.4 + 0.3 * np.sin(2 * np.pi * 0.8 * t)
    base_signal = base_signal * envelope

    # Constant ambient background noise floor
    np.random.seed(42)
    ambient_noise = 0.03 * np.random.normal(0, 1, len(t))
    
    # Authentic Recording
    authentic_audio = base_signal + ambient_noise
    authentic_path = os.path.join(output_dir, "authentic_sample.wav")
    sf.write(authentic_path, authentic_audio, sr, subtype='PCM_16')

    # Tampered Recording
    tampered_audio = authentic_audio.copy()
    
    # Splice 1: Insert an artificial splice at t = 2.0s to 2.5s with different frequency and loud noise floor shift
    t_splice = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
    foreign_insert = 0.8 * np.sin(2 * np.pi * 1750 * t_splice) + 0.15 * np.random.normal(0, 1, len(t_splice))
    
    splice_start = int(2.0 * sr)
    splice_end = splice_start + len(foreign_insert)
    tampered_audio[splice_start:splice_end] = foreign_insert
    
    # Splice 2: Insert dead digital silence gap at t = 3.8s to 4.3s
    silence_start = int(3.8 * sr)
    silence_end = int(4.3 * sr)
    tampered_audio[silence_start:silence_end] = 0.0

    tampered_path = os.path.join(output_dir, "tampered_sample.wav")
    sf.write(tampered_path, tampered_audio, sr, subtype='PCM_16')

    return {
        "authentic": authentic_path,
        "tampered": tampered_path
    }

if __name__ == "__main__":
    paths = generate_sample_audio_files()
    print("Generated sample files:", paths)
