import hashlib
import os
import datetime
import wave
import soundfile as sf

try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.flac import FLAC
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def compute_file_hashes(filepath: str) -> dict:
    """
    Compute cryptographic hashes for Chain-of-Custody forensic verification.
    Produces MD5, SHA-1, SHA-256, and SHA-512.
    """
    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()
    sha256_hash = hashlib.sha256()
    sha512_hash = hashlib.sha512()

    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5_hash.update(chunk)
            sha1_hash.update(chunk)
            sha256_hash.update(chunk)
            sha512_hash.update(chunk)

    return {
        "md5": md5_hash.hexdigest().upper(),
        "sha1": sha1_hash.hexdigest().upper(),
        "sha256": sha256_hash.hexdigest().upper(),
        "sha512": sha512_hash.hexdigest().upper()
    }


def scan_raw_binary_signatures(filepath: str) -> list:
    """
    Inspect raw binary file headers and chunks for embedded software fingerprints.
    Forensic DAW tools often leave signatures in RIFF INFO lists, ID3 comments, or encoder strings.
    """
    signatures_found = []
    known_signatures = {
        b"Lavf": "FFmpeg / Libavformat Encoder",
        b"Audacity": "Audacity Digital Audio Editor",
        b"Adobe Audition": "Adobe Audition Workstation",
        b"FL Studio": "Image-Line FL Studio",
        b"Pro Tools": "Avid Pro Tools",
        b"Logic Pro": "Apple Logic Pro",
        b"Sound Forge": "Magix Sound Forge",
        b"GoldWave": "GoldWave Audio Editor",
        b"Reaper": "Cockos REAPER",
        b"LAME": "LAME MP3 Encoder",
        b"sox": "Sound eXchange (SoX) CLI",
        b"Cool Edit": "Syntrillium Cool Edit"
    }

    try:
        # Read first 128KB and last 32KB where headers, metadata chunks, and trailers reside
        file_size = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            header_bytes = f.read(min(file_size, 131072))
            trailer_bytes = b""
            if file_size > 131072:
                f.seek(max(0, file_size - 32768))
                trailer_bytes = f.read()

        combined_bytes = header_bytes + trailer_bytes
        for sig_bytes, sig_name in known_signatures.items():
            if sig_bytes.lower() in combined_bytes.lower():
                if sig_name not in signatures_found:
                    signatures_found.append(sig_name)
    except Exception:
        pass

    return signatures_found


def extract_metadata(filepath: str) -> dict:
    """
    Extract container structure, acoustic formatting parameters, and metadata signatures.
    """
    stats = os.stat(filepath)
    file_size_bytes = stats.st_size
    created_time = datetime.datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
    modified_time = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

    ext = os.path.splitext(filepath)[1].lower()

    metadata = {
        "filename": os.path.basename(filepath),
        "file_size": f"{file_size_bytes / (1024 * 1024):.2f} MB ({file_size_bytes:,} bytes)",
        "file_size_bytes": file_size_bytes,
        "file_extension": ext,
        "created_at": created_time,
        "modified_at": modified_time,
        "duration_sec": 0.0,
        "sample_rate": 0,
        "channels": 0,
        "subtype": "Standard Audio",
        "format": ext.replace('.', '').upper() if ext else "UNKNOWN",
        "bitrate_kbps": 0.0,
        "software_tags": [],
        "binary_signatures": [],
        "suspicious_flags": [],
        "container_status": "Valid Container"
    }

    # Primary inspection using soundfile
    try:
        info = sf.info(filepath)
        metadata["sample_rate"] = int(info.samplerate)
        metadata["channels"] = int(info.channels)
        metadata["duration_sec"] = round(float(info.duration), 3)
        metadata["format"] = str(info.format)
        metadata["subtype"] = str(info.subtype)
        if info.duration > 0:
            metadata["bitrate_kbps"] = round((file_size_bytes * 8) / (info.duration * 1000), 2)
    except Exception:
        # Fallback to wave module for WAV files
        if ext == '.wav':
            try:
                with wave.open(filepath, 'rb') as wf:
                    metadata["channels"] = wf.getnchannels()
                    metadata["sample_rate"] = wf.getframerate()
                    frames = wf.getnframes()
                    duration = frames / float(wf.getframerate()) if wf.getframerate() > 0 else 0.0
                    metadata["duration_sec"] = round(duration, 3)
                    metadata["subtype"] = f"PCM {wf.getsampwidth()*8}-bit"
                    if duration > 0:
                        metadata["bitrate_kbps"] = round((file_size_bytes * 8) / (duration * 1000), 2)
            except Exception:
                metadata["container_status"] = "Corrupted or Non-Standard Container"

    # Mutagen tag inspection
    if MUTAGEN_AVAILABLE:
        try:
            audio_tags = mutagen.File(filepath)
            if audio_tags is not None and audio_tags.tags:
                tag_str = str(audio_tags.tags).lower()
                editing_keywords = {
                    "audacity": "Audacity",
                    "adobe audition": "Adobe Audition",
                    "logic pro": "Logic Pro",
                    "cubase": "Steinberg Cubase",
                    "pro tools": "Avid Pro Tools",
                    "fl studio": "FL Studio",
                    "goldwave": "GoldWave",
                    "reaper": "REAPER",
                    "ffmpeg": "FFmpeg",
                    "sound forge": "Sound Forge",
                    "wavepad": "WavePad",
                    "garageband": "GarageBand",
                    "sox": "SoX Audio",
                    "cool edit": "Cool Edit Pro"
                }

                found_software = [label for kw, label in editing_keywords.items() if kw in tag_str]
                if found_software:
                    metadata["software_tags"] = found_software
                    metadata["suspicious_flags"].append(
                        f"Editing software signature identified in tags: {', '.join(found_software)}"
                    )
        except Exception:
            pass

    # Raw binary chunk inspection
    bin_sigs = scan_raw_binary_signatures(filepath)
    if bin_sigs:
        metadata["binary_signatures"] = bin_sigs
        for sig in bin_sigs:
            if sig not in metadata["software_tags"]:
                metadata["suspicious_flags"].append(f"Software footprint detected in file header/chunks: {sig}")

    # Physical acoustic parameters integrity check
    if metadata["sample_rate"] > 0 and metadata["sample_rate"] not in [8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 88200, 96000, 192000]:
        metadata["suspicious_flags"].append(f"Non-standard forensic sampling rate: {metadata['sample_rate']} Hz")

    if metadata["channels"] > 2:
        metadata["suspicious_flags"].append(f"Unusual multi-channel configuration: {metadata['channels']} channels")

    return metadata
