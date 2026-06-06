import io
import requests
from pathlib import Path
from PIL import Image

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent": "ShortsFactory/1.0 (educational-video-generator; contact: emrekumusoglu53@gmail.com)"
}


def wikipedia_search_title(topic: str, lang: str = "tr") -> str | None:
    url = f"https://{lang}.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "list": "search",
        "srsearch": topic,
        "srlimit": 1,
        "format": "json"
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()

        results = r.json().get("query", {}).get("search", [])

        if results:
            return results[0]["title"]

    except Exception as e:
        print(f"[Wikipedia] Başlık arama hatası: {e}")

    return None


def get_english_title_from_tr(title: str) -> str | None:
    url = "https://tr.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "prop": "langlinks",
        "titles": title,
        "lllang": "en",
        "format": "json"
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()

        pages = r.json().get("query", {}).get("pages", {})

        for page in pages.values():
            langlinks = page.get("langlinks", [])

            if langlinks:
                return langlinks[0]["*"]

    except Exception as e:
        print(f"[Wikipedia] İngilizce başlık hatası: {e}")

    return None


def build_search_queries(topic: str) -> list[str]:
    queries = []

    clean_topic = topic.strip()
    queries.append(clean_topic)

    print("[Arama] Wikipedia başlığı aranıyor...")

    tr_title = wikipedia_search_title(clean_topic, lang="tr")

    if tr_title:
        print(f"[Arama] Türkçe başlık bulundu: {tr_title}")
        queries.append(tr_title)

        en_title = get_english_title_from_tr(tr_title)

        if en_title:
            print(f"[Arama] İngilizce başlık bulundu: {en_title}")
            queries.append(en_title)

            queries.extend([
                f"{en_title} painting",
                f"{en_title} illustration",
                f"{en_title} historical",
                f"{en_title} map",
            ])

    en_search_title = wikipedia_search_title(clean_topic, lang="en")

    if en_search_title:
        print(f"[Arama] İngilizce arama sonucu: {en_search_title}")
        queries.append(en_search_title)

    return list(dict.fromkeys([q for q in queries if q]))


def search_commons(query: str, limit: int = 10) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "format": "json"
    }

    response = requests.get(
        COMMONS_API_URL,
        params=params,
        headers=HEADERS,
        timeout=20
    )

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
        "logo",
        "icon",
        "stamp",
        "coin",
        "wax",
        "signature",
        "seal",
        "grave",
        "tomb"
    ]

    lower = title.lower()
    return any(word in lower for word in bad_words)


def download_wikimedia_images(topic: str, output_dir: str, max_images: int = 6) -> list[Path]:
    print("[Wikimedia] Görsel arama başlatıldı...")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    downloaded = []
    seen_urls = set()
    used_titles = set()

    queries = build_search_queries(topic)

    print("[Wikimedia] Denenecek aramalar:")
    for q in queries:
        print(f"  - {q}")

    for query in queries:
        if len(downloaded) >= max_images:
            break

        print(f"[Wikimedia] Aranıyor: {query}")

        try:
            results = search_commons(query, limit=15)
        except Exception as e:
            print(f"[Wikimedia] Arama hatası: {e}")
            continue

        for item in results:
            if len(downloaded) >= max_images:
                break

            title = item.get("title", "")

            if should_skip_title(title):
                continue

            if title in used_titles:
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
            used_titles.add(title)

            try:
                img = requests.get(url, headers=HEADERS, timeout=30)
                img.raise_for_status()

                file_name = f"wikimedia_{len(downloaded) + 1}.jpg"
                file_path = output_path / file_name

                save_as_jpg(img.content, file_path)

                downloaded.append(file_path)

                print(f"[Wikimedia] İndirildi: {file_path.name} | {title}")

            except Exception as e:
                print(f"[Wikimedia] İndirme/dönüştürme hatası: {e}")

    print(f"[Wikimedia] Toplam indirilen: {len(downloaded)}")
    return downloaded