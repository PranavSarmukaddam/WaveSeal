import os
import numpy as np
import soundfile as sf
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_audio_signal(filepath: str, target_sr: int = 22050):
    """
    Robust forensic audio loader supporting any format (WAV, MP3, FLAC, OGG, M4A, etc.).
    Falls back gracefully across multiple audio decoding backends.
    Converts multi-channel inputs to single-channel mono.
    """
    y = None
    sr = target_sr

    # Attempt 1: SoundFile (Fast C-based library)
    try:
        data, file_sr = sf.read(filepath, dtype='float32')
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        if target_sr is not None and file_sr != target_sr:
            data = librosa.resample(data, orig_sr=file_sr, target_sr=target_sr)
            sr = target_sr
        else:
            sr = file_sr
        y = data
    except Exception:
        pass

    # Attempt 2: Librosa fallback (uses audioread / ffmpeg underneath)
    if y is None:
        try:
            y, sr = librosa.load(filepath, sr=target_sr, mono=True)
        except Exception:
            pass

    # Attempt 3: PyAV fallback (bundles its own ffmpeg — works on Streamlit Cloud
    #             without needing system ffmpeg; handles M4A, MP3, AAC, etc.)
    if y is None:
        try:
            import av
            container = av.open(filepath)
            resampler = av.AudioResampler(
                format='fltp', layout='mono', rate=target_sr
            )
            chunks = []
            for frame in container.decode(audio=0):
                # resample() returns a LIST of AudioFrame objects — must iterate
                for resampled_frame in resampler.resample(frame):
                    chunks.append(resampled_frame.to_ndarray().flatten())
            # Flush any remaining samples buffered in the resampler
            for resampled_frame in resampler.resample(None):
                chunks.append(resampled_frame.to_ndarray().flatten())
            container.close()
            if chunks:
                y = np.concatenate(chunks).astype(np.float32)
                sr = target_sr
        except Exception:
            pass

    # Attempt 4: Pydub fallback (needs system ffmpeg; may work on some envs)
    if y is None:
        try:
            from pydub import AudioSegment
            audio_seg = AudioSegment.from_file(filepath)
            audio_seg = audio_seg.set_channels(1).set_frame_rate(target_sr)
            raw = np.array(audio_seg.get_array_of_samples(), dtype=np.float32)
            max_val = float(2 ** (audio_seg.sample_width * 8 - 1))
            y = raw / (max_val + 1e-9)
            sr = target_sr
        except Exception:
            pass

    # Attempt 3: Standard wave module fallback (for standard PCM WAVs)
    if y is None and filepath.lower().endswith('.wav'):
        try:
            import wave
            with wave.open(filepath, 'rb') as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_data = wf.readframes(n_frames)
                
                if sampwidth == 2:
                    int_data = np.frombuffer(raw_data, dtype=np.int16)
                    float_data = int_data.astype(np.float32) / 32768.0
                elif sampwidth == 1:
                    int_data = np.frombuffer(raw_data, dtype=np.uint8)
                    float_data = (int_data.astype(np.float32) - 128.0) / 128.0
                else:
                    int_data = np.frombuffer(raw_data, dtype=np.int32)
                    float_data = int_data.astype(np.float32) / 2147483648.0

                if n_channels > 1:
                    float_data = float_data.reshape(-1, n_channels).mean(axis=1)

                if target_sr and framerate != target_sr:
                    y = librosa.resample(float_data, orig_sr=framerate, target_sr=target_sr)
                    sr = target_sr
                else:
                    y = float_data
                    sr = framerate
        except Exception:
            pass

    if y is None or len(y) == 0:
        ext = os.path.splitext(filepath)[1].upper() or "unknown format"
        raise ValueError(
            f"Unable to decode audio stream from '{os.path.basename(filepath)}' ({ext}). "
            f"All backends (SoundFile, Librosa, pydub, wave) failed. "
            f"Try converting the file to WAV (16-bit PCM) before uploading."
        )

    # Ensure float32 representation and remove non-finite entries
    y = np.nan_to_num(y.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)

    return y, sr


def compute_audio_health_metrics(y: np.ndarray, sr: int) -> dict:
    """
    Compute physical audio signal health: clipping percentage, dynamic range, and RMS.
    """
    total_samples = len(y)
    if total_samples == 0:
        return {"clipping_pct": 0.0, "peak_amp": 0.0, "crest_factor_db": 0.0, "rms": 0.0}

    peak_amp = float(np.max(np.abs(y)))
    rms = float(np.sqrt(np.mean(y**2)))
    clipped_samples = int(np.sum(np.abs(y) >= 0.999))
    clipping_pct = round((clipped_samples / total_samples) * 100.0, 3)

    crest_factor_db = round(20.0 * np.log10(peak_amp / (rms + 1e-9)), 2) if rms > 0 else 0.0

    return {
        "clipping_pct": clipping_pct,
        "clipped_samples": clipped_samples,
        "peak_amp": round(peak_amp, 4),
        "crest_factor_db": crest_factor_db,
        "rms": round(rms, 4)
    }


def compute_spectrogram(y: np.ndarray, sr: int, n_fft: int = 2048, hop_length: int = 512):
    """
    Compute Short-Time Fourier Transform (STFT) magnitude in dB.
    """
    stft = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
    stft_db = librosa.amplitude_to_db(np.abs(stft), ref=np.max)
    times = librosa.frames_to_time(np.arange(stft_db.shape[1]), sr=sr, hop_length=hop_length)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    return stft_db, times, freqs


def extract_frame_features(y: np.ndarray, sr: int, frame_length: int = 2048, hop_length: int = 512):
    """
    Extract frame-by-frame RMS Energy, Spectral Centroid, and Spectral Flux.
    """
    stft = np.abs(librosa.stft(y, n_fft=frame_length, hop_length=hop_length))
    spectral_flux = np.sqrt(np.sum(np.diff(stft, axis=1)**2, axis=0))
    spectral_flux = np.pad(spectral_flux, (1, 0), mode='edge')

    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=frame_length, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    return {
        "times": times,
        "rms": rms,
        "spectral_flux": spectral_flux,
        "centroid": centroid
    }


def plot_forensic_visuals(y: np.ndarray, sr: int, audit_results: dict = None, output_path: str = None):
    """
    Generate professional forensic inspection charts:
    Panel 1: Audio Waveform with splice markers.
    Panel 2: Calibrated STFT Spectrogram (dB).
    Panel 3: Frame Anomaly Score (Spectral Flux & RMS Discontinuity) with Decision Boundary.
    Panel 4: Ambient Noise Floor Progression across segments.
    """
    fig, axes = plt.subplots(4, 1, figsize=(13, 10), sharex=False, gridspec_kw={'height_ratios': [1.1, 1.4, 1.0, 0.9]})
    
    # Clean professional forensic styling
    fig.patch.set_facecolor('#ffffff')

    for ax in axes:
        ax.set_facecolor('#f8fafc')
        ax.tick_params(colors='#334155', labelsize=8)
        for spine in ax.spines.values():
            spine.set_color('#cbd5e1')
            spine.set_linewidth(1.0)
        ax.grid(True, linestyle=':', alpha=0.6, color='#94a3b8')

    duration = len(y) / sr
    times = np.linspace(0, duration, len(y))

    # Panel 1: Time-Domain Waveform
    axes[0].plot(times, y, color='#0284c7', linewidth=0.7, alpha=0.9, label="Signal Amplitude")
    axes[0].set_ylabel("Amplitude", color='#0f172a', fontsize=9, fontweight='bold')
    axes[0].set_title("1. TIME-DOMAIN WAVEFORM & DETECTED SPLICE LOCATIONS", color='#0f172a', fontsize=10, fontweight='bold', loc='left', pad=6)
    axes[0].set_xlim(0, duration)
    axes[0].set_ylim(-1.05, 1.05)

    # Panel 2: STFT Spectrogram
    stft_db, spec_times, freqs = compute_spectrogram(y, sr)
    mesh = axes[1].pcolormesh(spec_times, freqs, stft_db, cmap='magma', shading='auto', vmin=-80, vmax=0)
    axes[1].set_ylabel("Frequency (Hz)", color='#0f172a', fontsize=9, fontweight='bold')
    axes[1].set_title("2. SHORT-TIME FOURIER TRANSFORM (STFT) MAGNITUDE SPECTROGRAM (dB)", color='#0f172a', fontsize=10, fontweight='bold', loc='left', pad=6)
    axes[1].set_xlim(0, duration)
    cbar = fig.colorbar(mesh, ax=axes[1], orientation='vertical', pad=0.015, aspect=20)
    cbar.set_label("dBFS", color='#334155', fontsize=8)
    cbar.ax.tick_params(labelsize=7, colors='#334155')

    # Panel 3: Inter-Frame Anomaly Score (Spectral Flux + RMS Jump)
    feat = extract_frame_features(y, sr)
    flux = feat["spectral_flux"]
    norm_flux = (flux - np.mean(flux)) / (np.std(flux) + 1e-9)
    rms_diff = np.abs(np.diff(feat["rms"], prepend=feat["rms"][0]))
    norm_rms_diff = (rms_diff - np.mean(rms_diff)) / (np.std(rms_diff) + 1e-9)
    combined_anomaly = np.clip(norm_flux * 0.6 + norm_rms_diff * 0.4, 0, None)

    axes[2].plot(feat["times"], combined_anomaly, color='#d97706', linewidth=1.0, label="Discontinuity Index")
    threshold_val = audit_results.get("threshold_used", 3.2) if audit_results else 3.2
    axes[2].axhline(y=threshold_val, color='#dc2626', linestyle='--', linewidth=1.2, label=f"Detection Threshold ({threshold_val:.1f})")
    axes[2].set_ylabel("Anomaly Index", color='#0f172a', fontsize=9, fontweight='bold')
    axes[2].set_title("3. INTER-FRAME SPECTRAL & ENERGY DISCONTINUITY CURVE", color='#0f172a', fontsize=10, fontweight='bold', loc='left', pad=6)
    axes[2].set_xlim(0, duration)
    axes[2].legend(loc="upper right", fontsize=8, framealpha=0.9)

    # Panel 4: Ambient Noise Floor Stability
    noise_info = audit_results.get("noise_analysis", {}) if audit_results else {}
    noise_floors = noise_info.get("noise_floors", [])
    if noise_floors:
        seg_times = np.linspace(0.5, duration - 0.5, len(noise_floors))
        axes[3].step(seg_times, noise_floors, where='mid', color='#475569', linewidth=1.4, label="Acoustic Noise Floor (10th percentile)")
        axes[3].set_ylabel("Noise Energy", color='#0f172a', fontsize=9, fontweight='bold')
        axes[3].set_title("4. AMBIENT BACKGROUND NOISE FLOOR STEP PROGRESSION", color='#0f172a', fontsize=10, fontweight='bold', loc='left', pad=6)
        axes[3].legend(loc="upper right", fontsize=8, framealpha=0.9)
    else:
        axes[3].text(0.5, 0.5, "Duration insufficient for multi-segment noise floor profiling", ha='center', va='center', color='#64748b', fontsize=9)
    
    axes[3].set_xlabel("Time (seconds)", color='#0f172a', fontsize=9, fontweight='bold')
    axes[3].set_xlim(0, duration)

    # Mark Detected Splice Events Across Panels
    if audit_results and "discontinuities" in audit_results:
        discs = audit_results["discontinuities"]
        for disc in discs:
            t_sec = disc["timestamp_sec"]
            for ax_idx in range(3):
                axes[ax_idx].axvline(x=t_sec, color='#dc2626', linestyle='--', linewidth=1.3, alpha=0.9)
            axes[0].text(t_sec, 0.75, f" Cut @ {t_sec:.2f}s", color='#991b1b', fontsize=8, fontweight='bold',
                         bbox=dict(boxstyle="square,pad=0.2", fc="#fee2e2", ec="#dc2626", lw=0.8))

    # Mark Silence Gaps
    if audit_results and "silence_gaps" in audit_results:
        for gap in audit_results["silence_gaps"]:
            if gap.get("is_dead_silence"):
                for ax_idx in range(2):
                    axes[ax_idx].axvspan(gap["start_sec"], gap["end_sec"], color='#ef4444', alpha=0.18)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='#ffffff')
        plt.close(fig)
        return output_path

    return fig
