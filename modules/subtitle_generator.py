import re
import subprocess
from pathlib import Path

FFMPEG_PATH = r"C:\Users\Emre\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"


def get_audio_duration(audio_file: str) -> float:
    cmd = [
        FFMPEG_PATH,
        "-i", audio_file,
        "-hide_banner"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stderr

    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", output)

    if not match:
        raise Exception("Ses süresi okunamadı.")

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


def format_timestamp(seconds: float):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def split_script_to_subtitle_lines(script: str, max_words_per_line: int = 7):
    sentences = re.split(r"(?<=[.!?])\s+", script.strip())
    lines = []

    for sentence in sentences:
        words = sentence.strip().split()

        if not words:
            continue

        current = []

        for word in words:
            current.append(word)

            if len(current) >= max_words_per_line:
                lines.append(" ".join(current))
                current = []

        if current:
            lines.append(" ".join(current))

    return lines


def generate_srt_from_script(script: str, audio_file: str, output_dir: str):
    print("[Altyazı] Script üzerinden altyazı oluşturuluyor...")

    duration = get_audio_duration(audio_file)
    lines = split_script_to_subtitle_lines(script, max_words_per_line=7)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    srt_file = output_path / "subtitles.srt"

    total_words = sum(len(line.split()) for line in lines)
    current_time = 0.0

    with open(srt_file, "w", encoding="utf-8") as f:
        for index, line in enumerate(lines, start=1):
            word_count = len(line.split())
            line_duration = max(1.3, duration * (word_count / total_words))

            start = current_time
            end = min(duration, current_time + line_duration)

            f.write(f"{index}\n")
            f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
            f.write(f"{line}\n\n")

            current_time = end

    print(f"[Altyazı] Hazır: {srt_file}")
    return srt_file