import json

# Plages de diamètre standard ISO (limites : d_min, d_max)
diameter_ranges = [
    (0, 3),
    (3, 6),
    (6, 10),
    (10, 18),
    (18, 30),
    (30, 50),
    (50, 80),
    (80, 120),
    (120, 180),
    (180, 250),
    (250, 315),
    (315, 400),
    (400, 500)
]

# Table ISO des IT1 à IT18 (en µm) pour chaque plage de diamètre
IT_values = {
    "IT1":  [0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 1.5, 2.0, 2.5, 3.0, 3.5],
    "IT2":  [0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5],
    "IT3":  [0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0],
    "IT4":  [1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0,10.0,11.0],
    "IT5":  [2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0,10.0,11.0,13.0,14.0],
    "IT6":  [3.0, 4.0, 5.0, 6.0, 8.0, 9.0,11.0,13.0,15.0,18.0,20.0,22.0,25.0],
    "IT7":  [4.0, 5.0, 6.0, 8.0,10.0,11.0,13.0,16.0,19.0,22.0,25.0,29.0,32.0],
    "IT8":  [6.0, 7.0, 8.0,10.0,13.0,14.0,16.0,20.0,23.0,27.0,31.0,35.0,40.0],
    "IT9":  [10.0,12.0,14.0,16.0,18.0,20.0,23.0,25.0,30.0,36.0,40.0,46.0,52.0],
    "IT10": [14.0,16.0,18.0,20.0,23.0,25.0,29.0,32.0,37.0,43.0,48.0,54.0,61.0],
    "IT11": [20.0,22.0,25.0,28.0,30.0,35.0,40.0,46.0,52.0,57.0,63.0,70.0,78.0],
    "IT12": [25.0,30.0,35.0,40.0,45.0,50.0,57.0,64.0,70.0,76.0,84.0,92.0,102.0],
    "IT13": [40.0,50.0,60.0,70.0,80.0,90.0,100.0,115.0,130.0,140.0,160.0,175.0,190.0],
    "IT14": [60.0,70.0,80.0,90.0,100.0,110.0,120.0,140.0,160.0,180.0,200.0,220.0,240.0],
    "IT15": [100.0,120.0,140.0,160.0,180.0,200.0,220.0,250.0,280.0,315.0,350.0,385.0,430.0],
    "IT16": [140.0,160.0,180.0,200.0,220.0,250.0,280.0,320.0,360.0,400.0,440.0,480.0,520.0],
    "IT17": [250.0,290.0,320.0,360.0,400.0,440.0,480.0,530.0,580.0,630.0,700.0,760.0,840.0],
    "IT18": [400.0,460.0,510.0,570.0,630.0,700.0,770.0,850.0,930.0,1010.0,1100.0,1200.0,1300.0]
}

# Construire le dictionnaire JSON
IT_table = {
    "INFO": "Chaque clé ITx contient une liste de triplets [d_min, d_max, IT_en_µm] valables pour diamètre (d_min < Ø ≤ d_max).",
    "units": "µm",
    "source": "ISO 286-1/2 (jusqu’à Ø500 mm, valeurs standards arrondies)"
}

# Ajouter les ITs
for grade, values in IT_values.items():
    IT_table[grade] = []
    for (d_min, d_max), IT in zip(diameter_ranges, values):
        IT_table[grade].append([d_min, d_max, IT])

# Export JSON
with open("IT_table.json", "w", encoding="utf-8") as f:
    json.dump(IT_table, f, indent=2)

print("✅ Fichier 'IT_table.json' généré.")



--------------------------------------------------------------------------------------------------------------------------

import json

# Table des positions optimisée
optimized_position_table = {
    "INFO": "Format : [d_min, d_max, base, direction] avec direction '+' = IT ajouté (base = min), '-' = IT retiré (base = max), '±' = symétrique. '*' = tous IT. Unités : µm.",
    "units": "µm",
    "source": "ISO 286, positions optimisées pour Ø 0–500 mm.",
    
    "shafts": {
        "h": {"*": [[0, 500, 0, "-"]]},
        "js": {
            "*": [[0, 500, 0, "±"]]
        },
        "k": {
            "*": [
            [0, 3, 0, "+"],
            [3, 18, 1, "+"],
            [18, 80, 2, "+"],
            [80, 180, 3, "+"],
            ...
        },
        "m": {
            "*": [
            [0, 3, 2, "+"],
            [3, 6, 4, "+"],
            [6, 10, 6, "+"],
            [10, 18, 7, "+"],
            ...
        },
        "n": {
            "*": [
            [0, 3, 4, "+"],
            [3, 6, 8, "+"],
            [6, 10, 10, "+"],
            [10, 18, 12, "+"],
            ...
        }
    },
    "holes": {
        "H": {"*": [[0, 500, 0, "+"]]},
        "K": {
          "IT6": [
            [0, 3, -9, "+"],
            [3, 6, -11, "+"],
            ...
          ],
          "IT7": [
            [0, 3, -13, "+"],
            ...
          ]
        },
        "M": {
            "IT5": [[0, 500, -20, "+"]],
            "IT6": [[0, 500, -23, "+"]],
            "IT7": [[0, 500, -29, "+"]]
        },
        "N": {
            "IT5": [[0, 500, -30, "+"]],
            "IT6": [[0, 500, -33, "+"]],
            "IT7": [[0, 500, -39, "+"]]
        }
    }
}

# Export JSON
with open("positions_table_optimized.json", "w", encoding="utf-8") as f:
    json.dump(optimized_position_table, f, indent=2)

print("✅ Fichier 'positions_table_optimized.json' généré.")



===================================================================================================================

import json

# Chargement des fichiers JSON
with open("IT_table.json", encoding="utf-8") as f:
    IT_TABLE = json.load(f)

with open("positions_table_optimized.json", encoding="utf-8") as f:
    POS_TABLE = json.load(f)

def get_position(diameter, letter, IT_grade):
    """
    Retourne (min, max) en µm pour un diamètre, une lettre (ex: 'h', 'H', 'k', ...) et un IT (ex: 'IT7').
    La fonction détecte automatiquement si c’est un arbre ou un alésage via la casse.
    """
    # Déduire type selon la casse
    if letter.islower():
        type_ = "shafts"
    elif letter.isupper():
        type_ = "holes"
    else:
        raise ValueError(f"Lettre inconnue ou mal formée : {letter}")

    # Accès à la position de base
    group = POS_TABLE.get(type_)
    if not group:
        raise ValueError(f"Type inconnu : {type_}")
    
    letter_data = group.get(letter)
    if not letter_data:
        raise ValueError(f"Aucune donnée pour la lettre : {letter} ({type_})")
    
    rules = letter_data.get(IT_grade) or letter_data.get("*")
    if not rules:
        raise ValueError(f"Aucune règle pour {letter} {IT_grade}")

    # Recherche de la valeur IT correspondante au diamètre
    it_list = IT_TABLE.get(IT_grade)
    if not it_list:
        raise ValueError(f"Grade IT inconnu : {IT_grade}")

    IT_value = None
    for dmin, dmax, it_val in it_list:
        if dmin < diameter <= dmax:
            IT_value = it_val
            break
    if IT_value is None:
        raise ValueError(f"Diamètre {diameter} mm hors plage pour {IT_grade}")

    # Application de la position
    for dmin, dmax, base, direction in rules:
        if dmin < diameter <= dmax:
            if direction == "+":
                return (base, base + IT_value)
            elif direction == "-":
                return (base - IT_value, base)
            elif direction == "±":
                return (-IT_value / 2, +IT_value / 2)
            else:
                raise ValueError(f"Direction inconnue : {direction}")
    
    raise ValueError(f"Aucune plage trouvée pour diamètre {diameter} mm dans {letter} {IT_grade}")

# ➕ Fonctions pratiques (optionnelles)

def get_position_mm(diameter, letter, IT_grade):
    """Retourne (min, max) en mm"""
    min_um, max_um = get_position(diameter, letter, IT_grade)
    return (min_um / 1000.0, max_um / 1000.0)

def get_tolerance(diameter, letter, IT_grade):
    """Retourne la tolérance totale (max - min) en µm"""
    min_um, max_um = get_position(diameter, letter, IT_grade)
    return max_um - min_um

# 🧪 Exemple d’utilisation
if __name__ == "__main__":
    tests = [
        (49.95, "h", "IT6"),
        (49.95, "H", "IT6"),
        (49.95, "k", "IT6"),
        (49.95, "K", "IT7"),
        (200, "js", "IT13"),
        (120, "H", "IT13"),
        (2.5, "m", "IT6")
    ]

    for diam, letter, IT in tests:
        try:
            min_, max_ = get_position(diam, letter, IT)
            print(f"{letter}{IT} @ {diam:.2f} mm → min: {min_} µm, max: {max_} µm (±{(max_ - min_) / 2:.1f})")
        except ValueError as e:
            print(f"❌ Erreur : {e}")









