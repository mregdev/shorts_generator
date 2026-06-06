import re
import requests

HEADERS = {
    "User-Agent": "ShortsFactory/1.0 (educational-video-generator; contact: emrekumusoglu53@gmail.com)"
}


def search_wikipedia_title(topic: str, lang: str = "tr") -> str | None:
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


def get_wikipedia_extract(title: str, lang: str = "tr") -> str | None:
    url = f"https://{lang}.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": True,
        "exintro": True,
        "titles": title,
        "format": "json"
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()

        pages = r.json().get("query", {}).get("pages", {})

        for page in pages.values():
            extract = page.get("extract", "").strip()
            if extract:
                return extract

    except Exception as e:
        print(f"[Wikipedia] Özet alma hatası: {e}")

    return None


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def build_script_from_wikipedia(topic: str, video_duration: int) -> str:
    print("[Script] Wikipedia özeti alınıyor...")

    title = search_wikipedia_title(topic, lang="tr")

    if not title:
        raise Exception("Wikipedia başlığı bulunamadı.")

    print(f"[Script] Bulunan başlık: {title}")

    extract = get_wikipedia_extract(title, lang="tr")

    if not extract:
        raise Exception("Wikipedia özeti bulunamadı.")

    sentences = split_sentences(extract)

    if not sentences:
        raise Exception("Wikipedia özeti cümlelere ayrılamadı.")

    target_words = max(45, int(video_duration * 2.1))

    selected = []
    word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        if word_count + sentence_words > target_words:
            break

        selected.append(sentence)
        word_count += sentence_words

    if not selected:
        selected = sentences[:2]

    script = "\n\n".join(selected)

    if video_duration >= 25:
        script += "\n\nPeki sizce bu olay tarihin akışını gerçekten değiştirdi mi?"

    return script.strip()