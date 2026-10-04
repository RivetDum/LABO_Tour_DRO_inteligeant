# cutting_tool/ - cut_norme.py           # 🚀 LE FOURRE-TOUT NORMATIF : Angles, cercles inscrits, codes ISO

import json
import copy
import math

from kivy.uix.popup import Popup
from cutting_tool.cutting_widgets  import common_cut_tool as cut_tool
import common_draw as cdraw

'''Lettre (Pos. 1)Forme géométriqueCe que le code de taille (Pos. 5) indique
C, D, E, H, K, M, O, P, R, S, T, W
Diamants, Carrés, Triangles, Trigones, Ronds, Hexagones, Pentagones
Le Cercle Inscrit (IC) (valeur brute extrapolée)

A, B, L, V
Parallélogrammes étirés, Rectangles, Diamant très pointu (35°)
La Longueur d'Arête Réelle sans rayon
'''

# Angles inclus théoriques de la norme ISO
ISO_ANGLES = {
    "S": (90.0, "insc", "diamond"), # Plaquette losange à 90° (carré)
    "C": (80.0, "insc", "diamond"), # Plaquette losange
    "D": (55.0, "insc", "diamond"), # Plaquette losange
    "E": (75.0, "insc", "diamond"), # Plaquette losange
    "V": (35.0, "insc", "diamond"),  # Plaquette losange
    "T": (60.0, "insc", "triangle"), # Plaquette triangle
    "W": (80.0, "insc", "trigon"), # Plaquette trigone (3 angles à 80°)
    "R": (360.0,"insc", "round"),  # Ronde
    #"A": (85.0, "spec", "paral."), # parallélogramme
    #"B": (82.0, "spec", "paral."),  # parallélogramme
    "H": (120.0, "insc", "hexa")  # Plaquette hexagonale
    # ...
}

# 📊 TABLE DES CERCLES INSCRITS ISO (en microns)
# Traduction exacte de ta matrice standard pour chaque forme d'insert
ISO_IC_TABLE = {
    "S": {"03": 3970,  "04": 4760,  "05": 5560,  "06": 6350,  "07": 7940,  "09": 9525,  "12": 12700, "15": 15875, "19": 19050, "25": 25400, "31": 31750},
    "C": {"04": 4760,  "05": 5560,  "06": 6350,  "08": 7940,  "09": 9525,  "12": 12700, "16": 15875, "19": 19050, "25": 25400, "32": 31750},
    "D": {"05": 4760,  "06": 5560,  "07": 6350,  "09": 7940,  "11": 9525,  "15": 12700, "19": 15875, "23": 19050, "31": 25400, "38": 31750},
    "E": {"04": 4760,  "05": 5560,  "06": 6350,  "08": 7940,  "09": 9525,  "13": 12700, "16": 15875, "19": 19050, "26": 25400, "32": 31750},
    "V": {"06": 3970,  "08": 4760,  "09": 5560,  "11": 6350,  "13": 7940,  "16": 9525,  "22": 12700, "27": 15875, "33": 19050, "44": 25400, "54": 31750},
    "T": {"06": 3970,  "08": 4760,  "09": 5560,  "11": 6350,  "13": 7940,  "16": 9525,  "22": 12700, "27": 15875, "33": 19050, "44": 25400, "54": 31750},
    "W": {"02": 3970,  "L3": 4760,  "03": 5560,  "04": 6350,  "05": 7940,  "06": 9525,  "08": 12700, "10": 15875, "13": 19050, "17": 25400, "21": 31750},
    "R": {"06": 6350,  "07": 7940,  "09": 9525,  "12": 12700, "15": 15875, "19": 19050, "25": 25400, "31": 31750}
}

    
class IsoInserteCreator(Popup):
    def __init__():
        pass

    def generate_parametric_insert(self, shape_letter: str, size_code: str, radius_micron: int, tool_angle_deg=45.0):
        """
        📐 LE CALCULATEUR ISO PARAMÉTRIQUE
        Génère les points d'une plaquette à partir des normes ISO, indexés sur le centre du bec (0,0).
        """
        shape = shape_letter.upper()
        size = str(size_code)
        
        # Résolution du Cercle Inscrit (IC) depuis la table interne
        if shape in ISO_IC_TABLE and size in ISO_IC_TABLE[shape]:
            ic = ISO_IC_TABLE[shape][size]
        else:
            ic = 9525  # Fallback standard de sécurité (9.525mm)
            
        alpha_deg = ISO_ANGLES.get(shape, 80.0)
        alpha = math.radians(alpha_deg)

        # Calcul de la longueur d'arête L induite par la norme ISO
        size_l = ic / math.sin(alpha)

        # Positionnement du nez virtuel pour que le congé soit parfaitement tangent
        dist_sommet_centre = radius_micron / math.sin(alpha / 2.0)
        v_sommet = [dist_sommet_centre, 0.0]

        # Orientation des flancs à plat autour de la bissectrice (axe X)
        dir_arete1 = [math.cos(alpha / 2.0), math.sin(alpha / 2.0)]
        dir_arete2 = [math.cos(-alpha / 2.0), math.sin(-alpha / 2.0)]

        # Calcul des sommets du losange
        pnt_opp_1 = [v_sommet[0] - size_l * dir_arete1[0], v_sommet[1] - size_l * dir_arete1[1]]
        pnt_opp_2 = [v_sommet[0] - size_l * dir_arete2[0], v_sommet[1] - size_l * dir_arete2[1]]
        pnt_fond  = [pnt_opp_1[0] - size_l * dir_arete2[0], pnt_opp_1[1] - size_l * dir_arete2[1]]

        brut_points = [v_sommet, pnt_opp_1, pnt_fond, pnt_opp_2]

        # Application de la matrice de rotation selon l'angle du burin sur la machine
        rot_angle = math.radians(tool_angle_deg)
        cos_r, sin_r = math.cos(rot_angle), math.sin(rot_angle)

        final_points = []
        for pt in brut_points:
            rx = pt[0] * cos_r - pt[1] * sin_r
            rz = pt[0] * sin_r + pt[1] * cos_r
            
            final_points.append({
                "pos": [round(rx, 2), round(rz, 2)],
                "shape": ["standard", "Congé"],
                "shape_label": f"Congé (R={radius_micron/1000})",
                "shape_params": {"rayon_conge": radius_micron}
            })

        return final_points

#def traiter_geometrie_generique(data_forme): 
# ==>> Déplacé dans: cutting_tool/cutting_widgets/ - common_cut_tool.py


def fabriquer_geometrie_plaquette(forme_lettre, code_taille, radius):
    if forme_lettre not in ISO_ANGLES:
        return None
        
    angle, base_calcul, forme_visuelle = ISO_ANGLES[forme_lettre]
    valeur_table = ISO_IC_TABLE.get(forme_lettre, {}).get(code_taille)
    if not valeur_table:
        return None
        
    dim = valeur_table
    rad = math.radians(angle)

    # --- CAS 1 : LOSANGE (S, C, D, E, V) ---
    if forme_visuelle in ["diamond", "rhombic"] and base_calcul == "insc":
        cote = dim / math.sin(rad)
        a0 = [[0.0, 0.0],  radius]
        a1 = [[cote, 0.0],  radius]
        a3 = [[cote * math.cos(rad), dim],  radius]
        a2 = [[a3[0][0] + a1[0][0], a3[0][1]],  radius]
        
        data_forme = {"points": [a0, a1, a2, a3]}
        return cut_tool.traiter_geometrie_generique(data_forme)

    # --- CAS 2 : TRIANGLE (T) ---
    elif forme_visuelle == "triangle" and base_calcul == "insc":
        cote = math.sqrt(3) * dim
        hauteur = 1.5 * dim
        a0 = [[0.0, 0.0], radius]
        a1 = [[cote, 0.0], radius]
        a2 = [[cote / 2.0, hauteur], radius]
        
        data_forme = {"points": [a0, a1, a2]}
        return cut_tool.traiter_geometrie_generique(data_forme)

    # --- CAS 3 : RONDE (R) ---
    elif forme_visuelle == "round":
        # Pour une plaquette ronde, le "bec" est la plaquette elle-même.
        # Le centre outil (0,0) est le centre de la plaquette.
        data_forme = {"points": [[[0.0, 0.0], dim / 2.0]]}
        return cut_tool.traiter_geometrie_generique(data_forme)

    elif forme_visuelle == "trigon" or forme_visuelle == "hexag":
        # VECTEUR Normalisé de 60° , constante trigonométrique calculée une seule fois
        vect_60_x, vect_60_y = 0.5, math.sqrt(3) / 2.0        
        # Directions des 6 sommets espacés de 60° (Vecteurs unitaires fixes)
        dirs_60 = [
            (1.0, 0.0),               # 0°
            (vect_60_x, vect_60_y),   # 60°
            (-vect_60_x, vect_60_y),  # 120°
            (-1.0, 0.0),              # 180°
            (-vect_60_x, -vect_60_y), # 240°
            (vect_60_x, -vect_60_y)   # 300°
        ]
        
        # Hypoténuses exactes depuis le centre (0,0) validées par vos angles
            # C'est l'angle du triangle au point  dirA vers le centre, dirB vers le point de tangence (angle droit au point de tangence)
        angle_grand_demi = angle / 2    # en degrés
        angle_petit_demi = 90 - (angle_grand_demi - 30) # (90° - (delta trigone triangle) / 2) (/2 car delta identique de chaque côté!)
        dist_pointe = (dim / 2.0) / math.sin(math.radians(angle_grand_demi))
        dist_plat = (dim / 2.0) / math.sin(math.radians(angle_petit_demi))
        
        points_w = []
        for i, (vx, vy) in enumerate(dirs_60):
            # Alternance : Pointe active (pair) / Face de transition (impair)
            if i % 2 == 0:
                dist = dist_pointe
                r_sommet = radius
            else:
                dist = dist_plat
                if forme_visuelle == "hexag":
                    r_sommet = radius
                else:
                    r_sommet = 0
                
            # Calcul cartésien direct par multiplication vectorielle
            x = vx * dist
            y = vy * dist
            points_w.append([[x, y], r_sommet])
            
        data_forme = {"points": points_w}
        return cut_tool.traiter_geometrie_generique(data_forme)



    