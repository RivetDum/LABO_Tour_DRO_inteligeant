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
            → Valeur en unité utilisateur (machine) (pour un tour par ex, on est toujours au rayon)
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
    │   ├── ... TODO: A competter
    │   └── __init__.py   ← avec fonction globale `tr("key") , Tr("key") , TR("key")`
    |    info>> tr: comme dans le dictionnaire ; Tr: avec le premier caractère majuscule ; TR: tous en majuscules
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
    │ ├── profil_machine_actif.json # Save profile à usiner partagé avec la machine (voir reel_time/machine_mcu.py)
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
    │ //  └── plugin_loader.py        ← plus tard, pour charger des plugins externes
    │
    ├── cutting_tool/       # Modules fonctionnels liés au dessin du burin
    │   ├─v TurnCut.py              # Editeur d'outils de coupe
    │   ├─v Insert.py               // classe de la plaquette
    │   ├─^ tool_lib.json           # Fichier de sauvegarde (librairie d'outils)
    │   └── __init__.py             # Initialise le package tool: TurnCut
    │  // ├── insert/
    |
    | .... Uniquement pour test ou debugage ....
    ├── main_temp.py             # lanceur pour tester draw_data
    |
    │ /dro_viewer/
    ├── dro_viewer.py            # Layout principal + gestion globale
    ├── dro_viewer.kv
    │
    ├── dro_tool/
    │   ├── dro_axis.py         # ⚙️ popups / outils liés aux axes
    │   ├── dro_cutter.py       # 🏗️ outils / ofsset / état
    │   ├── dro_machine.py      # 🏗️ machine / homing / état
    │   ├── dro_user.py         # 👤 profil utilisateur, préférences
    │   ├── dro_comm.py         # 🔌 communication MCU / port série ==> ?? A remplacer par reel_time/machine_mcu.py ??
    │   └── dro_drawing.py      # 🧭 affichage, points, graph, etc.
    │
    │
    ├── machine_tool/
    │   ├─v machine_data.py     # gère la configuration des MCU machine
    │   └─^ TODO: json de sauvegarde à faire
    |
    ├── reel_time/              # gestion de communication haut débit
    │   └── machine_mcu.py      # gestion de la communiquation entre la machine (mcu = ESP32-S3) et ce logiciel
    |
    | 
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

# 🛠️ Stratégie Cinématique ESP32 : Algorithme Anti-Collision & Rayon de Bec
        Ce document résume la logique géométrique hybride validée pour le calcul temps réel de la compensation du rayon de bec du burin et l'évitement prédictif des collisions (look-ahead) sur l'ESP32.

        ## 📐 1. Architecture Globale : Répartition des rôles (Kivy ↔️ ESP32)
        * **Kivy (Le Cerveau CAO)** : Dispose de la puissance de calcul. Il utilise les Bounding Boxes (BBox) ultra-précises de la pièce pour filtrer la géométrie et envoyer régulièrement (min. 40Hz) à l'ESP32 uniquement les **3 à 5 segments maîtres** les plus proches du burin.
        * **ESP32 (La Sécurité Haute Vitesse)** : Libéré du tri lourd, il tourne sa loop à haute fréquence exclusivement sur ce sous-ensemble de segments pour calculer les distances, anticiper l'inertie des manivelles et piloter l'axe incliné (moteur pas-à-pas).

        ## 🧮 2. Modélisation de l'Outil (La Plaquette)
        * L'ESP32 ne calcule pas le corps complexe en acier du burin pour ne pas saturer son processeur.
        * L'outil est résumé à **un cercle de sécurité unique de rayon combiné ($R_{\text{outil}} + \text{offset\_usinage}$)** centré sur son point pilote théorique `(0,0)`.

        ## 🔄 3. Algorithme Hybride d'Usinage des Arcs (Facettes ↔️ Cercle Continu)
        Pour garantir à la fois la légèreté informatique et un état de surface parfaitement lisse (sans facettes), l'arc de cercle est traité par un double système :

        ### A. Le Filtre d'Approche par Facettes (L'Interrupteur)
        * Au chargement, l'arc de la pièce est décomposé virtuellement en **petites facettes de droites (ex: tous les 20°)**, dotées de leurs propres BBox.
        * **Règle Spécifique des Rayons Circonscrits (Convexes)** : Le premier et le dernier segment de l'arc sont obligatoirement des **demi-segments** partant pile du point de tangence initial (0°) pour éliminer tout débordement de sécurité dans le vide et éviter les faux déclenchements.

        ### B. L'Aiguillage Dynamique dans la Loop (Au micron près)
        À chaque cycle, l'ESP32 compare en direct la position du burin par rapport à la droite tangente de la pièce et la facette d'entrée de l'arc :
        1. **Tant que la facette est plus loin que la droite tangente** ➡️ Le burin est sur la partie rectiligne. L'ESP32 utilise l'équation standard de distance perpendiculaire à une droite ($ax + bz + c = 0$).
        2. **Dès que la facette devient plus proche** ➡️ **Bascule instantanée.** L'ESP32 sait que la frontière de l'arrondi est franchie. Il quitte l'analyse linéaire et active la formule du **vrai cercle analytique continu** (Distance Centre-Centre).
        3. **Au Point de Tangence Exact** ➡️ Les deux formules (droite et cercle) donnent la même valeur au micron près. La bascule se fait « au bol » sans aucun saut ni secousse mécanique.
        4. **Sortie d'Arc** ➡️ Dès que la droite tangente suivante redevient la plus restrictive, le calcul bascule à nouveau sur la droite.

        ## 🏎️ 4. Anticipation Dynamique de l'Arrêt (Look-Ahead Manuel)
        Contrairement à une CNC, la vitesse d'avance est dictée par les mains de l'opérateur sur les manivelles.
        1. **Calcul du Vecteur Vitesse ($\vec{V}$)** : L'ESP32 mesure l'écart de temps ($\Delta t$) entre les impulsions des règles optiques pour calculer en direct $V_z$, $V_x$ et l'angle d'approche ($\theta = \text{atan2}(V_x, V_z)$).
        2. **Calcul de la Distance d'Arrêt ($D_{\text{arrêt}}$)** : Intègre l'accélération maximale ($a_{\max}$) que le moteur pas-à-pas peut encaisser sans sauter de pas face à l'inertie du chariot :
        $$D_{\text{arrêt}} = \frac{V^2}{2 \cdot a_{\max}} + (\text{Temps\_de\_réaction} \cdot V) + \text{offset\_sécurité}$$
        3. **Déclenchement du Fusible** : Dès que la distance minimale par rapport au profil analytique devient égale ou inférieure à cette distance d'arrêt dynamique, l'ESP32 prend le contrôle pour appliquer la rampe de freinage d'urgence ou faire reculer l'axe incliné.
