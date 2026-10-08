"""Télécharge les images des 52 cartes.

Source : Wikimedia Commons, catégorie « Playing cards set by Byron Knoll ».
Wikimedia fournit une version PNG des fichiers SVG, il n'y a donc rien à convertir.

Usage : python -m scratch.dataset_generation.assets
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .cards import DECK

API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "advanced-deep-learning-3a/0.1 (student project, playing card grounding)"
WIDTH = 250  # largeur des PNG téléchargés, en pixels


def commons_title(card):
    rank = card.rank if card.rank.isdigit() else card.rank.capitalize()
    variant = "2" if card.is_face else ""  # "King of hearts2.svg" : la version illustrée des figures
    return f"File:{rank} of {card.suit}{variant}.svg"


def http_get(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def thumbnail_urls(titles):
    """Demande à l'API Wikimedia l'URL d'une version PNG de chaque fichier SVG."""
    params = {
        "action": "query",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": WIDTH,
        "format": "json",
    }
    data = json.loads(http_get(f"{API_URL}?{urllib.parse.urlencode(params)}"))
    normalized = {n["to"]: n["from"] for n in data["query"].get("normalized", [])}
    urls = {}
    for page in data["query"]["pages"].values():
        if "imageinfo" in page:
            title = normalized.get(page["title"], page["title"])
            urls[title] = page["imageinfo"][0]["thumburl"]
    return urls


def download_cards(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    missing = [card for card in DECK if not (out_dir / card.filename).exists()]
    if not missing:
        print(f"Les 52 cartes sont déjà dans {out_dir}/")
        return

    titles = [commons_title(card) for card in missing]
    urls = {}
    for start in range(0, len(titles), 50):  # l'API accepte 50 titres par requête
        urls.update(thumbnail_urls(titles[start : start + 50]))

    for card, title in zip(missing, titles):
        if title not in urls:
            raise RuntimeError(f"Fichier introuvable sur Wikimedia Commons : {title}")
        (out_dir / card.filename).write_bytes(http_get(urls[title]))
        print(f"  {card.name}")
        time.sleep(0.1)  # reste poli avec les serveurs de Wikimedia
    print(f"{len(missing)} cartes téléchargées dans {out_dir}/")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data/cards")
    download_cards(parser.parse_args().out_dir)


if __name__ == "__main__":
    main()
