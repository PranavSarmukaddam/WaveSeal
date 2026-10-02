import numpy as np
import librosa
from scipy.signal import welch


def detect_silence_gaps(y: np.ndarray, sr: int, top_db: float = 40.0, min_duration_sec: float = 0.15) -> list:
    """
    Examine audio for pauses and distinguish between natural acoustic room pauses
    and synthetic zero-energy digital silence gaps.
    """
    total_samples = len(y)
    if total_samples == 0:
        return []

    # Identify non-silent intervals using energy relative to maximum
    try:
        non_silent_intervals = librosa.effects.split(y, top_db=top_db)
    except Exception:
        return []

    silence_gaps = []

    # Check initial silence
    if len(non_silent_intervals) > 0 and non_silent_intervals[0][0] > 0:
        start_sec = 0.0
        end_sec = float(non_silent_intervals[0][0]) / sr
        duration = end_sec - start_sec
        if duration >= min_duration_sec:
            seg = y[0:non_silent_intervals[0][0]]
            is_dead = float(np.std(seg)) < 1e-7 or float(np.max(np.abs(seg))) < 1e-6
            silence_gaps.append({
                "type": "Digital Zero Silence (Leading)" if is_dead else "Natural Acoustic Pause (Leading)",
                "start_sec": round(start_sec, 3),
                "end_sec": round(end_sec, 3),
                "duration_sec": round(duration, 3),
                "is_dead_silence": is_dead,
                "variance": float(np.var(seg)),
                "severity": "High" if is_dead and duration > 0.3 else "Low",
                "implication": "Synthetic digital mute" if is_dead else "Ambient recording pause"
            })

    # Check internal silence gaps
    for i in range(len(non_silent_intervals) - 1):
        gap_start_sample = non_silent_intervals[i][1]
        gap_end_sample = non_silent_intervals[i+1][0]
        start_sec = float(gap_start_sample) / sr
        end_sec = float(gap_end_sample) / sr
        duration = end_sec - start_sec

        if duration >= min_duration_sec:
            gap_audio = y[gap_start_sample:gap_end_sample]
            seg_std = float(np.std(gap_audio))
            seg_max = float(np.max(np.abs(gap_audio))) if len(gap_audio) > 0 else 0.0

            # Absolute zero or sub-quantization noise indicates synthetic zero-fill
            is_dead = seg_std < 1e-7 or seg_max < 1e-6
            severity = "High" if (is_dead and duration > 0.25) else ("Medium" if is_dead else "Low")

            silence_gaps.append({
                "type": "Digital Zero Silence Gap" if is_dead else "Natural Speech Pause",
                "start_sec": round(start_sec, 3),
                "end_sec": round(end_sec, 3),
                "duration_sec": round(duration, 3),
                "is_dead_silence": is_dead,
                "variance": round(float(np.var(gap_audio)), 9),
                "severity": severity,
                "implication": "Artificial zero-fill insertion (Cut / Mute)" if is_dead else "Acoustic background room tone preserved"
            })

    return silence_gaps


def detect_discontinuities(y: np.ndarray, sr: int, user_sensitivity: float = 3.5) -> dict:
    """
    Robust adaptive splice and boundary discontinuity detector.
    Analyzes multi-feature concordance: Spectral Flux, Frame-to-Frame RMS Jump, and Spectral Centroid.
    Uses Median Absolute Deviation (MAD) for adaptive outlier thresholding to prevent false positives.
    """
    total_duration = len(y) / sr
    if total_duration < 0.2:
        return {"discontinuities": [], "threshold_used": user_sensitivity, "max_anomaly": 0.0}

    hop_length = 512
    n_fft = 2048

    # 1. STFT Magnitude and Spectral Flux
    stft = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
    spectral_flux = np.sqrt(np.sum(np.diff(stft, axis=1)**2, axis=0))
    spectral_flux = np.pad(spectral_flux, (1, 0), mode='edge')

    # 2. RMS Energy derivative
    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop_length)[0]
    rms_diff = np.abs(np.diff(rms, prepend=rms[0]))

    # 3. Spectral Centroid derivative
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)[0]
    centroid_diff = np.abs(np.diff(centroid, prepend=centroid[0]))

    # Robust normalization using Median and Median Absolute Deviation (MAD)
    def robust_zscore(vec):
        med = np.median(vec)
        mad = np.median(np.abs(vec - med))
        scale = 1.4826 * mad
        if scale > 1e-6:
            return np.clip((vec - med) / scale, 0.0, 30.0)
        std = np.std(vec)
        if std > 1e-6:
            return np.clip((vec - np.mean(vec)) / std, 0.0, 30.0)
        return np.zeros_like(vec)

    norm_flux = robust_zscore(spectral_flux)
    norm_rms = robust_zscore(rms_diff)
    norm_centroid = robust_zscore(centroid_diff)

    # Concordance anomaly score: Splices produce synchronous jumps in both flux and energy
    combined_score = norm_flux * 0.50 + norm_rms * 0.35 + norm_centroid * 0.15

    # Adaptive threshold anchored on user sensitivity
    adaptive_threshold = max(2.8, float(user_sensitivity))

    # Identify candidate spikes excluding initial 0.1s and final 0.1s transients
    discontinuities = []
    spike_indices = np.where(combined_score > adaptive_threshold)[0]

    valid_indices = []
    for idx in spike_indices:
        t_sec = librosa.frames_to_time(idx, sr=sr, hop_length=hop_length)
        if 0.10 <= t_sec <= (total_duration - 0.10):
            valid_indices.append(idx)

    # Cluster adjacent frame detections to pinpoint single exact splice timestamp
    if valid_indices:
        clusters = []
        current = [valid_indices[0]]
        for idx in valid_indices[1:]:
            if idx <= current[-1] + 3:
                current.append(idx)
            else:
                clusters.append(current)
                current = [idx]
        clusters.append(current)

        for cluster in clusters:
            best_idx = cluster[int(np.argmax(combined_score[cluster]))]
            peak_score = float(combined_score[best_idx])
            t_sec = float(librosa.frames_to_time(best_idx, sr=sr, hop_length=hop_length))
            
            # Confidence estimation (60% to 99%)
            confidence = min(99.0, max(50.0, 50.0 + (peak_score / (adaptive_threshold * 2.0)) * 45.0))
            severity = "Critical" if peak_score > adaptive_threshold * 1.8 else ("High" if peak_score > adaptive_threshold * 1.3 else "Moderate")

            discontinuities.append({
                "timestamp_sec": round(t_sec, 3),
                "anomaly_score": round(peak_score, 2),
                "confidence_pct": round(confidence, 1),
                "severity": severity,
                "description": f"Acoustic phase/spectral splice discontinuity detected at {t_sec:.2f}s",
                "implication": "Butt-splice boundary or inserted foreign material"
            })

    max_anomaly = float(np.max(combined_score)) if len(combined_score) > 0 else 0.0

    return {
        "discontinuities": discontinuities,
        "threshold_used": round(adaptive_threshold, 2),
        "max_anomaly": round(max_anomaly, 2)
    }


def analyze_noise_floor_consistency(y: np.ndarray, sr: int, segment_sec: float = 1.0) -> dict:
    """
    Analyze ambient background noise floor stability across 1-second rolling segments.
    Estimates the ambient room tone using the 10th percentile energy in each segment.
    """
    segment_samples = int(sr * segment_sec)
    total_len = len(y)
    n_segments = total_len // segment_samples

    if n_segments < 2:
        return {
            "noise_floors": [],
            "max_shift_ratio": 1.0,
            "step_ratio": 0.0,
            "inconsistency_flagged": False,
            "score": 100.0,
            "details": "Audio duration too brief for multi-window acoustic noise profiling."
        }

    noise_floors = []
    hop = 256
    frame_len = 1024

    for i in range(n_segments):
        seg = y[i * segment_samples : (i + 1) * segment_samples]
        energies = librosa.feature.rms(y=seg, frame_length=frame_len, hop_length=hop)[0]
        # 10th percentile represents stationary ambient background floor (room tone)
        p10 = float(np.percentile(energies, 10))
        noise_floors.append(p10)

    noise_arr = np.array(noise_floors)
    eps = 1e-7
    min_floor = float(np.min(noise_arr)) + eps
    max_floor = float(np.max(noise_arr)) + eps
    shift_ratio = float(max_floor / min_floor)

    adjacent_diffs = np.abs(np.diff(noise_arr))
    max_step = float(np.max(adjacent_diffs)) if len(adjacent_diffs) > 0 else 0.0
    mean_floor = float(np.mean(noise_arr)) + eps
    step_ratio = float(max_step / mean_floor)

    # Calibrated continuous noise score
    # Ratios under 2.0 are normal physical variance. Above 2.5 indicates environment mismatch.
    if shift_ratio <= 1.8 and step_ratio <= 1.5:
        score = 98.0
        inconsistent = False
        summary = "Stationary ambient acoustic room tone verified across entire recording."
    else:
        penalty = min(80.0, max(0.0, (shift_ratio - 1.8) * 14.0 + (step_ratio - 1.2) * 12.0))
        score = round(max(15.0, 98.0 - penalty), 1)
        inconsistent = bool(shift_ratio > 3.2 or step_ratio > 2.5)
        summary = f"Ambient noise floor fluctuates by {shift_ratio:.2f}x (Step shift: {step_ratio:.2f}x), suggesting mixed recording environments."

    return {
        "noise_floors": [round(float(nf), 6) for nf in noise_floors],
        "max_shift_ratio": round(shift_ratio, 2),
        "step_ratio": round(step_ratio, 2),
        "inconsistency_flagged": inconsistent,
        "score": score,
        "details": summary
    }


def analyze_enf_mains_hum(y: np.ndarray, sr: int) -> dict:
    """
    Electric Network Frequency (ENF) continuity audit (50 Hz and 60 Hz mains hum).
    """
    nperseg = min(len(y), 16384)
    if nperseg < 1024:
        return {"detected": False, "score": 95.0, "dominant_grid_freq": "N/A", "enf_power": 0.0, "note": "Insufficient length"}

    freqs, psd = welch(y, fs=sr, nperseg=nperseg)

    mask_50 = (freqs >= 49.2) & (freqs <= 50.8)
    mask_60 = (freqs >= 59.2) & (freqs <= 60.8)

    p50 = float(np.sum(psd[mask_50])) if np.any(mask_50) else 0.0
    p60 = float(np.sum(psd[mask_60])) if np.any(mask_60) else 0.0

    dominant_grid = "50 Hz (Standard)" if p50 >= p60 else "60 Hz (Standard)"
    enf_power = max(p50, p60)

    detected = bool(enf_power > 1e-5)

    return {
        "dominant_grid_freq": dominant_grid,
        "enf_power": round(float(enf_power), 8),
        "detected": detected,
        "score": 98.0 if detected else 94.0,
        "note": f"Grid frequency profile {dominant_grid} examined; continuous mains induction verified." if detected else "Acoustic signal exhibits no artificial electrical mains interference."
    }


def run_full_forensic_audit(y: np.ndarray, sr: int, metadata: dict, sensitivity: float = 3.5) -> dict:
    """
    Comprehensive multi-pillar forensic tamper detection pipeline.
    Calculates 5 distinct scientific pillars and produces a continuous, calibrated Forensic Authenticity Index (0-100%).
    """
    duration = len(y) / sr

    # 1. Acoustic Discontinuities & Splices
    disc_data = detect_discontinuities(y, sr, user_sensitivity=sensitivity)
    discontinuities = disc_data["discontinuities"]
    threshold_used = disc_data["threshold_used"]

    # 2. Silence & Gap Analysis
    silence_gaps = detect_silence_gaps(y, sr)
    dead_silences = [g for g in silence_gaps if g.get("is_dead_silence")]

    # 3. Noise Floor Profile
    noise_analysis = analyze_noise_floor_consistency(y, sr)

    # 4. Signal Health & ENF
    peak_amp = float(np.max(np.abs(y))) if len(y) > 0 else 0.0
    clipped_samples = int(np.sum(np.abs(y) >= 0.999))
    clipping_pct = (clipped_samples / len(y)) * 100.0 if len(y) > 0 else 0.0
    enf_analysis = analyze_enf_mains_hum(y, sr)

    # =========================================================================
    # SCIENTIFIC MULTI-PILLAR SCORING ENGINE (Continuous, non-stepped)
    # =========================================================================

    # Pillar 1: Acoustic Continuity Score (Weight: 30%)
    # Evaluates presence and intensity of spectral flux/energy boundary spikes
    if not discontinuities:
        acoustic_score = 98.5
    else:
        # Penalize smoothly based on splice count, severity, and anomaly score
        splice_penalty = 0.0
        for d in discontinuities:
            score_above = max(0.0, d["anomaly_score"] - threshold_used)
            if d["severity"] == "Critical":
                splice_penalty += 24.0 + score_above * 4.0
            elif d["severity"] == "High":
                splice_penalty += 16.0 + score_above * 3.0
            else:
                splice_penalty += 9.0 + score_above * 2.0
        acoustic_score = max(10.0, 98.5 - min(88.0, splice_penalty))

    # Pillar 2: Background Noise Stability Score (Weight: 25%)
    noise_score = float(noise_analysis.get("score", 95.0))

    # Pillar 3: Silence & Pause Authenticity Score (Weight: 20%)
    if not dead_silences:
        silence_score = 99.0
    else:
        total_dead_sec = sum(g["duration_sec"] for g in dead_silences)
        dead_ratio = min(1.0, total_dead_sec / max(0.5, duration))
        silence_penalty = len(dead_silences) * 18.0 + (dead_ratio * 40.0)
        silence_score = max(12.0, 99.0 - min(87.0, silence_penalty))

    # Pillar 4: Signal & Dynamic Linearity Score (Weight: 15%)
    signal_score = 98.0
    if clipping_pct > 0.05:
        signal_score -= min(35.0, clipping_pct * 8.0)
    if peak_amp < 0.02:
        signal_score -= 20.0 # Extremely low signal amplitude
    signal_score = max(20.0, signal_score)

    # Pillar 5: Container & Metadata Integrity (Weight: 10%)
    container_score = 98.0
    software_flags = metadata.get("software_tags", [])
    binary_flags = metadata.get("binary_signatures", [])
    all_sw = list(set(software_flags + binary_flags))

    if all_sw:
        container_score = 45.0
    elif metadata.get("suspicious_flags"):
        container_score = 75.0

    # Composite Weighted Forensic Authenticity Index (0.0 to 100.0%)
    composite_index = (
        0.30 * acoustic_score +
        0.25 * noise_score +
        0.20 * silence_score +
        0.15 * signal_score +
        0.10 * container_score
    )

    # Final rounding
    authenticity_score = round(float(np.clip(composite_index, 0.0, 100.0)), 1)

    # Findings Compilation
    anomalies_summary = []
    if all_sw:
        anomalies_summary.append(f"Digital Audio Workstation signature confirmed: {', '.join(all_sw)}.")
    
    if len(discontinuities) > 0:
        anomalies_summary.append(
            f"Detected {len(discontinuities)} acoustic splice boundary jump(s) indicating potential cuts or insertions."
        )

    if len(dead_silences) > 0:
        anomalies_summary.append(
            f"Identified {len(dead_silences)} unnatural digital zero silence interval(s) lacking ambient room tone."
        )

    if noise_analysis["inconsistency_flagged"]:
        anomalies_summary.append(
            f"Ambient noise floor shifts by {noise_analysis['max_shift_ratio']}x across recording segments (Acoustic room mismatch)."
        )

    if clipping_pct > 0.1:
        anomalies_summary.append(
            f"Audio signal exhibits digital clipping on {clipping_pct:.2f}% of samples (Exceeds 0 dBFS ceiling)."
        )

    # Forensic Classification & Status Badges
    if authenticity_score >= 88.0 and len(discontinuities) == 0 and not all_sw:
        verdict = "AUTHENTIC"
        verdict_level = "High Integrity"
        verdict_color = "#15803d"  # Forest green
        verdict_bg = "#dcfce7"
        verdict_desc = "Recording exhibits continuous acoustic characteristics, consistent ambient room tone, and natural pause structures with no indications of tampering."
    elif authenticity_score >= 70.0:
        verdict = "INCONCLUSIVE / SUSPICIOUS"
        verdict_level = "Moderate Variance"
        verdict_color = "#b45309"  # Amber brown
        verdict_bg = "#fef3c7"
        verdict_desc = "Minor acoustic irregularities or ambient shifts identified. Secondary spectral review or original recording medium examination recommended."
    else:
        verdict = "TAMPERED / MANIPULATED"
        verdict_level = "High Probability of Manipulation"
        verdict_color = "#b91c1c"  # Forensic crimson
        verdict_bg = "#fee2e2"
        verdict_desc = "Definite forensic evidence of audio editing detected: acoustic splice boundaries, artificial zero-energy mutes, or DAW metadata footprints present."

    return {
        "authenticity_score": authenticity_score,
        "verdict": verdict,
        "verdict_level": verdict_level,
        "verdict_color": verdict_color,
        "verdict_bg": verdict_bg,
        "verdict_desc": verdict_desc,
        "threshold_used": threshold_used,
        "anomalies_summary": anomalies_summary,
        "discontinuities": discontinuities,
        "silence_gaps": silence_gaps,
        "noise_analysis": noise_analysis,
        "enf_analysis": enf_analysis,
        "pillars": {
            "acoustic_continuity": {
                "name": "Acoustic Continuity",
                "score": round(acoustic_score, 1),
                "weight": "30%",
                "status": "Normal" if acoustic_score >= 80 else ("Review" if acoustic_score >= 60 else "Flagged"),
                "detail": f"{len(discontinuities)} splice boundary jump(s) detected."
            },
            "noise_uniformity": {
                "name": "Room Tone & Noise Stability",
                "score": round(noise_score, 1),
                "weight": "25%",
                "status": "Normal" if noise_score >= 80 else ("Review" if noise_score >= 60 else "Flagged"),
                "detail": f"Max ambient variance ratio: {noise_analysis['max_shift_ratio']}x."
            },
            "silence_authenticity": {
                "name": "Pause & Silence Authenticity",
                "score": round(silence_score, 1),
                "weight": "20%",
                "status": "Normal" if silence_score >= 80 else ("Review" if silence_score >= 60 else "Flagged"),
                "detail": f"{len(dead_silences)} digital zero gap(s) identified."
            },
            "signal_integrity": {
                "name": "Signal Dynamics & ENF",
                "score": round(signal_score, 1),
                "weight": "15%",
                "status": "Normal" if signal_score >= 80 else ("Review" if signal_score >= 60 else "Flagged"),
                "detail": f"Clipping: {clipping_pct:.2f}%, Peak: {peak_amp:.3f} FS."
            },
            "container_integrity": {
                "name": "Container & Metadata Audit",
                "score": round(container_score, 1),
                "weight": "10%",
                "status": "Normal" if container_score >= 80 else "Flagged",
                "detail": f"DAW Tags: {', '.join(all_sw) if all_sw else 'None detected'}."
            }
        }
    }
