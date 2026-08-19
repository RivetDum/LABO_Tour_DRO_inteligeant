# cutting_tool \ cutter.py
import json
import copy
import math

# Angles inclus théoriques de la norme ISO
ISO_ANGLES = {
    "S": 90.0, # Plaquette losange à 90° (carré)
    "C": 80.0, # Plaquette losange
    "D": 55.0, # Plaquette losange
    "E": 75.0, # Plaquette losange
    "V": 35.0, # Plaquette losange
    "T": 60.0, # Plaquette triangle
    "W": 80.0, # Plaquette trigone (3 angles à 80°)
    "R": 360.0 # Ronde
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



class CutterManager:
    def __init__(self, json_path="cutting_tool/cutter.json"):
        """
        🛠️ GESTIONNAIRE DE TOURELLE ET DE BURINS
        Assure la liaison directe avec ton fichier JSON d'atelier.
        """
        self.json_path = json_path
        self.profiles = {}       # Dictionnaire des plaquettes (cutt_profile)
        self.tools = {}          # Dictionnaire des burins (cutt_tool)
        self.active_tool_id = None
        
        # Chargement automatique au démarrage si le fichier existe
        self.load_from_json()

    def load_from_json(self):
        """Lit la bibliothèque d'outils depuis le fichier JSON."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.profiles = data.get("cutt_profile", {})
                self.tools = data.get("cutt_tool", {})
                print(f"[⚙️ CutterManager] {len(self.tools)} burins et {len(self.profiles)} formes chargés.")
                return True
        except FileNotFoundError:
            print(f"[⚠️ CutterManager] Fichier {self.json_path} introuvable. Initialisation à vide.")
            return False
        except Exception as e:
            print(f"[🚨 CutterManager] Erreur critique lors de la lecture du JSON : {e}")
            return False

    def save_to_json(self):
        """Sauvegarde les modifications (ex: mise à jour des corrections d'usure) dans le JSON."""
        try:
            data = {
                "cutt_profile": self.profiles,
                "cutt_tool": self.tools
            }
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print("[⚙️ CutterManager] Bibliothèque d'outils sauvegardée avec succès.")
            return True
        except Exception as e:
            print(f"[🚨 CutterManager] Impossible de sauvegarder dans le JSON : {e}")
            return False

    def select_tool(self, tool_id: int | str):
        """Sélectionne le burin actif sur le tour."""
        t_id = str(tool_id)
        if t_id in self.tools:
            self.active_tool_id = t_id
            print(f"[⚙️ CutterManager] Outil actif validé : N°{t_id} ({self.tools[t_id].get('nom', 'Sans nom')})")
            return True
        print(f"[⚠️ CutterManager] Erreur : L'outil N°{t_id} n'existe pas dans ton catalogue.")
        return False

    def get_active_tool_data(self):
        """Retourne l'assemblage complet (Burin + Plaquette liée) de l'outil sélectionné."""
        if not self.active_tool_id:
            return None
            
        tool = self.tools[self.active_tool_id]
        form_id = str(tool.get("form"))
        profile = self.profiles.get(form_id, {})
        
        # Extraction du rayon (soit surchargé dans le burin, soit lu depuis la plaquette)
        radius = tool.get("radius", profile.get("radius", 0))
        cadran = tool.get("cadran", profile.get("cadran", 4))
        
        return {
            "tool": tool,
            "profile": profile,
            "radius": radius,
            "cadran": cadran
        }

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
