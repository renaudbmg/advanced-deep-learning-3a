"""Génère le dataset synthétique : images de cartes + boîte et nom de chaque carte.

Usage :
    python -m scratch.dataset_generation.generate_dataset --n-train 20000 --n-val 2000 --n-test 2000
    python -m scratch.dataset_generation.generate_dataset --yolo   # exporte aussi le test au format YOLO

Structure produite :
    data/synthetic/{train,val,test}/images/000000.jpg
    data/synthetic/{train,val,test}/annotations.json
    data/synthetic/yolo/                              (avec --yolo)
"""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

from .cards import DECK
from .scene import load_card_images, make_scene

IMAGE_SIZE = 256


def generate_split(out_dir, n_images, card_images, seed):
    rng = np.random.default_rng(seed)  # seed fixe par split : le dataset est reproductible
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    items = []
    for i in range(n_images):
        image, cards, boxes = make_scene(card_images, rng, IMAGE_SIZE)
        image_path = f"images/{i:06d}.jpg"
        image.save(out_dir / image_path, quality=92)
        items.append(
            {
                "image": image_path,
                "cards": [{"name": card.name, "class_id": card.class_id, "box": box} for card, box in zip(cards, boxes)],
            }
        )
        if (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{n_images}")

    annotations = {"image_size": IMAGE_SIZE, "items": items}
    (out_dir / "annotations.json").write_text(json.dumps(annotations))
    n_cards = sum(len(item["cards"]) for item in items)
    print(f"{out_dir}: {n_images} images, {n_cards} cartes")


def export_yolo(split_dir, yolo_dir):
    """Format YOLO : une classe par carte, boîtes (cx, cy, w, h) normalisées."""
    annotations = json.loads((split_dir / "annotations.json").read_text())
    size = annotations["image_size"]
    (yolo_dir / "images").mkdir(parents=True, exist_ok=True)
    (yolo_dir / "labels").mkdir(parents=True, exist_ok=True)
    for item in annotations["items"]:
        image_path = split_dir / item["image"]
        shutil.copy(image_path, yolo_dir / "images" / image_path.name)
        lines = []
        for card in item["cards"]:
            x1, y1, x2, y2 = card["box"]
            cx, cy, w, h = (x1 + x2) / 2 / size, (y1 + y2) / 2 / size, (x2 - x1) / size, (y2 - y1) / size
            lines.append(f"{card['class_id']} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        # Image sans carte : fichier d'étiquettes vide, c'est la convention YOLO
        (yolo_dir / "labels" / f"{image_path.stem}.txt").write_text("".join(f"{line}\n" for line in lines))

    names = "\n".join(f"  {card.class_id}: {card.name}" for card in DECK)
    (yolo_dir / "data.yaml").write_text(
        f"path: {yolo_dir.resolve()}\ntrain: images\nval: images\ntest: images\nnames:\n{names}\n"
    )
    print(f"Export YOLO : {yolo_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Génère le dataset synthétique de cartes.")
    parser.add_argument("--out-dir", default="data/synthetic")
    parser.add_argument("--cards-dir", default="data/cards")
    parser.add_argument("--n-train", type=int, default=20000)
    parser.add_argument("--n-val", type=int, default=2000)
    parser.add_argument("--n-test", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--yolo", action="store_true", help="exporte aussi le split test au format YOLO")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    card_images = load_card_images(args.cards_dir)
    for offset, (split, n_images) in enumerate([("train", args.n_train), ("val", args.n_val), ("test", args.n_test)]):
        print(f"Génération de {split}...")
        generate_split(out_dir / split, n_images, card_images, args.seed + offset)

    if args.yolo:
        export_yolo(out_dir / "test", out_dir / "yolo")


if __name__ == "__main__":
    main()
