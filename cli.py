import sys
import os
from core.metadata_extractor import compute_file_hashes, extract_metadata
from core.audio_processor import load_audio_signal, compute_audio_health_metrics, plot_forensic_visuals
from core.tamper_detector import run_full_forensic_audit
from core.report_generator import generate_pdf_report
from utils.audio_generator import generate_sample_audio_files


def run_cli_forensics(filepath: str, sensitivity: float = 3.5):
    print("=" * 76)
    print(" WAVESEAL AUDIO FORENSICS & TAMPER DETECTION SYSTEM - CLI")
    print("=" * 76)

    if not os.path.exists(filepath):
        print(f"[ERROR] Target audio evidence not found at: {filepath}")
        return

    print(f"[*] Ingesting Audio Evidence: {filepath}")

    # 1. Chain of custody hashes & metadata
    hashes = compute_file_hashes(filepath)
    metadata = extract_metadata(filepath)

    print("\n--- [1] EVIDENCE SPECIFICATIONS & CHAIN OF CUSTODY HASHES ---")
    print(f"  - Filename        : {metadata['filename']}")
    print(f"  - Format & Codec  : {metadata['format']} ({metadata['subtype']})")
    print(f"  - Duration        : {metadata['duration_sec']} seconds")
    print(f"  - Sample Rate     : {metadata['sample_rate']} Hz")
    print(f"  - Channels        : {metadata['channels']}")
    print(f"  - Bitrate         : {metadata['bitrate_kbps']} kbps")
    print(f"  - MD5 Hash        : {hashes['md5']}")
    print(f"  - SHA-1 Hash      : {hashes['sha1']}")
    print(f"  - SHA-256 Hash    : {hashes['sha256']}")
    print(f"  - SHA-512 Hash    : {hashes['sha512'][:48]}...")

    if metadata['suspicious_flags']:
        print("\n  [!] CONTAINER / METADATA ALERTS:")
        for flag in metadata['suspicious_flags']:
            print(f"      - {flag}")

    # 2. Audio loading & physical health
    print("\n[*] Decoding audio signal and evaluating physical metrics...")
    y, sr = load_audio_signal(filepath)
    health = compute_audio_health_metrics(y, sr)
    print(f"  - Peak Amplitude  : {health['peak_amp']:.4f} FS")
    print(f"  - RMS Level       : {health['rms']:.4f}")
    print(f"  - Digital Clipping: {health['clipping_pct']:.2f}% ({health['clipped_samples']} samples)")
    print(f"  - Dynamic Range   : {health['crest_factor_db']:.1f} dB")

    # 3. Tamper audit
    print("\n[*] Executing multi-pillar forensic inspection algorithms...")
    audit_results = run_full_forensic_audit(y, sr, metadata, sensitivity=sensitivity)

    print("\n--- [2] FORENSIC INTEGRITY VERDICT ---")
    print(f"  - Determination   : {audit_results['verdict']} [{audit_results['verdict_level']}]")
    print(f"  - Authenticity    : {audit_results['authenticity_score']:.1f}% / 100.0%")
    print(f"  - Summary         : {audit_results['verdict_desc']}")

    print("\n--- [3] MULTI-PILLAR FORENSIC EVALUATION ---")
    pillars = audit_results.get("pillars", {})
    for p_key, p_val in pillars.items():
        print(f"  - {p_val['name']:<28}: {p_val['score']:>5.1f}% [{p_val['status'].upper():<7}] (Weight: {p_val['weight']}) -> {p_val['detail']}")

    if audit_results['anomalies_summary']:
        print("\n  [!] FORENSIC ANOMALIES IDENTIFIED:")
        for idx, anomaly in enumerate(audit_results['anomalies_summary'], 1):
            print(f"      [{idx}] {anomaly}")

    # 4. Save visual plot
    output_plot = "forensic_spectrogram.png"
    plot_forensic_visuals(y, sr, audit_results=audit_results, output_path=output_plot)
    print(f"\n[+] Rendered Multi-Panel Forensic Evidence Chart to: {output_plot}")

    # 5. Export PDF report
    output_pdf = "forensic_report.pdf"
    generate_pdf_report(metadata, hashes, audit_results, chart_image_path=output_plot, output_path=output_pdf)
    print(f"[+] Compiled Certified PDF Forensic Audit Report to: {output_pdf}")
    print("=" * 76)


if __name__ == "__main__":
    target_path = None
    sensitivity = 3.5

    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            sensitivity = float(sys.argv[2])
        except ValueError:
            pass

    if not target_path:
        print("[*] No target file specified. Generating forensic benchmark samples...")
        sample_paths = generate_sample_audio_files()
        target_path = sample_paths["tampered"]
        print(f"[*] Defaulting to calibrated tampered test recording: {target_path}\n")

    run_cli_forensics(target_path, sensitivity=sensitivity)
