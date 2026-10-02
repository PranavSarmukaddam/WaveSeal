import os
import sys
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

# Add root folder to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.metadata_extractor import compute_file_hashes, extract_metadata
from core.audio_processor import load_audio_signal, plot_forensic_visuals
from core.tamper_detector import run_full_forensic_audit
from core.report_generator import generate_pdf_report
from utils.audio_generator import generate_sample_audio_files

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Ensure synthetic sample audio files exist
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'samples')
sample_paths = generate_sample_audio_files(SAMPLES_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/samples', methods=['GET'])
def get_samples():
    return jsonify({
        "status": "success",
        "samples": [
            {"id": "tampered", "name": "Tampered / Spliced Recording (High Risk)", "path": sample_paths["tampered"]},
            {"id": "authentic", "name": "Authentic Speech Recording (Clean)", "path": sample_paths["authentic"]}
        ]
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_audio():
    try:
        temp_path = None
        if 'file' in request.files and request.files['file'].filename != '':
            audio_file = request.files['file']
            ext = os.path.splitext(audio_file.filename)[1].lower() or '.wav'
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            audio_file.save(tfile.name)
            temp_path = tfile.name
        elif request.json and 'sample_id' in request.json:
            sample_id = request.json['sample_id']
            temp_path = sample_paths.get(sample_id, sample_paths['tampered'])
        else:
            return jsonify({"status": "error", "message": "No audio file or sample ID provided"}), 400

        # Perform analysis
        hashes = compute_file_hashes(temp_path)
        metadata = extract_metadata(temp_path)
        y, sr = load_audio_signal(temp_path)
        audit_results = run_full_forensic_audit(y, sr, metadata)

        # Generate plot image
        plot_filename = f"plot_{os.path.basename(temp_path)}.png"
        plot_path = os.path.join(app.static_folder, 'plots', plot_filename)
        os.makedirs(os.path.dirname(plot_path), exist_ok=True)
        plot_forensic_visuals(y, sr, audit_results, output_path=plot_path)

        # Store analysis state in session temp directory for report download
        report_pdf_name = f"report_{os.path.basename(temp_path)}.pdf"
        report_path = os.path.join(tempfile.gettempdir(), report_pdf_name)
        generate_pdf_report(metadata, hashes, audit_results, chart_image_path=plot_path, output_path=report_path)

        return jsonify({
            "status": "success",
            "hashes": hashes,
            "metadata": metadata,
            "audit": audit_results,
            "plot_url": f"/static/plots/{plot_filename}",
            "report_id": report_pdf_name,
            "audio_url": f"/api/audio/{os.path.basename(temp_path)}" if not request.files else f"/api/audio_temp?path={temp_path}"
        })
    except Exception as e:
        import traceback
        return jsonify({"status": "error", "message": str(e), "trace": traceback.format_exc()}), 500

@app.route('/api/audio/<filename>')
def serve_sample_audio(filename):
    sample_file = os.path.join(SAMPLES_DIR, filename)
    if os.path.exists(sample_file):
        return send_file(sample_file)
    return jsonify({"error": "File not found"}), 404

@app.route('/api/audio_temp')
def serve_temp_audio():
    path = request.args.get('path')
    if path and os.path.exists(path):
        return send_file(path)
    return jsonify({"error": "File not found"}), 404

@app.route('/api/download_report/<report_id>')
def download_report(report_id):
    report_path = os.path.join(tempfile.gettempdir(), report_id)
    if os.path.exists(report_path):
        return send_file(report_path, as_attachment=True, download_name=f"Forensic_Report_{report_id}")
    return jsonify({"error": "Report file expired or not found"}), 404

if __name__ == '__main__':
    print("Starting Audio Forensics Web Server at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
