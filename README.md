# Projet de Dessin Technique – Kivy

Ce projet est une application Kivy permettant la création de dessins techniques basés sur des points et segments, avec des outils interactifs comme des fenêtres modales pour définir la géométrie.

## 📦 Fonctionnalités principales

- Dessin de points et segments
- Définition de longueur (`L`) ou d’angle (`α`) via popup personnalisée
- Sauvegarde des données sous forme JSON
- Architecture modulaire avec outils extensibles

## 🗂️ Structure du projet

    🔤 Nomenclature des différentes valeurs selon leur affectation :
        - val_base() → retourne un int (ex. en µm : 10000)
            → Valeur en unité de base (unité fixe)
        - val_work() → retourne un float (ex. en mm : 10.0)
            → Valeur en unité utilisateur (machine)
        - val_disp() → retourne un str (ex. "20.00 mm")
            → Valeur en unité affichée à l’écran (facteur visuel inclus, ex. diamètre)

    ✅ Orientation de référence : Z horizontal, X vertical
        Sur un tour, l’axe Z est horizontal (axe de rotation), et l’axe X est vertical (profondeur de passe).
            Donc sur ton dessin :
                Z = axe horizontal, de gauche à droite → 0°
                X = axe vertical, de bas en haut → 90°
        📐 Convention d’angle :
            Angle 0° : vers la droite (Z positif)
            Angle 90° : vers le bas (X positif)
            Angle 180° : vers la gauche (Z négatif)
            Angle 270° : vers le haut (X négatif)
        C’est exactement le référentiel usiné/atelier → gardons-le partout.

    project_root/
    ├── i18n/               # Dictionnaire de traduction pour l'interface ("A mettre en place")
    │   ├── fr.json
    │   ├── en.json
    │   └── __init__.py   ← avec une fonction globale `tr("key")`
    |
    ├── table/              # Dossier pour tabels informatives
    │   ├── tolerance/          # Dossier pour tables de tolérances
    │   | ├── ISO.py                # Provisoir: Idée de configuration pour tolérance ISO
    │   | ├── ...                   # ...
    │   └── Macine/             # Dossier tabels porpre à la machine
    │     ├── ...                   # Table machine: vitesse; avance; filet; ...
    |
    |
    ├─── utils.py           # utilitaires globaux (structure, format, log.txt, etc...)
    ├── ui_configurator/    # Dossier thèmes et autre configurations de l'écran
    │   └── ...                 # ...
    ├──v config.py          # Paramètres globaux et constantes (structure, accès facile)
    ├──^ user_settings.json  # Paramètres persistants utilisateur (unité, thème, etc.)
    |
    │
    ├── main.py             # Point d’entrée de l’application
    ├── common_widgets.py   # Composants UI réutilisables (MyLabel, Separator, etc.)
    ├── common_draw.py      # Méthodes commune pour le dessin de profils
    │
    ├── part/               # Modules fonctionnels liés au dessin de la pièce
    │ ├── draw_data.py          # Modèle : données de base et logique métier
    │ ├─v draw_pnt_manager.py   # Gestion des coordonées de dessin et du fichier de sauvegarde (draw_point.json)
    │ ├─^ draw_point.json       # Fichier de sauvegarde (liste de points, segments)
    │ ├── draw_form.py          # Vue principale pour l’affichage graphique
    │ ├── __init__.py           # Initialise le package part
    │ ├── draw_tool/            # Outils annexes (fenêtres modales, etc.)
    │ | ├── popup_segment.py        # Popup pour définir la longueur ou l’angle
    │ | ├── future_modal.py         # Autres modales avancées (en développement)
    │ | └── __init__.py             # Initialise le package draw_tool
    | └── shapes/               ← dessin de terminaison sur point
    │   ├── __init__.py             ← registre des formes + fonction get_shape_class(type)
    │   ├── base_shape.py           ← classe de base ShapeType  
    │   ├── shape_registry.py       ← Registre pour les formes de terminaison disponibles (programme et plugin)
    │   ├── shape_editor.py         ← Formulaire pour l'édition/définition d'un shape
    │   ├── fillet.py               ← classe `FilletShape`
    │   ├── round_corner.py         ← classe `RoundedCornerShape`
    │   ├── round_corner2.py        ← classe `RoundedCornerShapeNew`
    │   ├── chamfer.py              ← classe `ChamferShape`
    │   ├── thread_relief_iso.py    ← classe `gorge de filatge ISO`
//    │   └── plugin_loader.py        ← plus tard, pour charger des plugins externes
    │
    ├── cutting_tool/       # Modules fonctionnels liés au dessin du burin
    │   ├─v TurnCut.py          # Editeur d'outils de coupe
    │   ├─v Insert.py           // classe de la plaquette
    │   ├─^ tool_lib.json       # Fichier de sauvegarde (librairie d'outils)
    │   └── __init__.py           # Initialise le package tool: TurnCut
//    │   ├── insert/
    |
    .... Uniquement pour test ou debugage ....
    ├── main_temp.py             # lanceur pour tester draw_data

    /dro_viewer/
    │
    ├── dro_viewer.py            # Layout principal + gestion globale
    ├── dro_viewer.kv
    │
    ├── dro_tool/
    │   ├── dro_axis.py         # ⚙️ popups / outils liés aux axes
    │   ├── dro_cutter.py      # 🏗️ outils / ofsset / état
    │   ├── dro_machine.py      # 🏗️ machine / homing / état
    │   ├── dro_user.py         # 👤 profil utilisateur, préférences
    │   ├── dro_comm.py         # 🔌 communication MCU / port série
    │   └── dro_drawing.py      # 🧭 affichage, points, graph, etc.
    │
    └── __init__.py

## ▶️ Lancer l’application

Assurez-vous d’avoir installé [Kivy](https://kivy.org/).

```bash
pip install kivy
python main.py

```

Aide pour la mise en place de forme sur point :
------------------------------------------------
 📐 Raccords entre segments (avec ou sans transition) :
    Chanfrein (45° ou autre)
    Congé (raccord tangentiel concave ou convexe)
    Rayon (non nécessairement tangent)
    Décrochement (forme libre de transition, souvent non normée)
    Épaulement (forme normée, souvent perpendiculaire)
    Gorge (filetage)
    Saignée (portée précise)
    Rainure (fonctionnelle : circlip, clavette, gaissage, etc.)
    Lamage (pour vis)
    (Eventuellement) Arrondi (populaire, moins normé)