import io
import os
import requests
from pathlib import Path
from PIL import Image

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent": "ShortsFactory/1.0 (educational-video-generator; contact: emrekumusoglu53@gmail.com)"
}


def search_commons(query: str, limit: int = 20, offset: int = 0) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "gsroffset": offset,
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "format": "json"
    }

    response = requests.get(COMMONS_API_URL, params=params, headers=HEADERS, timeout=20)
    response.raise_for_status()

    pages = response.json().get("query", {}).get("pages", {})
    return list(pages.values())


def save_as_jpg(image_bytes: bytes, file_path: Path):
    image = Image.open(io.BytesIO(image_bytes))

    if image.mode != "RGB":
        image = image.convert("RGB")

    image.save(file_path, "JPEG", quality=92)


def should_skip_title(title: str) -> bool:
    bad_words = [
        "logo", "icon", "stamp", "coin", "signature",
        "seal", "grave", "tomb"
    ]

    lower = title.lower()
    return any(word in lower for word in bad_words)


def download_image_to_jpg(url: str, file_path: Path):
    img = requests.get(url, headers=HEADERS, timeout=30)
    img.raise_for_status()
    save_as_jpg(img.content, file_path)


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(prompt).strip().lower()

        if answer in ["y", "yes", "e", "evet"]:
            return True

        if answer in ["n", "no", "h", "hayır", "hayir"]:
            return False

        print("Lütfen Y veya N yaz.")


def download_wikimedia_images(topic: str, output_dir: str, max_images: int = 6) -> list[Path]:
    print("[Wikimedia] Manuel onaylı görsel seçimi başlatıldı.")
    print(f"[Wikimedia] Arama konusu: {topic}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    downloaded = []
    seen_urls = set()
    used_titles = set()

    offset = 0
    batch_size = 20

    while len(downloaded) < max_images:
        print(f"[Wikimedia] Yeni adaylar aranıyor... offset={offset}")

        try:
            results = search_commons(topic, limit=batch_size, offset=offset)
        except Exception as e:
            raise Exception(f"Wikimedia arama hatası: {e}")

        if not results:
            raise Exception(
                f"Yeterli görsel bulunamadı. Onaylanan: {len(downloaded)}/{max_images}"
            )

        offset += batch_size

        for item in results:
            if len(downloaded) >= max_images:
                break

            title = item.get("title", "")

            if not title or should_skip_title(title) or title in used_titles:
                continue

            imageinfo = item.get("imageinfo", [])
            if not imageinfo:
                continue

            info = imageinfo[0]
            url = info.get("url", "")
            mime = info.get("mime", "")

            if not url or url in seen_urls:
                continue

            if not mime.startswith("image/"):
                continue

            if url.lower().endswith((".svg", ".gif", ".tif", ".tiff", ".webm", ".mp4")):
                continue

            seen_urls.add(url)

            preview_path = output_path / "candidate_preview.jpg"

            try:
                download_image_to_jpg(url, preview_path)
            except Exception as e:
                print(f"[Wikimedia] Aday indirilemedi: {e}")
                continue

            print("\n----------------------------------------")
            print(f"Aday görsel: {title}")
            print(f"Dosya: {preview_path}")
            print("----------------------------------------")

            try:
                os.startfile(preview_path)
            except Exception:
                pass

            accepted = ask_yes_no("Bu resmi onaylıyor musun? (Y/N): ")

            if accepted:
                final_path = output_path / f"wikimedia_{len(downloaded) + 1}.jpg"

                if final_path.exists():
                    final_path.unlink()

                preview_path.rename(final_path)

                downloaded.append(final_path)
                used_titles.add(title)

                print(f"[Wikimedia] Onaylandı: {final_path.name} | {title}")
                print(f"[Wikimedia] Toplam onaylı: {len(downloaded)}/{max_images}")
            else:
                if preview_path.exists():
                    preview_path.unlink()

                print("[Wikimedia] Reddedildi, yeni aday aranacak.")

    print(f"[Wikimedia] Seçim tamamlandı. Toplam: {len(downloaded)}")
    return downloaded