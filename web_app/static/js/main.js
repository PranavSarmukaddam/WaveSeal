// Main JavaScript for Audio Forensics Student Mini Project Interface

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                uploadAndAnalyze(e.target.files[0]);
            }
        });
    }
});

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.getAttribute('onclick').includes(tabId));
    if (activeBtn) activeBtn.classList.add('active');

    const activeContent = document.getElementById(tabId);
    if (activeContent) activeContent.classList.add('active');
}

function analyzeSample(sampleId) {
    showLoading(true);
    fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sample_id: sampleId })
    })
    .then(res => res.json())
    .then(data => {
        showLoading(false);
        if (data.status === 'success') {
            displayResults(data);
        } else {
            alert('Analysis Error: ' + data.message);
        }
    })
    .catch(err => {
        showLoading(false);
        alert('Server connection error: ' + err);
    });
}

function uploadAndAnalyze(file) {
    showLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/analyze', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        showLoading(false);
        if (data.status === 'success') {
            displayResults(data);
        } else {
            alert('Analysis Error: ' + data.message);
        }
    })
    .catch(err => {
        showLoading(false);
        alert('Upload server error: ' + err);
    });
}

function showLoading(isLoading) {
    document.getElementById('loading-area').style.display = isLoading ? 'block' : 'none';
    if (isLoading) {
        document.getElementById('results-area').style.display = 'none';
    }
}

function displayResults(data) {
    document.getElementById('results-area').style.display = 'block';

    // 1. Verdict & Score
    const audit = data.audit;
    const scoreVal = document.getElementById('score-val');
    const verdictTitle = document.getElementById('verdict-title');
    const verdictDesc = document.getElementById('verdict-desc');
    const verdictBox = document.getElementById('verdict-box');

    scoreVal.innerText = audit.authenticity_score;
    verdictTitle.innerText = audit.verdict;
    verdictDesc.innerText = audit.verdict_desc;

    verdictBox.className = 'verdict-box ';
    if (audit.verdict === 'AUTHENTIC') {
        verdictBox.className += 'verdict-authentic';
    } else if (audit.verdict === 'SUSPICIOUS') {
        verdictBox.className += 'verdict-suspicious';
    } else {
        verdictBox.className += 'verdict-tampered';
    }

    // Audio Player
    const audioPlayer = document.getElementById('audio-player');
    if (audioPlayer && data.audio_url) {
        audioPlayer.src = data.audio_url;
    }

    // 2. Hashes & Metadata
    const hashes = data.hashes;
    const meta = data.metadata;
    document.getElementById('hash-md5').innerText = hashes.md5;
    document.getElementById('hash-sha256').innerText = hashes.sha256;

    document.getElementById('meta-format').innerText = meta.format + ' (' + meta.subtype + ')';
    document.getElementById('meta-sr').innerText = meta.sample_rate + ' Hz';
    document.getElementById('meta-channels').innerText = meta.channels;
    document.getElementById('meta-duration').innerText = meta.duration_sec + ' s';
    document.getElementById('meta-bitrate').innerText = meta.bitrate_kbps + ' kbps';
    document.getElementById('meta-size').innerText = meta.file_size;

    // 3. Visual Spectrogram Image
    const specImg = document.getElementById('spectrogram-img');
    if (specImg && data.plot_url) {
        specImg.src = data.plot_url + '?t=' + new Date().getTime();
    }

    // 4. Discontinuities & Silence
    const disconTbody = document.getElementById('discon-tbody');
    disconTbody.innerHTML = '';
    if (audit.discontinuities && audit.discontinuities.length > 0) {
        audit.discontinuities.forEach(d => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${d.timestamp_sec}s</td>
                <td><span class="badge ${d.severity === 'High' ? 'badge-red' : 'badge-amber'}">${d.severity}</span></td>
                <td>${d.anomaly_score}</td>
                <td>${d.description}</td>
            `;
            disconTbody.appendChild(tr);
        });
    } else {
        disconTbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#166534; font-weight:600;">No abrupt splice boundaries detected.</td></tr>';
    }

    // Silence Gaps
    const silenceContainer = document.getElementById('silence-tbody');
    if (audit.silence_gaps && audit.silence_gaps.length > 0) {
        let html = '<ul>';
        audit.silence_gaps.forEach(g => {
            html += `<li><b>${g.type}</b> from ${g.start_sec}s to ${g.end_sec}s (Duration: ${g.duration_sec}s)</li>`;
        });
        html += '</ul>';
        silenceContainer.innerHTML = html;
    } else {
        silenceContainer.innerHTML = '<p style="color:#166534; font-weight:600;">No unnatural silence gaps detected.</p>';
    }

    // Noise Floor
    document.getElementById('noise-details').innerText = audit.noise_analysis.details || 'Noise floor level analyzed.';

    // Download Report Link
    const reportBtn = document.getElementById('download-report-btn');
    if (reportBtn && data.report_id) {
        reportBtn.href = '/api/download_report/' + data.report_id;
    }
}
