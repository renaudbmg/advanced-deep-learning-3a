# advanced-deep-learning-3a

Projet de Deep Learning avancé : réseau de neurones multimodal (texte et image).

## Équipe

- Renaud Baumgarten
- Romain Chenot
- Mathis Isaac

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Structure

- `scratch/` : partie 1, le modèle construit de A à Z. Un sous-dossier par partie du travail, chacun avec un README qui explique ses décisions ([scratch/README.md](scratch/README.md)).
  - `scratch/dataset_generation/` : génération du dataset synthétique de cartes à jouer ([README](scratch/dataset_generation/README.md))
- `notebooks/` : notebooks d'exploration communs
- `docs/` : rapport, supports de soutenance, liens utiles

Le dossier `data/` (cartes téléchargées, dataset généré) n'est pas versionné.

## Démarrage rapide

Depuis la racine du repo :

```bash
python -m scratch.dataset_generation.assets              # télécharge les 52 cartes dans data/cards/
python -m scratch.dataset_generation.generate_dataset    # génère le dataset dans data/synthetic/
```
