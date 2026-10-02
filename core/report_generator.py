import os
import datetime
from fpdf import FPDF


class ForensicPDFReport(FPDF):
    def header(self):
        # Professional institutional top banner
        self.set_fill_color(30, 41, 59)  # Dark slate navy
        self.rect(0, 0, 210, 20, 'F')
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(255, 255, 255)
        self.cell(0, 5, "WAVESEAL DIGITAL FORENSICS - EXAMINATION REPORT", border=False, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(203, 213, 225)
        self.cell(0, 4, "WaveSeal Audio Integrity & Forensic Verification Document", border=False, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}} | Chain of Custody Confidential Forensic Document | WaveSeal Forensics", align="C")


def generate_pdf_report(metadata: dict, hashes: dict, audit_results: dict, chart_image_path: str = None, output_path: str = "forensic_report.pdf") -> str:
    """
    Generate professional court-admissible style PDF forensic examination report.
    """
    pdf = ForensicPDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # 1. Executive Summary & Verdict
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "1. EXECUTIVE FORENSIC INTEGRITY VERDICT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(203, 213, 225)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    verdict = audit_results.get("verdict", "UNKNOWN")
    score = audit_results.get("authenticity_score", 0.0)
    verdict_level = audit_results.get("verdict_level", "")

    # Verdict Box Styling
    if verdict == "AUTHENTIC":
        pdf.set_fill_color(220, 252, 231)  # Soft green
        pdf.set_text_color(21, 128, 61)
        pdf.set_draw_color(134, 239, 172)
    elif "SUSPICIOUS" in verdict:
        pdf.set_fill_color(254, 243, 199)  # Soft amber
        pdf.set_text_color(180, 83, 9)
        pdf.set_draw_color(253, 224, 71)
    else:
        pdf.set_fill_color(254, 226, 226)  # Soft red
        pdf.set_text_color(185, 28, 28)
        pdf.set_draw_color(252, 165, 165)

    y_start = pdf.get_y()
    pdf.rect(10, y_start, 190, 22, 'DF')
    pdf.set_xy(14, y_start + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 5, f"OFFICIAL FINDING: {verdict} - {verdict_level}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 4, f"Forensic Authenticity Index: {score:.1f} / 100.0%", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.cell(0, 4, audit_results.get("verdict_desc", ""), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y_start + 25)

    # 2. Evidence Specifications & Cryptographic Chain of Custody
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "2. EVIDENCE RECORD & CHAIN-OF-CUSTODY HASHES", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(203, 213, 225)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    meta_table = [
        ("Evidence File Name", metadata.get("filename", "N/A")),
        ("Container & Codec", f"{metadata.get('format', 'N/A')} ({metadata.get('subtype', 'N/A')})"),
        ("Audio Duration", f"{metadata.get('duration_sec', 0.0)} seconds"),
        ("Sampling Rate & Channels", f"{metadata.get('sample_rate', 0)} Hz | {metadata.get('channels', 1)} Channel(s)"),
        ("Bitrate & Size", f"{metadata.get('bitrate_kbps', 0.0)} kbps | {metadata.get('file_size', 'N/A')}"),
        ("MD5 Hash", hashes.get("md5", "N/A")),
        ("SHA-1 Hash", hashes.get("sha1", "N/A")),
        ("SHA-256 Hash", hashes.get("sha256", "N/A")),
        ("SHA-512 Hash", hashes.get("sha512", "N/A")[:64] + "..."),
        ("Examination Date/Time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    ]

    for key, val in meta_table:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(48, 4.2, key + ":", border=0)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(142, 4.2, str(val), border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    # 3. Five-Pillar Forensic Breakdown
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "3. MULTI-PILLAR FORENSIC INTEGRITY AUDIT", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    # Table Header
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(50, 5, "Forensic Pillar", border=1, fill=True)
    pdf.cell(18, 5, "Weight", border=1, fill=True, align="C")
    pdf.cell(20, 5, "Score", border=1, fill=True, align="C")
    pdf.cell(22, 5, "Status", border=1, fill=True, align="C")
    pdf.cell(80, 5, "Observations", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 7.5)
    pillars = audit_results.get("pillars", {})
    for p_key, p_data in pillars.items():
        pdf.cell(50, 4.5, p_data.get("name", p_key), border=1)
        pdf.cell(18, 4.5, p_data.get("weight", "-"), border=1, align="C")
        pdf.cell(20, 4.5, f"{p_data.get('score', 0.0)}%", border=1, align="C")
        
        status = p_data.get("status", "Normal")
        pdf.set_font("Helvetica", "B", 7.5)
        if status == "Normal":
            pdf.set_text_color(21, 128, 61)
        elif status == "Review":
            pdf.set_text_color(180, 83, 9)
        else:
            pdf.set_text_color(185, 28, 28)
        pdf.cell(22, 4.5, status, border=1, align="C")
        
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(80, 4.5, p_data.get("detail", "")[:55], border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    # 4. Detected Splices & Discontinuities Table
    discs = audit_results.get("discontinuities", [])
    if discs:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "4. TIMESTAMPED SPLICE / CUT DISCONTINUITY REGISTER", new_x="LMARGIN", new_y="NEXT")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

        pdf.set_fill_color(241, 245, 249)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(25, 5, "Timestamp", border=1, fill=True, align="C")
        pdf.cell(25, 5, "Anomaly Score", border=1, fill=True, align="C")
        pdf.cell(25, 5, "Confidence", border=1, fill=True, align="C")
        pdf.cell(25, 5, "Severity", border=1, fill=True, align="C")
        pdf.cell(90, 5, "Forensic Description", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 7.5)
        for disc in discs:
            pdf.cell(25, 4.5, f"{disc.get('timestamp_sec', 0.0):.2f}s", border=1, align="C")
            pdf.cell(25, 4.5, str(disc.get("anomaly_score", 0.0)), border=1, align="C")
            pdf.cell(25, 4.5, f"{disc.get('confidence_pct', 0.0):.1f}%", border=1, align="C")
            
            sev = disc.get("severity", "Moderate")
            pdf.set_font("Helvetica", "B", 7.5)
            if sev == "Critical":
                pdf.set_text_color(185, 28, 28)
            else:
                pdf.set_text_color(180, 83, 9)
            pdf.cell(25, 4.5, sev, border=1, align="C")

            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(90, 4.5, disc.get("description", "")[:60], border=1, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

    # 5. Visual Charts (on new page or appended cleanly)
    if chart_image_path and os.path.exists(chart_image_path):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "5. MULTI-PANEL FORENSIC SPECTRAL & WAVEFORM EVIDENCE", new_x="LMARGIN", new_y="NEXT")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        pdf.image(chart_image_path, x=10, y=pdf.get_y(), w=190)

    pdf.output(output_path)
    return output_path
