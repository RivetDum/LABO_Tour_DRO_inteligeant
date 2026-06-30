# part/shapes/ thread_relief_iso.py
'''
ThreadReliefISOShape

Description :
    Représente une gorge de filetage ISO, construite entre trois points (A, B, C) et à partir de paramètres géométriques.

    Comportement :
    - shape_type = ['filet_gorge', 'ISO']
    - Utilise compute_geometry() pour générer les entités géométriques de la gorge (ligne, arcs).
    - Les entités sont accessibles via get_entities().
    - Les points de début et de fin de forme sont stockés dans self.shape_start et self.shape_end, 
      récupérables via get_start_end().
    - mirror_z est géré mais non encore utilisé.
    - La forme se dessine automatiquement à l’instanciation via compute_geometry().
    - Les valeurs par défaut sont définies en tant que variable de classe : val_default.

    Exemple d'entités produites :
        - Ligne d'entrée
        - Arc de congé 1
        - Segment central
        - Arc de congé 2
        - Ligne de sortie
'''

from .base_shape import BaseShape
import math
import copy

class ThreadReliefISOShape(BaseShape):
    shape_type = ['filet_gorge', 'ISO']
    val_default = {
        'largeur': 4500, 
        'profondeur': 1500, 
        "rayon_fond": 400, 
        "angle_entrer":30 * 1000
    }

    def __init__(self, point_a, entry_b, point_c, mirror_z=False):
        """
        Initialisation de la forme ThreadReliefISOShape.

        :param point_a: Coordonnée du point A (x, z).
        :param entry_b: [PointEntry()] compet du point à éditer
        :param point_c: Coordonnée du point C (x, z).
        :param params: Paramètres supplémentaires de la forme (largeur, profondeur, etc.).
        :param mirror_z: Option pour la symétrie selon l'axe Z (non utilisé ici).
        """

        # ceci dans BaseShape: self.entities = entry_b
        #pnt_raw = self.entities["raw"]
        # ceci dans BaseShape: self.start_entry = copy.deepcopy(entry_b)

        '''Déplacer dans BaseShape: (pour utiliser BaseShape sans forme.) ("Aucune forme")
        # Fusion des paramètres fournis avec les valeurs par défaut (contrôle de la complétude des clés de params et au cas ou remplace par les valeurs par défaut)
        merged_params = self.val_default.copy()
        merged_params.update(entry_b.get("raw", {}).get("shape_params", {}))
        entry_b["raw"]["shape_params"] = merged_params
        '''
        # Appel à l'init de la classe mère (BaseShape)
        super().__init__(point_a, entry_b, point_c, mirror_z)

        self.params = self.entry.raw["shape_params"]   # mise à jour de la variable dans BaseShape

        # Met à jour les positions des points (A, B, C)
        # à mettre dans BaseHape.__init__: self.update_pos(point_a, pnt_raw["pos"], point_c, mirror_z, recompute=False)

        # Met à jour les paramètres
        # à mettre dans BaseHape.__init__: self.update_params(pnt_raw["shape_params"])

    def update_params(self, params=None):
        """
        Met à jour les paramètres spécifiques à cette forme.
        Appelle la version de base pour faire la fusion et stocke le résultat.
        """
        self.update_params_Base(params)

        # Ici tu peux ajouter d'autres logiques spécifiques à ThreadReliefISOShape si besoin.
        # Exemple :
        # if self.params["profondeur"] > 5000:
        #     print("Attention : profondeur élevée")
        
        self.compute_geometry()

    def compute_geometry(self):
        """
        Construit les entités représentant la gorge de filetage ISO à partir des points A, B, C
        et des paramètres définis.
        """
        self.entities = []

        width = self.params.get("largeur")   # µm
        width = width if width is not None else self.val_default['largeur']
        depth = self.params.get("profondeur")
        depth = depth if depth is not None else self.val_default['profondeur']
        radius = self.params.get("rayon_fond")
        radius = radius if radius is not None else self.val_default['rayon_fond']
        γ_entrer_base = int(round(self.params.get("angle_entrer")))  # angle en milli-degrés
        if γ_entrer_base is None:
            γ_entrer_base = int(round(self.val_default['angle_entrer']))  # aussi en milli-degrés
        γ_entrer = math.radians(γ_entrer_base / 1000)  # conversion en radians

        ref_portee = self.params.get("ref_portee", "AB")  # "Z" ou "AB" -> C'est l'axe de référance pour le fond de gorge
        ref_appuis = self.params.get("ref_appuis", "BC")  # "X" ou "BC" -> C'est l'axe de référance pour la sortie
        # Direction
        invert_dir = self.params.get("invert_dir", False) # Inverser la direction (dela broche vers la contre-point)
        interne = self.params.get("interne", False)       # Inverser filetage intérieur / extérieur
        dir_draw = not invert_dir if interne else invert_dir    # Inverser l'ordre de dessin des segments (si vrai commencer depuis la face d'appui)

        p_ref_a = self.point_a if dir_draw else self.point_c    # Point direction côté fin du filet
        p_ref_c = self.point_c if dir_draw else self.point_a    # Point direction côté fin du filet

        z_ref = self.point_b[1]     # à rajouter aux valeurs pour la position absolue
        x_ref = self.point_b[0]

        def to_abs(pt):
            #return (pt[0] + x_ref, pt[1] + z_ref)
            x_dir, z_dir = pt
            if interne: x_dir *= -1
            return (x_dir + x_ref, z_dir + z_ref)
        
        def cotan(x):
            return 1 / math.tan(x)
        
        #z = 0                       #ici je définis la référence de la forme au point 0,0 (position relative)
        #x = 0
        a_z = p_ref_a[1]-self.point_b[1]   # Δ de position du point précédant (position relative du point A)
        a_x = p_ref_a[0]-self.point_b[0]
        c_z = p_ref_c[1]-self.point_b[1]   # Δ de position du point suivant (position relative du point C)
        c_x = p_ref_c[0]-self.point_b[0]
        α_ba = math.atan2(-a_x, -a_z)      # angle [en radian] du segment a-b par-rapport à l'axe Z
        α_bc = math.atan2(c_x, c_z)        # angle [en radian] du segment b-c par-rapport à l'axe Z

        α_protee = α_ba if ref_portee != "Z" else (0 if a_z <= 0 else math.pi)          # angle [en radian]
        β_appuis = α_bc if ref_appuis != "X" else math.pi * (-0.5 if c_x <= 0 else 0.5) # angle [en radian]
            #Δμαβγ

        # Étape 1
        dx1 = -(depth + width * math.tan(α_ba) - width * math.tan(α_protee))
        dz1 = -dx1 / math.tan(β_appuis)
        p1 = (dx1, dz1)
        print(f"TEST_compute_geometry: pnt1: {p1}")

        # Étape 2
        dx2 = width * math.tan(α_protee)
        dz2 = width
        p2 = (p1[0] + dx2, p1[1] + dz2)
        print(f"TEST_compute_geometry: pnt2: {p2}")

        # Étape 3
        γ_abs = α_ba + γ_entrer
        m1 = math.tan(α_ba)
        m2 = math.tan(γ_abs)

        b2 = p2[1] - m2 * p2[0]

        x3 = b2 / (m1 - m2)
        z3 = m1 * x3
        p3 = (x3, z3)
        print(f"TEST_compute_geometry: pnt3: {p3}")

        # Étape 4 ajouter les congé
        #Pour le congé sur p1:
        z1 = p1[1] + radius * cotan(β_appuis)
        x1 = p1[0] - radius * math.tan(α_protee)
        centre1 = (x1, z1)
        start1 = (x1 - radius * math.sin(β_appuis), z1 - radius * math.cos(β_appuis))
        end1 = (x1 + radius * math.sin(α_protee), z1 + radius * math.cos(α_protee))
        cw1 = False
        #Pour le congé sur p2 le centre est décaler:
        z2 = p1[1] - radius * cotan(γ_entrer)
        x2 = p2[0] - radius * math.tan(α_protee)
        centre2 = (x2, z2)
        start2 = (x2 - radius * math.sin(α_protee), z2 - radius * math.cos(α_protee))
        end2 = (x2 + radius * math.sin(γ_abs), z2 + radius * math.cos(γ_abs))
        cw2 = False

        #self.entities.append({"type": "line",  "start": to_abs(p3),  "end": to_abs(end2)})
        entity_a = {"type": "line",  "start": to_abs(p3),  "end": to_abs(end2)}

        #self.entities.append({
        entity_b = {
            "type": "arc", "center": to_abs(centre2), "radius": radius,
            "start": to_abs(end2), "end": to_abs(start2), "ccw": cw2}

        #self.entities.append({"type": "line",  "start": to_abs(start2),  "end": to_abs(end1)})
        entity_c = {"type": "line",  "start": to_abs(start2),  "end": to_abs(end1)}

        #self.entities.append({
        entity_d = {
            "type": "arc", "center": to_abs(centre1), "radius": radius,
            "start": to_abs(end1), "end": to_abs(start1), "ccw": cw1}

        #self.entities.append({"type": "line",  "start": to_abs(start1),  "end": self.point_b})
        entity_e = {"type": "line",  "start": to_abs(start1),  "end": self.point_b}

        if dir_draw:
            self.entities.append(entity_a)
            self.entities.append(entity_b)
            self.entities.append(entity_c)
            self.entities.append(entity_d)
            self.entities.append(entity_e)
            self.shape_start = to_abs(p3)
            self.shape_end = (x_ref, z_ref)
        else:
            self.entities.append(entity_e)
            self.entities.append(entity_d)
            self.entities.append(entity_c)
            self.entities.append(entity_b)
            self.entities.append(entity_a)
            self.shape_start = (x_ref, z_ref)
            self.shape_end = to_abs(p3)

        graph_entrities = copy.deepcopy(self.entities)
        graph_first_line = {"type": "line",  "start": self.point_a,  "end": self.entities[0]["start"]}
        graph_last_line  = {"type": "line",  "start": self.entities[-1]["end"],  "end": self.point_c}
        graph_entrities.insert(0, graph_first_line)
        graph_entrities.append(graph_last_line)
        self.update_draw_shape(graph_entrities)

    def get_shape_label_name(self):
        label_txt = f"filet ISO (D-{2*self.params.get("profondeur")/1000}/{self.params.get("largeur")/1000}/R{self.params.get("rayon_fond")/1000})"
        return label_txt
    







