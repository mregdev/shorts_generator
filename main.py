import asyncio
import os
import subprocess
from pathlib import Path

import edge_tts
import requests
from dotenv import load_dotenv

from modules.wikimedia_downloader import download_wikimedia_images
from modules.subtitle_generator import generate_srt_from_script
from modules.wiki_summary import build_script_from_wikipedia

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

BASE_DIR = Path(__file__).parent
DOWNLOADS = BASE_DIR / "downloads"
IMAGES_DIR = DOWNLOADS / "images"
AUDIO_DIR = DOWNLOADS / "audio"
OUTPUT_DIR = BASE_DIR / "output"

FFMPEG_PATH = r"C:\Users\Emre\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"

VOICE = "tr-TR-AhmetNeural"

IMAGE_COUNT = 6
VIDEO_DURATION = 30


def clear_folder(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)

    for item in folder.iterdir():
        if item.is_file():
            item.unlink()


def read_topic():
    topics_file = BASE_DIR / "topics.txt"

    if not topics_file.exists():
        raise FileNotFoundError("topics.txt bulunamadı.")

    topic = topics_file.read_text(encoding="utf-8").strip()

    if not topic:
        raise ValueError("topics.txt boş.")

    return topic


async def create_voice(text: str):
    print("[1/6] Ses oluşturuluyor...")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    output_path = AUDIO_DIR / "voice.mp3"

    communicate = edge_tts.Communicate(text.strip(), VOICE)
    await communicate.save(str(output_path))

    print(f"      Ses hazır: {output_path}")
    return output_path


def download_pexels_images(query: str, count: int):
    if not PEXELS_API_KEY:
        print("[Pexels] API key yok, Pexels atlandı.")
        return []

    print("[Pexels] Yedek fotoğraf araması başlatıldı...")

    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/v1/search"

    params = {
        "query": query,
        "per_page": count,
        "orientation": "portrait"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"[Pexels] Arama hatası: {e}")
        return []

    photos = response.json().get("photos", [])

    if not photos:
        print("[Pexels] Fotoğraf bulunamadı.")
        return []

    image_paths = []

    for i, photo in enumerate(photos, start=1):
        image_url = photo["src"]["large2x"]
        image_path = IMAGES_DIR / f"pexels_{i}.jpg"

        try:
            img = requests.get(image_url, timeout=30)
            img.raise_for_status()

            with open(image_path, "wb") as f:
                f.write(img.content)

            image_paths.append(image_path)
            print(f"[Pexels] İndirildi: {image_path.name}")

        except Exception as e:
            print(f"[Pexels] İndirme hatası: {e}")

    return image_paths


def get_images_for_topic(topic: str, count: int):
    print("[3/6] Görseller hazırlanıyor...")

    clear_folder(IMAGES_DIR)

    wikimedia_images = download_wikimedia_images(
        topic=topic,
        output_dir=str(IMAGES_DIR),
        max_images=count
    )

    if len(wikimedia_images) >= count:
        print(f"[Görsel] Wikimedia yeterli: {len(wikimedia_images)} görsel.")
        return wikimedia_images[:count]

    print("[Görsel] Wikimedia yeterli değil, Pexels ile tamamlanıyor...")

    missing = count - len(wikimedia_images)
    pexels_images = download_pexels_images(topic, count=missing)

    all_images = wikimedia_images + pexels_images

    if not all_images:
        raise Exception("Hiç görsel indirilemedi.")

    print(f"[Görsel] Toplam görsel: {len(all_images)}")
    return all_images[:count]


def create_video_from_images(image_paths, audio_path, subtitle_path):
    print("[4/6] Video oluşturuluyor...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    list_file = OUTPUT_DIR / "images.txt"
    temp_video = OUTPUT_DIR / "temp_video.mp4"
    final_video = OUTPUT_DIR / "final.mp4"
    final_subtitled = OUTPUT_DIR / "final_subtitled.mp4"

    duration_per_image = VIDEO_DURATION / len(image_paths)

    with open(list_file, "w", encoding="utf-8") as f:
        for image in image_paths:
            image_path = Path(image).resolve().as_posix()
            f.write(f"file '{image_path}'\n")
            f.write(f"duration {duration_per_image}\n")

        last_image_path = Path(image_paths[-1]).resolve().as_posix()
        f.write(f"file '{last_image_path}'\n")

    cmd_video = [
        FFMPEG_PATH, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        str(temp_video)
    ]

    subprocess.run(cmd_video, check=True)

    print("[5/6] Ses video ile birleştiriliyor...")

    cmd_audio = [
        FFMPEG_PATH, "-y",
        "-i", str(temp_video),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(final_video)
    ]

    subprocess.run(cmd_audio, check=True)

    print("[6/6] Altyazı videoya gömülüyor...")

    subtitle_path_fixed = str(Path(subtitle_path).resolve()).replace("\\", "/").replace(":", "\\:")

    subtitle_filter = (
        f"subtitles='{subtitle_path_fixed}':"
        "force_style='FontName=Segoe UI Semibold,"
        "FontSize=9,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=0.7,"
        "Shadow=0,"
        "Alignment=2,"
        "MarginV=35,"
        "MarginL=35,"
        "MarginR=35'"
    )

    cmd_subtitle = [
        FFMPEG_PATH, "-y",
        "-i", str(final_video),
        "-vf", subtitle_filter,
        "-c:a", "copy",
        str(final_subtitled)
    ]

    subprocess.run(cmd_subtitle, check=True)

    print(f"Video hazır: {final_subtitled}")


async def main():
    print("Shorts Factory başlatıldı.")

    clear_folder(AUDIO_DIR)

    topic = read_topic()

    print(f"Konu: {topic}")
    print(f"Görsel sayısı: {IMAGE_COUNT}")
    print(f"Hedef video süresi: {VIDEO_DURATION} saniye")

    script = build_script_from_wikipedia(topic, VIDEO_DURATION)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = OUTPUT_DIR / "script.txt"
    script_path.write_text(script.strip(), encoding="utf-8")

    print("Senaryo hazır.")

    audio_path = await create_voice(script)

    subtitle_file = generate_srt_from_script(
        script,
        str(audio_path),
        str(OUTPUT_DIR)
    )

    image_paths = get_images_for_topic(topic, count=IMAGE_COUNT)

    create_video_from_images(
        image_paths,
        audio_path,
        subtitle_file
    )

    print(f"Altyazı oluşturuldu: {subtitle_file}")
    print("Tamamlandı.")


if __name__ == "__main__":
    asyncio.run(main())