# Génération du dataset

Responsable : Renaud Baumgarten

Ce dossier génère un dataset synthétique d'images de cartes à jouer, avec la **boîte et le nom de chaque carte**.

## Utilisation

Depuis la racine du repo :

```bash
python -m scratch.dataset_generation.assets              # 1. télécharge les 52 cartes dans data/cards/ (une seule fois)
python -m scratch.dataset_generation.generate_dataset    # 2. génère le dataset dans data/synthetic/
```

Options de `generate_dataset` :

| Option | Défaut | Rôle |
|---|---|---|
| `--n-train`, `--n-val`, `--n-test` | 20 000, 2 000, 2 000 | Nombre d'images par split |
| `--out-dir` | `data/synthetic` | Dossier de sortie |
| `--cards-dir` | `data/cards` | Dossier des images de cartes |
| `--seed` | 0 | Graine du split train ; val et test utilisent `seed + 1` et `seed + 2` |
| `--yolo` | désactivé | Exporte aussi le split test au format YOLO |

Le notebook [visualisation.ipynb](visualisation.ipynb) affiche des exemples d'images avec leurs boîtes, et des statistiques sur le dataset.

## Les fichiers

| Fichier | Rôle |
|---|---|
| [cards.py](cards.py) | Les 52 cartes et leurs attributs : rang, enseigne, couleur, figure ou non, nom, `class_id`. |
| [assets.py](assets.py) | Télécharge les images des cartes depuis Wikimedia Commons. |
| [scene.py](scene.py) | Compose une image : fond, placement des cartes, retouches. Renvoie l'image, les cartes et leurs boîtes. |
| [generate_dataset.py](generate_dataset.py) | Répète la composition pour chaque image, écrit les images et `annotations.json`, et l'export YOLO. |

## Format des données produites

C'est ce que lit l'entraînement.

```
data/synthetic/{train,val,test}/images/000000.jpg
data/synthetic/{train,val,test}/annotations.json
data/synthetic/yolo/                              (avec --yolo)
```

```json
{
  "image_size": 256,
  "items": [{
    "image": "images/000000.jpg",
    "cards": [
      {"name": "ace of clubs", "class_id": 38, "box": [14, 22, 102, 121]},
      {"name": "7 of hearts", "class_id": 5, "box": [131, 98, 214, 191]}
    ]
  }]
}
```

- `box` : `[x1, y1, x2, y2]` en pixels, coins haut-gauche et bas-droit. `x2` et `y2` sont exclusifs : la largeur vaut `x2 − x1`.
- `class_id` : numéro de la carte de 0 à 51, égal à `enseigne × 13 + rang` (enseignes : hearts, diamonds, clubs, spades ; rangs : 2 à 10, jack, queen, king, ace).
- `cards` peut être vide : c'est une image sans carte.
- Export YOLO : un fichier `.txt` par image, une ligne `class_id cx cy w h` par carte (valeurs entre 0 et 1), et un fichier vide pour une image sans carte. `data.yaml` liste les 52 noms de classes.

## Décisions

### Les images des cartes

| Décision | Pourquoi |
|---|---|
| Jeu de **Byron Knoll**, dans le domaine public | Libre de droits, complet (52 cartes) et au design standard. |
| Téléchargement via l'**API Wikimedia**, qui fournit une version PNG de 250 px de large |

### La composition d'une image ([scene.py](scene.py))

| Décision | Valeur | Pourquoi |
|---|---|---|
| Taille de l'image | 256×256 | Assez grand pour lire le coin d'une carte, assez petit pour entraîner sur un portable. |
| Nombre de cartes visé | 0 : 5 %, 1 : 20 %, 2 : 25 %, 3 : 25 %, 4 : 15 %, 5 : 10 % (`N_CARDS_PROBS`) | Les **images vides** apprennent au détecteur à ne rien voir quand il n'y a rien, au lieu d'inventer une carte dans le fond. Les **images à une carte** imitent le cas typique d'une démo : on montre une carte à la webcam. |
| Tirage des cartes | Sans remise | Une carte apparaît au plus une fois par image, comme avec un vrai jeu. |
| Hauteur des cartes | Une hauteur par image, entre 50 px et un maximum qui dépend du nombre de cartes (200 px pour 0 ou 1 carte, 150 pour 2, 120 pour 3, 105 pour 4, 95 pour 5), puis ±10 % par carte (`MIN_CARD_HEIGHT`, `MAX_CARD_HEIGHT`) | À la webcam, une carte peut être tenue près de l'objectif ou posée loin. Tirer la taille par image imite une distance à la caméra : les cartes posées sur une même table ont à peu près la même taille. Le maximum baisse avec le nombre de cartes pour qu'elles tiennent toutes dans l'image. |
| Perspective | Intensité tirée par carte entre 0 et 15 % (`max_perspective`) ; chaque coin est rapproché du centre d'une fraction aléatoire de cette intensité | Imite une carte vue en biais, qui devient un trapèze. L'intensité par carte garde aussi des cartes presque à plat (environ 20 %), comme une carte tenue face à la caméra. |
| Rotation | −20° à +20° | Imite des cartes posées à la main, sans les rendre méconnaissables. |
| Position | Tirée au hasard, carte toujours **entièrement** dans l'image | Simple, et chaque boîte correspond à une carte complète. |
| Chevauchement maximal | 10 % (`max_overlap`) | Chaque carte reste presque entièrement visible, coin avec sa valeur compris. Sans cette règle, des cartes pourraient être presque totalement cachées tout en restant dans les annotations. |
| Essais de placement | 50 par carte | Au-delà, la carte est abandonnée et l'image en a une de moins. |

**La règle des 10 %** se calcule sur les boîtes : aire de la zone commune aux deux boîtes divisée par l'aire de la **plus petite** des deux (`overlap_ratio()`). On divise par la plus petite pour qu'une petite carte ne puisse jamais être cachée en grande partie par une grande. On compare des boîtes plutôt que des pixels parce que c'est simple et rapide, et parce que c'est ce qui compte pour un détecteur : deux boîtes qui se recouvrent beaucoup sont difficiles à séparer, et la NMS risquerait de les fusionner. Cette règle décide seulement si une position est acceptée ; elle ne modifie jamais les boîtes.

### Le calcul des boîtes

Les boîtes ne sont pas déduites de l'image finale : elles viennent de la façon dont on colle chaque carte (`place_cards()`).

1. La carte est déformée en perspective (`perspective()`, avec `Image.transform` de PIL et les coefficients calculés par `perspective_coefficients()`), recadrée, redimensionnée à la hauteur tirée, puis tournée avec `expand=True`. Les zones ajoutées autour de la carte restent transparentes. Le redimensionnement vient après la perspective, qui rétrécit la carte : la hauteur tirée est ainsi respectée.
2. On la découpe au ras de ses pixels non transparents : `sprite.crop(sprite.getchannel("A").getbbox())`. Les dimensions de l'image découpée sont alors exactement celles de la boîte.
3. On tire la position `(x, y)` du coin haut-gauche. La boîte vaut `[x, y, x + largeur, y + hauteur]`.
4. On colle la carte avec sa transparence comme masque : les coins laissent voir le fond.

Les boîtes sont donc **exactes au pixel près**, sans annotation manuelle. Elles sont alignées sur les axes, comme en détection classique.

### Le fond et les retouches

| Décision | Valeur | Pourquoi |
|---|---|---|
| Type de fond | Couleur unie, dégradé (vertical ou horizontal) ou taches de couleur floues, 1 chance sur 3 chacun | Le détecteur ne peut pas apprendre un raccourci lié à un fond particulier. |
| Luminosité, contraste | Facteur entre 0,7 et 1,3, sur l'image entière | Imite des éclairages différents. |
| Flou gaussien | 30 % des images, rayon 0,3 à 1,2 px | Imite une mise au point imparfaite. |
| Grain | Bruit gaussien, écart-type 6 sur 255, ajouté en dernier sur l'image entière, cartes comprises | Imite le bruit d'un capteur. Il était d'abord appliqué au fond seulement : les cartes, parfaitement nettes, se distinguaient du fond par ce seul détail, un raccourci qu'un détecteur aurait pu apprendre. |
| Format | JPEG qualité 92 | Fichiers légers, artefacts de compression faibles et proches d'une vraie caméra. |

### La production du dataset ([generate_dataset.py](generate_dataset.py))

| Décision | Pourquoi |
|---|---|
| Génération **sur disque**, une fois pour toutes | On peut ouvrir les images pour vérifier, le dataset est le même pour tout le groupe, et la génération ne ralentit pas l'entraînement. |
| **Graine fixe** par split | Relancer la commande redonne exactement les mêmes images, et train, val et test sont différents. |