# Reconstruction structurelle de documents administratifs à l'aide de l'IA

> Mini-projet utilisant **PaddleOCR** pour détecter, reconnaître et reconstruire automatiquement la structure de documents administratifs (attestations, formulaires, courriers officiels…).

---

## Objectif

Automatiser l'analyse de documents administratifs en :
- **Détectant** les zones de texte (en-tête, corps, pied de page)
- **Reconnaissant** le texte avec une haute précision (≥ 95%)
- **Reconstruisant** la structure logique du document (titre, champs, signature, tampon…)
- **Visualisant** le résultat annoté avec code couleur par zone

---

## Technologies utilisées

| Bibliothèque     | Version   | Rôle                                      |
|------------------|-----------|-------------------------------------------|
| PaddlePaddle     | 2.6.2     | Framework deep learning (backend OCR)     |
| PaddleOCR        | 2.7.0.3   | Détection + reconnaissance de texte       |
| OpenCV           | 4.6.0.66  | Traitement d'image, annotation visuelle   |
| NumPy            | 1.26.4    | Calculs matriciels                        |
| Pillow           | 12.1.1    | Génération et manipulation d'images       |
| Matplotlib       | 3.10.8    | Visualisation des résultats               |
| Pandas           | 3.0.1     | Structuration des données extraites       |

---

## Structure du projet

```
paddle-mini-project/
│
├── paddle_env/                        # Environnement virtuel Python
│
├── test_document_reconstruction.py    # Script principal du mini-projet
├── verify.py                          # Script de vérification de l'environnement
│
├── sample_admin_doc.png               # Document administratif généré (test)
├── document_reconstruction_result.png # Résultat annoté de la reconstruction
│
└── README.md                          # Ce fichier
```

---

## Installation

### 1. Activer l'environnement virtuel
```cmd
cd C:\Users\lakhdar chenene\Downloads\paddle-mini-project
paddle_env\Scripts\activate.bat
```

### 2. Vérifier les dépendances
```cmd
python verify.py
```

---

## Utilisation

```cmd
python test_document_reconstruction.py
```

Le script effectue automatiquement **4 étapes** :

| Étape | Description |
|-------|-------------|
| 1️⃣ Génération | Crée un document administratif synthétique (Attestation de scolarité) |
| 2️⃣ OCR | Lance PaddleOCR pour détecter et reconnaître tous les blocs de texte |
| 3️⃣ Reconstruction | Classe les blocs par zone : `EN-TÊTE / CORPS / PIED DE PAGE` |
| 4️⃣ Visualisation | Génère une image annotée + rapport textuel complet |

---

## Résultats obtenus

```
Total blocs détectés : 31
Confiance moyenne    : 98.7 %

[EN-TÊTE]  →  4 blocs   (titre, ministère, université)
[CORPS]    → 25 blocs   (champs étudiant, paragraphes, signature, cachet)
[PIED]     →  2 blocs   (mention légale, numéro de page)
```

---

## Auteur

**CHENENE Lakhdar** — Mini-projet IA, Mars 2026
