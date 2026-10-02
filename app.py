import os
import tempfile
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("Agg")

from core.metadata_extractor import compute_file_hashes, extract_metadata
from core.audio_processor import load_audio_signal, compute_spectrogram, compute_audio_health_metrics
from core.tamper_detector import run_full_forensic_audit
from core.report_generator import generate_pdf_report
from utils.audio_generator import generate_sample_audio_files

st.set_page_config(
    page_title="WaveSeal - Audio Forensics",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* Base typography and background */
html, body, [class*="css"] {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif !important;
    background-color: #f8fafc !important;
    color: #0f172a !important;
}

.stApp {
    background-color: #f8fafc !important;
}

/* Constrain width so layout never looks stretched */
.block-container {
    max-width: 1140px !important;
    padding-top: 1.25rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    margin: 0 auto !important;
}

#MainMenu, footer, header {
    visibility: hidden !important;
}

/* Top Navigation Bar */
.ws-navbar {
    background-color: #0f172a;
    border-radius: 8px;
    padding: 14px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 22px;
}
.ws-nav-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}
.ws-logo-mark {
    background-color: #ffffff;
    color: #0f172a;
    font-weight: 900;
    font-size: 13px;
    letter-spacing: 0.5px;
    width: 28px;
    height: 28px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.ws-nav-title {
    color: #ffffff;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.2px;
}
.ws-nav-sub {
    color: #94a3b8;
    font-size: 12.5px;
    margin-left: 6px;
    font-weight: 400;
}
.ws-nav-tag {
    background-color: #1e293b;
    color: #cbd5e1;
    font-size: 11.5px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid #334155;
}

/* Card titles */
.card-heading {
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 10px 0;
}

/* Native containers styled cleanly */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
    margin-bottom: 14px !important;
}

/* Native file uploader */
[data-testid="stFileUploader"] {
    background: #f8fafc !important;
    border: 1.5px dashed #cbd5e1 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
}
[data-testid="stFileUploader"] button {
    background: #0f172a !important;
    color: #f8fafc !important;
    border: none !important;
    border-radius: 5px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
}

/* Clean buttons */
.stButton > button {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    width: 100% !important;
    padding: 8px 12px !important;
    text-align: left !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.12s ease !important;
}
.stButton > button:hover {
    background: #f1f5f9 !important;
    border-color: #94a3b8 !important;
    color: #0f172a !important;
}

/* Primary / Action button */
[data-testid="stDownloadButton"] > button {
    background: #0f172a !important;
    color: #f8fafc !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 10px 18px !important;
    width: 100% !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.1) !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #1e293b !important;
}

/* Custom Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0px;
    margin-bottom: 16px;
}
.stTabs [data-baseweb="tab"] {
    height: 38px;
    background-color: transparent;
    border-radius: 6px 6px 0 0;
    color: #64748b;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 14px;
    border: none;
    transition: all 0.12s ease;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #0f172a !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #0f172a;
    background-color: #f1f5f9;
}

/* Verdict boxes */
.vbox {
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 16px;
}
.vbox-green  { background: #f0fdf4; border: 1px solid #bbf7d0; }
.vbox-red    { background: #fef2f2; border: 1px solid #fecaca; }
.vbox-yellow { background: #fffbeb; border: 1px solid #fde68a; }
.vbox-tag  { font-size: 11px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 4px; }
.vbox-head { font-size: 20px; font-weight: 800; margin-bottom: 6px; letter-spacing: -0.3px; }
.vbox-text { font-size: 13px; line-height: 1.5; color: #334155; }

/* Stat tiles */
.tile {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    padding: 12px 14px;
    text-align: center;
}
.tile-lbl { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; }
.tile-val { font-size: 16px; font-weight: 800; margin: 4px 0 2px; }
.tile-sub { font-size: 11px; color: #94a3b8; }

/* File info strip */
.strip {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    padding: 10px 16px;
    font-size: 12.5px;
    color: #334155;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
}
.strip b { color: #0f172a; }

/* Empty state card */
.empty-state {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 60px 32px;
    text-align: center;
}
.empty-icon {
    font-size: 34px;
    color: #94a3b8;
    margin-bottom: 10px;
}
.empty-title {
    font-size: 15px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 6px;
}
.empty-desc {
    font-size: 13px;
    color: #64748b;
    max-width: 320px;
    margin: 0 auto;
    line-height: 1.5;
}

/* Steps list */
.step-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
}
.step-num {
    min-width: 20px;
    height: 20px;
    background: #0f172a;
    color: #ffffff;
    border-radius: 50%;
    font-size: 10.5px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 1px;
}
.step-content {
    font-size: 12px;
    color: #334155;
    line-height: 1.45;
}
</style>
""", unsafe_allow_html=True)

# Top Bar
st.markdown("""
<div class="ws-navbar">
    <div class="ws-nav-brand">
        <div class="ws-logo-mark">WS</div>
        <div class="ws-nav-title">WaveSeal <span class="ws-nav-sub">/ Audio Forensics & Authenticity</span></div>
    </div>
    <div class="ws-nav-tag">Production Ready</div>
</div>
""", unsafe_allow_html=True)

# Generate or load built-in sample files
sample_dict = generate_sample_audio_files()

if "target_path" not in st.session_state:
    st.session_state.target_path = None
    st.session_state.display_name = None

def _load_sample(key, label):
    st.session_state.target_path = sample_dict[key]
    st.session_state.display_name = label

# Layout: Two columns (1.05 to 2.2 ratio)
col_left, col_right = st.columns([1.05, 2.2], gap="large")

# ═══════════════════════════ LEFT PANEL ═══════════════════════════════════════
with col_left:

    # 1. Upload Box
    with st.container(border=True):
        st.markdown('<p class="card-heading">Upload Audio File</p>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "WAV, MP3, M4A, FLAC, OGG",
            type=["wav", "mp3", "m4a", "flac", "ogg"],
            label_visibility="collapsed",
        )
        if uploaded is not None:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1])
            tmp.write(uploaded.read())
            tmp.close()
            st.session_state.target_path = tmp.name
            st.session_state.display_name = uploaded.name

    # 2. Test Samples Box
    with st.container(border=True):
        st.markdown('<p class="card-heading">Test Samples</p>', unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px;color:#64748b;margin:0 0 10px;'>Select a pre-built benchmark file to inspect:</p>", unsafe_allow_html=True)

        if st.button("Sample A: Authentic Recording (Clean speech)", key="btn_clean"):
            _load_sample("authentic", "authentic_sample.wav")
            st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        if st.button("Sample B: Tampered Audio (Spliced cuts)", key="btn_spliced"):
            _load_sample("tampered", "tampered_sample.wav")
            st.rerun()

    # 3. How It Works Box
    with st.container(border=True):
        st.markdown('<p class="card-heading">Forensic Pipeline</p>', unsafe_allow_html=True)
        pipeline_steps = [
            ("1", "Signal Discontinuity: Scans waveform for splice points and cut boundaries."),
            ("2", "Acoustic Tone: Checks background noise consistency across time slices."),
            ("3", "Zero-Fill Detection: Identifies unnatural digital silence gaps inserted by editors."),
            ("4", "Container Metadata: Inspects headers for DAW signatures (Audacity, etc.)."),
            ("5", "Chain of Custody: Generates cryptographic hashes (MD5, SHA-256) and court PDF."),
        ]
        for num, text in pipeline_steps:
            st.markdown(f"""
            <div class="step-item">
                <div class="step-num">{num}</div>
                <div class="step-content">{text}</div>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════ RIGHT PANEL ══════════════════════════════════════
with col_right:

    if not st.session_state.target_path or not os.path.exists(st.session_state.target_path):
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">&#9836;</div>
            <div class="empty-title">No Audio Selected</div>
            <div class="empty-desc">
                Upload a recording on the left, or click one of the pre-built test samples to launch forensic verification.
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        path = st.session_state.target_path
        fname = st.session_state.display_name

        with st.spinner("Executing forensic audit..."):
            hashes = compute_file_hashes(path)
            metadata = extract_metadata(path)
            metadata["filename"] = fname
            y, sr = load_audio_signal(path)
            health = compute_audio_health_metrics(y, sr)
            audit = run_full_forensic_audit(y, sr, metadata, sensitivity=3.5)

        score = audit["authenticity_score"]
        verdict = audit["verdict"]
        discs = audit.get("discontinuities", [])
        dead_s = [g for g in audit.get("silence_gaps", []) if g.get("is_dead_silence")]
        noise = audit.get("noise_analysis", {})
        all_sw = list(set(metadata.get("software_tags", []) + metadata.get("binary_signatures", [])))
        dur = metadata["duration_sec"]
        times_arr = np.linspace(0, dur, len(y))

        # File Strip with Reset Button
        col_strip, col_reset = st.columns([5, 1])
        with col_strip:
            st.markdown(f"""
            <div class="strip">
                <div><b>File:</b> {fname}</div>
                <div><b>Duration:</b> {dur:.2f}s</div>
                <div><b>Format:</b> {metadata['format']}</div>
                <div><b>Sample Rate:</b> {metadata['sample_rate']:,} Hz</div>
                <div><b>Channels:</b> {metadata['channels']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_reset:
            if st.button("Reset", key="btn_reset"):
                st.session_state.target_path = None
                st.session_state.display_name = None
                st.rerun()

        # Audio Player
        st.audio(path)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # ── TABS NAVIGATION ──
        tab_summary, tab_waveform, tab_spectrogram, tab_metadata, tab_report = st.tabs([
            "Overview",
            "Waveform & Cuts",
            "Spectral Analysis",
            "Metadata & Hashes",
            "Download Report",
        ])

        # ── TAB 1: OVERVIEW ──
        with tab_summary:
            if verdict == "AUTHENTIC":
                vc, col = "vbox-green", "#166534"
                head = f"Authentic Recording ({score:.1f}%)"
                body = "No signs of editing detected. Background noise is consistent, energy transitions are natural, and no splice cuts were isolated."
            elif "SUSPICIOUS" in verdict:
                vc, col = "vbox-yellow", "#92400e"
                head = f"Inconclusive / Suspicious ({score:.1f}%)"
                body = "Minor acoustic irregularities found, but without definitive cut points. The recording may have undergone light processing."
            else:
                vc, col = "vbox-red", "#991b1b"
                cut_txt = f"{len(discs)} splice cut point{'s' if len(discs) != 1 else ''}" if discs else "splice cut points"
                head = f"Signs of Tampering ({score:.1f}%)"
                body = f"Detected {cut_txt} and background noise shifts. This recording shows strong indicators of being spliced or assembled."

            st.markdown(f"""
            <div class="vbox {vc}">
                <div class="vbox-tag" style="color:{col};">Forensic Verdict</div>
                <div class="vbox-head" style="color:{col};">{head}</div>
                <div class="vbox-text">{body}</div>
            </div>""", unsafe_allow_html=True)

            # 4 Key Stat Tiles
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if discs:
                    v = f"{len(discs)} Cut(s)"
                    col2 = "#991b1b"
                    s = ", ".join(f"{d['timestamp_sec']:.1f}s" for d in discs[:2])
                else:
                    v = "None"
                    col2 = "#166534"
                    s = "Clean transitions"
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-lbl">Splice Cuts</div>
                    <div class="tile-val" style="color:{col2};">{v}</div>
                    <div class="tile-sub">{s}</div>
                </div>""", unsafe_allow_html=True)

            with c2:
                if noise.get("inconsistency_flagged"):
                    v2 = "Inconsistent"
                    c2c = "#991b1b"
                    s2 = f"{noise.get('max_shift_ratio', 1.0):.1f}x energy shift"
                else:
                    v2 = "Consistent"
                    c2c = "#166534"
                    s2 = "Uniform room tone"
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-lbl">Background Noise</div>
                    <div class="tile-val" style="color:{c2c};">{v2}</div>
                    <div class="tile-sub">{s2}</div>
                </div>""", unsafe_allow_html=True)

            with c3:
                if dead_s:
                    v3 = f"{len(dead_s)} Gap(s)"
                    c3c = "#991b1b"
                    s3 = "Digital zero-fill"
                else:
                    v3 = "Natural"
                    c3c = "#166534"
                    s3 = "Acoustic background"
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-lbl">Silence Gaps</div>
                    <div class="tile-val" style="color:{c3c};">{v3}</div>
                    <div class="tile-sub">{s3}</div>
                </div>""", unsafe_allow_html=True)

            with c4:
                if all_sw:
                    v4 = "Detected"
                    c4c = "#991b1b"
                    s4 = all_sw[0][:20]
                else:
                    v4 = "Clean"
                    c4c = "#166534"
                    s4 = "No editor signatures"
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-lbl">Editor Signatures</div>
                    <div class="tile-val" style="color:{c4c};">{v4}</div>
                    <div class="tile-sub">{s4}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

            # Forensic Highlights
            with st.container(border=True):
                st.markdown('<p class="card-heading">Analysis Findings</p>', unsafe_allow_html=True)
                findings = []
                if verdict == "AUTHENTIC":
                    findings.append("Continuous waveform continuity with no abrupt amplitude drops across frame boundaries.")
                    findings.append("Ambient acoustic floor remains stable with consistent spectral density throughout.")
                    findings.append("No artificial digital zero gaps or DAW editing tags detected.")
                else:
                    if discs:
                        findings.append(f"Waveform continuity interrupted at {len(discs)} specific cut location(s).")
                    if noise.get("inconsistency_flagged"):
                        findings.append("Acoustic ambient floor shifts significantly between segments, indicating multi-take assembly.")
                    if dead_s:
                        findings.append(f"Identified {len(dead_s)} digital zero-fill silence gap(s) not characteristic of genuine microphone capture.")
                    if all_sw:
                        findings.append(f"Editor metadata markers found: {', '.join(all_sw)}.")

                for f in findings:
                    st.markdown(f"- {f}")

        # ── TAB 2: WAVEFORM & CUTS ──
        with tab_waveform:
            st.markdown('<p class="card-heading">Signal Waveform & Splice Markers</p>', unsafe_allow_html=True)

            fig, ax = plt.subplots(figsize=(9, 2.5))
            fig.patch.set_facecolor("#ffffff")
            ax.set_facecolor("#fafaf9")
            ax.plot(times_arr, y, color="#2563eb", linewidth=0.7, alpha=0.9)
            ax.set_xlim(0, dur)
            ax.set_ylim(-1.08, 1.08)
            ax.set_xlabel("Time (seconds)", fontsize=9, color="#64748b")
            ax.set_ylabel("Amplitude", fontsize=9, color="#64748b")
            ax.tick_params(colors="#94a3b8", labelsize=8)
            for sp in ax.spines.values():
                sp.set_color("#e2e8f0")
            ax.grid(axis="x", linestyle=":", color="#e2e8f0", alpha=0.9)

            label_ys = [0.68, 0.4, 0.12, -0.18, -0.46]
            for i, d in enumerate(discs):
                t = d["timestamp_sec"]
                ax.axvline(x=t, color="#dc2626", linestyle="--", linewidth=1.4, zorder=5)
                ax.annotate(
                    f"Cut {i+1} ({t:.2f}s)",
                    xy=(t, label_ys[i % len(label_ys)]),
                    fontsize=7.5,
                    fontweight="bold",
                    color="#991b1b",
                    bbox=dict(boxstyle="square,pad=0.2", fc="#fee2e2", ec="#fca5a5", lw=0.8),
                    zorder=6,
                )
            plt.tight_layout(pad=0.3)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            if discs:
                st.markdown('<p class="card-heading">Detected Cut Registry</p>', unsafe_allow_html=True)
                st.dataframe(
                    pd.DataFrame([{
                        "Cut #": f"#{i}",
                        "Timestamp": f"{d['timestamp_sec']:.3f} s",
                        "Severity": d["severity"].title(),
                        "Confidence": f"{d['confidence_pct']:.0f}%",
                        "Details": "Step discontinuity in energy derivative across window boundary",
                    } for i, d in enumerate(discs, 1)]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("No waveform discontinuities or abrupt cut boundaries detected.")

            if dead_s:
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.markdown('<p class="card-heading">Digital Silence Intervals</p>', unsafe_allow_html=True)
                st.dataframe(
                    pd.DataFrame([{
                        "Interval #": f"#{i}",
                        "Start Time": f"{g['start_sec']:.3f} s",
                        "End Time": f"{g['end_sec']:.3f} s",
                        "Duration": f"{g['duration_sec']:.3f} s",
                        "Pattern": "Digital absolute zero sequence",
                    } for i, g in enumerate(dead_s, 1)]),
                    use_container_width=True,
                    hide_index=True,
                )

        # ── TAB 3: SPECTRAL ANALYSIS ──
        with tab_spectrogram:
            st.markdown('<p class="card-heading">Short-Time Fourier Transform (STFT) Spectrogram</p>', unsafe_allow_html=True)

            fig2, ax2 = plt.subplots(figsize=(9, 2.6))
            fig2.patch.set_facecolor("#ffffff")
            ax2.set_facecolor("#fafaf9")
            stft_db, spec_times, freqs = compute_spectrogram(y, sr)
            mesh = ax2.pcolormesh(spec_times, freqs, stft_db, cmap="magma", shading="auto", vmin=-80, vmax=0)
            ax2.set_xlim(0, dur)
            ax2.set_xlabel("Time (seconds)", fontsize=9, color="#64748b")
            ax2.set_ylabel("Frequency (Hz)", fontsize=9, color="#64748b")
            ax2.tick_params(colors="#94a3b8", labelsize=8)
            for sp in ax2.spines.values():
                sp.set_color("#e2e8f0")
            fig2.colorbar(mesh, ax=ax2, pad=0.01, aspect=18).ax.tick_params(labelsize=7)

            for d in discs:
                ax2.axvline(x=d["timestamp_sec"], color="#dc2626", linestyle="--", linewidth=1.2)

            plt.tight_layout(pad=0.3)
            st.pyplot(fig2, use_container_width=True)
            plt.close(fig2)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown('<p class="card-heading">Audio Signal Health Metrics</p>', unsafe_allow_html=True)

            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Peak Amplitude", f"{health['peak_amp']:.3f}")
            sm2.metric("RMS Power", f"{health['rms']:.3f}")
            sm3.metric("Clipping Rate", f"{health['clipping_pct']:.2f}%")
            sm4.metric("Crest Factor", f"{health['crest_factor_db']:.1f} dB")

        # ── TAB 4: METADATA & HASHES ──
        with tab_metadata:
            st.markdown('<p class="card-heading">Cryptographic Chain-of-Custody Hashes</p>', unsafe_allow_html=True)
            st.code(
                f"MD5:    {hashes['md5']}\nSHA1:   {hashes['sha1']}\nSHA256: {hashes['sha256']}",
                language="text",
            )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown('<p class="card-heading">Container & File Encoding Specifications</p>', unsafe_allow_html=True)

            meta_data_rows = [
                {"Property": "File Name", "Value": str(fname)},
                {"Property": "Container Format", "Value": str(metadata.get("format", "Unknown"))},
                {"Property": "Duration", "Value": f"{dur:.2f} seconds"},
                {"Property": "Sampling Rate", "Value": f"{metadata.get('sample_rate', 0):,} Hz"},
                {"Property": "Audio Channels", "Value": str(metadata.get("channels", "Mono"))},
                {"Property": "Bit Depth", "Value": f"{metadata.get('bits_per_sample', 16)}-bit"},
                {"Property": "File Size", "Value": f"{metadata.get('file_size_bytes', 0):,} bytes"},
            ]
            st.dataframe(pd.DataFrame(meta_data_rows), use_container_width=True, hide_index=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown('<p class="card-heading">Software Signatures & Metadata Tags</p>', unsafe_allow_html=True)
            if all_sw:
                st.warning(f"Editing software signature detected: {', '.join(all_sw)}")
            else:
                st.info("No digital audio workstation (DAW) or editor signatures detected in headers.")

        # ── TAB 5: DOWNLOAD REPORT ──
        with tab_report:
            st.markdown('<p class="card-heading">Official Forensic PDF Report</p>', unsafe_allow_html=True)
            st.write(
                "Export a court-admissible forensic document detailing the cryptographic file hashes, "
                "waveform analysis, detected cut timestamps, background noise evaluation, and final integrity verdict."
            )

            chart_f = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            chart_f.close()
            fig_r, ax_r = plt.subplots(figsize=(10, 2.5))
            ax_r.plot(times_arr, y, color="#2563eb", linewidth=0.7)
            for d in discs:
                ax_r.axvline(x=d["timestamp_sec"], color="#dc2626", linestyle="--", linewidth=1.2)
            ax_r.set_xlabel("Time (seconds)", fontsize=9)
            ax_r.set_ylabel("Amplitude", fontsize=9)
            ax_r.grid(axis="x", linestyle=":", color="#e2e8f0")
            ax_r.set_xlim(0, dur)
            plt.tight_layout()
            plt.savefig(chart_f.name, dpi=180, bbox_inches="tight", facecolor="#ffffff")
            plt.close(fig_r)

            pdf_f = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            pdf_f.close()
            generate_pdf_report(metadata, hashes, audit, chart_image_path=chart_f.name, output_path=pdf_f.name)
            with open(pdf_f.name, "rb") as pf:
                pdf_bytes = pf.read()

            st.download_button(
                label="Download Official Forensic PDF Report",
                data=pdf_bytes,
                file_name=f"WaveSeal_Forensic_Report_{fname.replace(' ', '_')}.pdf",
                mime="application/pdf",
                key="btn_download_report",
            )
