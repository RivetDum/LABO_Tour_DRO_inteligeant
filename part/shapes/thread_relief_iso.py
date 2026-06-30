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
    - La forme se dessine automatiquement à l'instanciation via compute_geometry().
    - Les valeurs par défaut sont définies en tant que variable de classe : val_default.

    Exemple d'entités produites :
        - Ligne d'entrée
        - Arc de congé 1
        - Segment central (fond de gorge)
        - Arc de congé 2
        - Ligne de sortie
'''

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.metrics import dp
from functools import partial
import math
import copy

#from i18n import tr, Tr, TR  # La fonction de traduction importée tr>> tel que la traduction; Tr première lettre en majuscule; TR tous en majuscule
from .base_shape import BaseShape
from common_widgets import LabeledCell, InputCell, MyLabel, Separator, GroupHeader, STATUS_VALIDE,STATUS_ERREUR,STATUS_NEUTRE,STATUS_INACTIF
import config as conf
import common_draw as cd
from ui_configurator.theme_manager import draw_line as th_drl


class ThreadReliefISOShape(BaseShape):
    shape_type = ['filet_gorge', 'ISO']
    val_default = {
        'largeur': 4500, 
        'profondeur': 1500, 
        "rayon_fond": 400, 
        "angle_entrer":30 * 1000,
        "invert_dir":False,
        "ref_portee":"axis",
        "ref_appuis":"B-A"
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

        # ceci dans BaseShape: self.entities_shape = entry_b
        #pnt_raw = self.entities_shape["raw"]
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
        self.compute_geometry()
        self.update_shape_label_name(self.get_shape_label_name())

    def compute_geometry(self):
        """
        Construit les entités représentant la gorge de filetage ISO à partir des points A, B, C
        et des paramètres définis.
        
        
        
        self.entities_shape = []

        width = self.params.get("largeur")   # µm
        width = width if width is not None else self.val_default['largeur']
        depth = self.params.get("profondeur")
        depth = depth if depth is not None else self.val_default['profondeur']
        radius = self.params.get("rayon_fond")
        radius = radius if radius is not None else self.val_default['rayon_fond']
        yota_entrer_base = int(round(self.params.get("angle_entrer")))  # angle en milli-degrés
        if yota_entrer_base is None:
            yota_entrer_base = int(round(self.val_default['angle_entrer']))  # aussi en milli-degrés
        yota_entrer = math.radians(yota_entrer_base / 1000)  # conversion en radians

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

        """

        self.entities_shape = []

        #fonctions internes
        def normalize_angle(angle):
            ''' 
            Normaliser l'angle en radians entre -π et π 
                Info: L'invertion de l'angle avant et après normalisation a pour but 
                    de retourner π pour un demi-tour (au-lieu de -π sans ces invertions)

            Args:
                angle_rad (float): Angle en radians à normaliser.

            Returns:
                float: Angle normalisé dans l'intervalle ]-π, π].
            '''
            return -((-angle + math.pi) % (2 * math.pi) - math.pi)

        def get_direction(angle):
            ''' Retourne la direction cardinal correspondant à un angle donné (en radians) '''
            angle_deg = math.degrees(angle) % 360

            if 45 <= angle_deg < 135:
                return 'top'
            elif 135 <= angle_deg < 225:
                return 'left'
            elif 225 <= angle_deg < 315:
                return 'bottom'
            else:
                return 'right'

        def cotan(x):
            return 1 / math.tan(x)

        width = self.params.get("largeur")   # µm
        width = width if width is not None else self.val_default['largeur']

        depth = self.params.get("profondeur")
        depth = depth if depth is not None else self.val_default['profondeur']

        radius = self.params.get("rayon_fond")

        radius = radius if radius is not None else self.val_default['rayon_fond']

        yota_entrer_base = int(round(self.params.get("angle_entrer")))  # angle en milli-degrés
        if yota_entrer_base is None:
            yota_entrer_base = int(round(self.val_default['angle_entrer']))  # aussi en milli-degrés

        # Direction
        dir_c = self.params.get("invert_dir", False) # Inverser la direction (Gorge sur sgment B-C au-lieu de A-B)

        # Point de A-B-C
        ref_abs = self.point_b  # posission X,Y de B. Pour les rajouter au positions relative une foiss fini
        p_a_abs = self.point_c if dir_c else self.point_a   # Point direction côté fin du filet
        # pnt_b c'est 0,0
        p_c_abs = self.point_a if dir_c else self.point_c   # Point direction côté face d'appuis
        pnt_a = [0,0]
        pnt_c = [0,0]
        pnt_a[0], pnt_a[1] = p_a_abs[0] - ref_abs[0] , p_a_abs[1] - ref_abs[1]
        pnt_c[0], pnt_c[1] = p_c_abs[0] - ref_abs[0] , p_c_abs[1] - ref_abs[1]

        # Calcul des angles
        yota_entrer = math.radians(yota_entrer_base / 1000)  # conversion en radians
        alpha_ba = math.atan2(pnt_a[1], pnt_a[0])   # de B vers A
        alpha_bc = math.atan2(pnt_c[1], pnt_c[0])   # de B vers C
        dir_ba = get_direction(alpha_ba)
        dir_bc = get_direction(alpha_bc)
        
        interior = normalize_angle(alpha_ba - alpha_bc) < 0 # "creuser le côté obtus de l'angle"

        # Définition des axes cartésiens
        direction_map = {
            'top': math.pi / 2,
            'right': 0,
            'bottom': -math.pi / 2,
            'left': math.pi,
        }
        axis_ba = direction_map.get(dir_ba, 0)
        axis_bc = direction_map.get(dir_bc, 0)


        def point_rotate_to_abs(point, angle=alpha_ba, point_ref=ref_abs):
            x, y = point
            x_ref, y_ref = point_ref
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            x1 = x * cos_a - y * sin_a
            y1 = x * sin_a + y * cos_a

            return [
                x1 + x_ref,
                y1 + y_ref
            ]

        # Variables propre aux segments
        alpha_se0 = (axis_bc if self.params.get("ref_appuis", "BC") == "axis" else alpha_bc) # (choix selon paramètre fourni: self.params.get("ref_appuis", "BC")  # "axis" ou "BC" -> C'est l'axe de référance pour la sortie)
        alpha_se1 = axis_ba if self.params.get("ref_portee", "BC") == "axis" else alpha_ba # (choix selon paramètre fourni: self.params.get("ref_portee", "AB")  # "axis" ou "AB" -> C'est l'axe de référance pour le fond de gorge)
        #yota_entrer *= 1 if not interior else -1
        alpha_se2 = normalize_angle(alpha_ba +  (-yota_entrer if not interior else (yota_entrer + math.pi)))
        lse1 = width# ça longeur: lse1 = param_longueur (paramètre fourni)
        use1 = depth# ça distance perpendiculaire à B-A minimal (p1 ou p2) : use1 = param_profondeur  (paramètre fourni)
        # Info:
            #- p 0 c'est le point d'incertion originaal
            #- p 1 c'est le point fond de gorge/face d'appuis
            #- p 2 c'est le point fond de gorge/pente d'entré
            #- p 3 c'est le point de connexion pente d'entré/porté du filet
            #- seo c'est le segment reliant la façe d'appuis au fond de gorge (entre p0 et p1)
            #- se1 c'est le segment droit du fond de gorge (entre p1 et p2)
            #- se2 c'est le segment du fond de gorge à la porté di filet (entre p2 et p3)
            #- _ba sela signifie valeur relative à l'axe B-A: Pour simplifier j'ai tous ramené comme si l'axe B-A valait 0° puis à la fin je retourne denouveau avec le bon angle !
        
        ''' Calcul de se1 (relative à B-A ramené à 0 radian) '''  # Position de p3 sur l'axe X (vertical est nul, ce raccorde au segment B-A)
        if alpha_se1 == math.pi and alpha_ba < 0:
            alpha_se1 *= -1
        angle_diff = normalize_angle(alpha_se1 - alpha_ba)

        if angle_diff == 0 or angle_diff == -0:     # SE1 parallèle à B-A
            _yy_ba = 0          # Pas de compencation de profondeur
            _y_ba = 0           # Pas de décalage de profondeur (y constant)
            x_ba = lse1         # le décalage en x du segment et égale à ça longeur
        else:
            _y_ba = math.sin(angle_diff) * lse1
            x_ba = math.cos(angle_diff) * lse1
            # SE1 monte → profondeur réelle réduite côté entrée → on compense || SE1 descend ou horizontal → la profondeur est au moins celle demandée 
            _yy_ba = _y_ba if (angle_diff > 0 and interior) or (angle_diff < 0 and not interior) else 0
            #_y_ba *= 1 if (angle_diff < 0 and interior) or (angle_diff > 0 and not interior) else 0
            print(f"angle_dif: {math.degrees(angle_diff)} Angle SE1: {math.degrees(alpha_se1)}  Angle B-A: {math.degrees(alpha_ba)}")
            print(f"<<< _y_ba:{_y_ba} : _yy_ba:{_yy_ba}   || Interior:{interior}")
        # Décalage en Y de p1_ba
        p1_ba = [None, (use1) * (-1 if interior else 1) - _yy_ba]
        
        # Création du vecteur p1_ba -> p2_ba
        y_ba = _y_ba #y_ba = _y_ba if interior else _y_ba
        se1p2_ba = x_ba, y_ba
    
        ''' Calcul de se0 '''
        se0_alpha_ba = normalize_angle(alpha_se0 - alpha_ba)  # Angle relatif à B-A
        # Calcul de x_ba
        y_ba = p1_ba[1] # (déjà défini lors du calcul de sse1)
        epsilon = 1e-8
        if abs(y_ba) < epsilon or abs(se0_alpha_ba) < epsilon or abs(se0_alpha_ba - math.pi) < epsilon:
            x_ba = 0
        else:
            x_ba = cotan(se0_alpha_ba) * y_ba  # Utilisation de la cotangente pour le calcul de x_ba
        # Vérification et création du segment p1_ba
        p1_ba = x_ba, y_ba 

        # Mise à jour de p2_ba : la somme de p1_ba et se1p2_ba
        p2_ba = p1_ba[0] + se1p2_ba[0], p1_ba[1] + se1p2_ba[1]
    
        ''' Calcul de se2 (en tenant compte de 'interior')'''
        se2_alpha_ba = (alpha_se2 - alpha_ba) #* (1 if dir_c else -1)  # Angle relatif à B-A
        # Calcul du déplacement en Y et X
        y_ba = -p2_ba[1]  # La différence de p2_ba à B-A (0, 0)
        #x_ba = y_ba * math.tan(se2_alpha_ba)  # Déplacement horizontal lié à l'angle de se2
        epsilon = 1e-8
        if abs(y_ba) < epsilon or abs(se2_alpha_ba) < epsilon or abs(se2_alpha_ba - math.pi) < epsilon:
            x_ba = 0
        else:
            x_ba = cotan(se2_alpha_ba) * y_ba  # Utilisation de la cotangente pour le calcul de x_ba
        # Position finale de p3_ba
        p3_ba = x_ba + p2_ba[0], 0

        # position absolue pour les points utiles. (Rotation et positionnement absolue)
        pnt3 = point_rotate_to_abs(p3_ba)
        pnt2 = point_rotate_to_abs(p2_ba)
        pnt1 = point_rotate_to_abs(p1_ba)

        #Création de la liste brut des segments. (direction standart)
        # --> Avec ajout des congés
        entities = []   # Donné brut
        A = self.point_c if dir_c else self.point_a
        C = self.point_a if dir_c else self.point_c
        entities.append({"type":"l", "start":A, "end":pnt3, "color":th_drl["liaison"]})
        entities.append({"type":"l", "start":pnt3, "end":pnt2, "color":th_drl["detail"]})
        conge = cd.create_fillet(point_before=pnt3, point_intersect=pnt2, point_after=pnt1, radius=radius, dict_formated_auto=True)
        conge["color"] = th_drl["detail"]
        entities.append(conge)
        entities.append({"type":"l", "start":pnt2, "end":pnt1, "color":th_drl["detail"]})
        conge = cd.create_fillet(point_before=pnt2, point_intersect=pnt1, point_after=ref_abs, radius=radius, dict_formated_auto=True)
        conge["color"] = th_drl["detail"]
        entities.append(conge)
        entities.append({"type":"l", "start":pnt1, "end":ref_abs, "color":th_drl["detail"]})
        entities.append({"type":"l", "start":ref_abs, "end":C, "color":th_drl["liaison"]})
        
        # Initialisation de draw_part (pour le dessin de la pièce)
        self.draw_part = []
        firstentities = len(entities)-1
        for idx, entity in enumerate(entities):
            if idx == 0 or idx == firstentities: # ne pas inclure les lignes de liaison !
                continue
            _ent = copy.deepcopy(entity)
            _ent["color"] = th_drl["profil"]
            _ent["id_pnt"] = None

            # Mise dans l'ordre des segments, avec invertion de direction du dessin !!!
            if dir_c:
                if "end" in _ent and "start" in _ent:
                    _ent["end"], _ent["start"] = _ent["start"], _ent["end"]
                    if "cw" in _ent:
                        # Inverser le sens de rotation de l'arc
                        _ent["cw"] = not _ent["cw"]
                    if "dir" in _ent:
                        _ent["dir"] = not _ent["dir"]
                self.draw_part.insert(0, _ent)
            else:
                self.draw_part.append(_ent)

        # Mise au format pour mon dessin 
        # --> Avec invertion de l'ordre des segments si n'écécaire (voir:"dir_c") 
        # --> Format corespondant à ProfilDraw() 
        # --> Les bbox sont calculés ajoutés par: create_entities_from_raw
        self.entities_shape = cd.create_entities_from_raw(entities, dir_c, error_color=th_drl["erreur_detail"])    # donnés formatés pour dessin
        
        # Mettre à jour le dessin du détail
        self.update_draw_shape(self.entities_shape)

    def get_shape_label_name(self):
        label_txt = f"filet ISO (D-{2*self.params.get("profondeur")/1000}/{self.params.get("largeur")/1000}/R{self.params.get("rayon_fond")/1000})"
        return label_txt
    
    def shape_config_box(self):
        # Céation standardisée d'un BoxLayout pour le sous-formulaire
        layout = self.create_standard_config_box(
            orientation='vertical',     # Orientation du BoxLayout
            pilot_hint=(1, 0),      # ici largeur piloté par le box de destination et hauteur pilotée par les enfants
            fixed_size=(None, None),    # pas de largeur ou hauteur avec des valeurs fixe
            spacing=dp(5)              # Espacement entre les éléments
        )
        # Ajout des widgets

        # === Configuration centralisée des champs ===
        fields = [      # Champs pour dimentions
            {"key": "largeur", "label": f'"width":', "default": 1000, "unit_type": "unit_distance"},
            {"key": "profondeur", "label": f'"depth" :', "default": 1000, "unit_type": "unit_distance"},
            {"key": "rayon_fond", "label": f'"radius" :', "default": 1000, "unit_type": "unit_distance"},
            {"key": "angle_entrer", "label": f'"angle" :', "default": 30000, "unit_type": "unit_angle"},
        ]
        bt_fields = [      # Champs des cases_options
            {"key": "invert_dir", "label": f'Direction :', "text_up":"Normal", "text_down":"Invercé", "val_up": False, "val_down": True},
            {"key": "ref_portee", "label": f'Fond parallèle à :', "text_up":"Portée filet", "text_down":"Axe cartésien", "val_up": "B-A", "val_down": "axis"},
            {"key": "ref_appuis", "label": f'Sortie parallèle à :', "text_up":"Face d'appuis", "text_down":"Axe cartésien", "val_up": "B-C", "val_down": "axis"},
        ]
        # === Méthode de parsing et mise à jour ===
        def on_text_change(index, instance, value):
            field = fields[index]
            parsed = conf.parse_user_input(value, default_unit_type_or_id=field["unit_type"])

            if isinstance(parsed, str):
                instance.set_status(STATUS_ERREUR)
                return

            val_float, unit_id, _ = parsed
            instance.set_status(STATUS_NEUTRE)

            factor = conf.get_unit_config(unit_id).get("factor", 1.0)
            self.update_params({field["key"]: int(round(val_float * factor))})
        def make_line(index, field):
            line = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(25), spacing=dp(30))
            label = Label(text=field["label"], size_hint_x=0.5)
            val_um = self.params.get(field["key"], field["default"])
            text_val = conf.format_unit(val_um, field["unit_type"], True)
            input_r = InputCell(text=f"{text_val[0]} {text_val[1]}", size_hint_x=0.5)
            input_r.bind(text=partial(on_text_change, index))

            line.add_widget(label)
            line.add_widget(input_r)
            return line
                
        def on_toggle_btn(index, instance, value):
            # index : l'indice du bouton dans bt_fields
            txt = bt_fields[index]['text_down'] if instance.state == 'down' else bt_fields[index]['text_up']
            _key = bt_fields[index]["key"]
            _valtxt = bt_fields[index]['val_down'] if instance.state == 'down' else bt_fields[index]['val_up']
            self.update_params({_key: _valtxt})
            instance.text = txt
            
        def make_options(index, bt_fields):
            field = bt_fields[index]
            key = field["key"]

            # Cherche la valeur actuelle dans self.params (ou prend val_up par défaut)
            current_val = self.params.get(key, field["val_up"])
            is_down = current_val == field["val_down"]    # Determine si on doit mettre le bouton en "down"

            box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30), spacing=dp(30), padding=[dp(0), dp(0)])
            
            label = Label(text=field["label"], size_hint_x=0.5)

            btn = ToggleButton(allow_no_selection=True, size_hint_x=0.5 ,background_color=(0.0, 0.9, 1.0, 1))        
            btn.state = 'down' if is_down else 'normal'    # Appliquer l'état et le texte correct
            btn.text = field['text_down'] if is_down else field['text_up']
            btn.bind(state=partial(on_toggle_btn, index))    # Bind avec l’index

            box.add_widget(label)
            box.add_widget(btn)
            return box


        # === GROUPE: invercé la direction ===
        layout.add_widget(GroupHeader("choose_direction", thickness=1))
        #  Toggle buttons pour la direction de référence
        layout.add_widget(make_options(0, bt_fields))

        # === GROUPE: dimensions ===
        layout.add_widget(GroupHeader("dimensions", thickness=1))

        for idx, field in enumerate(fields):
            layout.add_widget(make_line(idx, field))


        # === GROUPE: Référence d'allignement ===
        layout.add_widget(GroupHeader("reference_axes", thickness=1))
        #  Toggle buttons pour la direction de référence
        layout.add_widget(make_options(1, bt_fields))
        layout.add_widget(make_options(2, bt_fields))



        # === GROUPE: pied de formulaire ===
        layout.add_widget(GroupHeader("validate", thickness=1))

        return layout



