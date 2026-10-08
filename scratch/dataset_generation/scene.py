"""Génération d'une scène synthétique : quelques cartes posées sur un fond aléatoire.

Comme c'est nous qui posons les cartes, on connaît la boîte exacte de chacune :
les annotations sont parfaites et gratuites.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from .cards import DECK


def load_card_images(cards_dir="data/cards"):
    images = {}
    for card in DECK:
        path = Path(cards_dir) / card.filename
        if not path.exists():
            raise FileNotFoundError(f"{path} introuvable. Lance d'abord : python -m scratch.dataset_generation.assets")
        images[card] = Image.open(path).convert("RGBA")
    return images


def random_background(rng, size):
    kind = rng.integers(3)
    if kind == 0:  # couleur unie
        array = np.broadcast_to(rng.integers(0, 256, 3), (size, size, 3)).astype(np.float32)
    elif kind == 1:  # dégradé entre deux couleurs
        t = np.linspace(0, 1, size)[:, None, None]
        array = np.broadcast_to(rng.integers(0, 256, 3) * (1 - t) + rng.integers(0, 256, 3) * t, (size, size, 3))
        if rng.random() < 0.5:
            array = array.transpose(1, 0, 2)
    else:  # taches de couleur floues
        low = rng.integers(0, 256, (4, 4, 3)).astype(np.uint8)
        array = np.asarray(Image.fromarray(low).resize((size, size), Image.BICUBIC), dtype=np.float32)
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))


def overlap_ratio(a, b):
    """Part de la plus petite des deux boîtes [x1, y1, x2, y2] recouverte par l'autre."""
    width = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    smallest = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return width * height / smallest


def augment(image, rng):
    """Retouches de l'image entière, cartes comprises."""
    image = ImageEnhance.Brightness(image).enhance(rng.uniform(0.7, 1.3))
    image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.7, 1.3))
    if rng.random() < 0.3:
        image = image.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 1.2)))
    # Grain en dernier, comme le bruit d'un capteur de caméra : il couvre aussi les cartes
    array = np.asarray(image, dtype=np.float32) + rng.normal(0, 6, (image.height, image.width, 3))
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))


def perspective_coefficients(output_points, input_points):
    """Les 8 coefficients qu'attend Image.transform(..., Image.PERSPECTIVE, ...).

    PIL calcule, pour chaque pixel (x, y) de l'image de sortie, la position
    correspondante dans l'image d'entrée :
        ((a x + b y + c) / (g x + h y + 1), (d x + e y + f) / (g x + h y + 1))
    Chaque couple de points (sortie -> entrée) donne deux équations : avec 4 coins,
    on obtient un système linéaire de 8 équations à 8 inconnues.
    """
    matrix, target = [], []
    for (x, y), (u, v) in zip(output_points, input_points):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        target += [u, v]
    return np.linalg.solve(np.array(matrix, dtype=np.float64), np.array(target, dtype=np.float64))


def perspective(sprite, rng, strength):
    """Déforme la carte comme si elle était vue en biais.

    Chaque coin est rapproché du centre d'une fraction aléatoire (entre 0 et strength)
    de la largeur et de la hauteur. Les coins ne font que rentrer : la carte déformée
    reste dans son canevas, et ce qui est hors de la carte reste transparent.
    """
    w, h = sprite.size
    dx = rng.uniform(0, strength, 4) * w
    dy = rng.uniform(0, strength, 4) * h
    corners = [(0, 0), (w, 0), (w, h), (0, h)]  # haut-gauche, haut-droit, bas-droit, bas-gauche
    moved = [(dx[0], dy[0]), (w - dx[1], dy[1]), (w - dx[2], h - dy[2]), (dx[3], h - dy[3])]
    coefficients = perspective_coefficients(moved, corners)
    return sprite.transform((w, h), Image.PERSPECTIVE, coefficients, Image.BICUBIC)


def place_cards(image, card_images, rng, n_cards, base_height, max_rotation, max_perspective, max_overlap, max_tries=50):
    """Colle des cartes au hasard. Une carte qui ne trouve pas de place libre est abandonnée."""
    size = image.width
    cards, boxes = [], []
    for index in rng.choice(len(DECK), size=n_cards, replace=False):
        card = DECK[index]
        sprite = card_images[card]
        height = round(base_height * rng.uniform(0.9, 1.1))  # ±10 % autour de la taille de l'image
        # Intensité tirée par carte : de quasiment à plat à nettement penchée
        sprite = perspective(sprite, rng, rng.uniform(0, max_perspective))
        sprite = sprite.crop(sprite.getchannel("A").getbbox())
        # Redimensionner après la perspective, qui rétrécit la carte : elle retrouve la hauteur tirée
        sprite = sprite.resize((round(sprite.width * height / sprite.height), height), Image.LANCZOS)
        sprite = sprite.rotate(rng.uniform(-max_rotation, max_rotation), resample=Image.BICUBIC, expand=True)
        sprite = sprite.crop(sprite.getchannel("A").getbbox())  # boîte serrée autour de la carte déformée
        if max(sprite.size) > size:  # garde-fou : la carte doit tenir dans l'image
            sprite.thumbnail((size, size), Image.LANCZOS)

        for _ in range(max_tries):
            x = int(rng.integers(0, size - sprite.width + 1))
            y = int(rng.integers(0, size - sprite.height + 1))
            box = [x, y, x + sprite.width, y + sprite.height]
            if all(overlap_ratio(box, other) <= max_overlap for other in boxes):
                image.paste(sprite, (x, y), sprite)
                cards.append(card)
                boxes.append(box)
                break
    return cards, boxes


# Probabilité de chaque nombre de cartes visé : 0, 1, 2, 3, 4, 5.
N_CARDS_PROBS = (0.05, 0.20, 0.25, 0.25, 0.15, 0.10)

# Hauteur des cartes, en pixels. On tire une hauteur par image, comme une distance à la
# caméra : toutes les cartes d'une image ont à peu près la même taille. La hauteur
# maximale baisse avec le nombre de cartes, pour qu'elles tiennent dans l'image.
MIN_CARD_HEIGHT = 50
MAX_CARD_HEIGHT = {0: 200, 1: 200, 2: 150, 3: 120, 4: 105, 5: 95}


def make_scene(
    card_images,
    rng,
    image_size=256,
    n_cards_probs=N_CARDS_PROBS,
    max_rotation=20,
    max_perspective=0.15,
    max_overlap=0.1,
):
    """Retourne (image RGB, liste de cartes, liste de boîtes [x1, y1, x2, y2] en pixels).

    Le nombre de cartes posées peut être inférieur au nombre visé : une carte qui ne
    trouve pas de place libre est abandonnée.
    """
    image = random_background(rng, image_size)
    n = int(rng.choice(len(n_cards_probs), p=n_cards_probs))
    base_height = rng.uniform(MIN_CARD_HEIGHT, MAX_CARD_HEIGHT[n])
    cards, boxes = place_cards(image, card_images, rng, n, base_height, max_rotation, max_perspective, max_overlap)
    return augment(image, rng), cards, boxes
