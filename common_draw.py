# common_draw.py

from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Line, Ellipse
from kivy.properties import ListProperty, NumericProperty, BooleanProperty, ObjectProperty, OptionProperty, StringProperty
from kivy.metrics import dp
import math
from ui_configurator.theme_manager import draw_line as th_drl   # th_drl => Thème draw line



class ProfilPiece(Widget):
    """ (docstring de classe)
    Widget personnalisé pour dessiner des entités géométriques (lignes et arcs)
    à l'intérieur d'une boîte de dessin. Gère le redimensionnement semi-automatique
    et la mise à l'échelle selon la taille du widget parent (si transmise).

    Attributs :
    - entities : liste d'entités brutes à dessiner (non mises à l'échelle).
    - box_size : taille de la boîte cible (facultatif, sinon pas de mise à l'échelle).
    - scale : facteur d'échelle calculé automatiquement.
    - offset_vert / offset_y : décalage appliqué pour centrer le dessin.
    - raw_entities : liste des objets graphiques ajoutés au canvas.

    Méthodes principales :
    - update_entities() : mettre à jour les entités à dessiner.
    - update_size_entities() : mettre à jour les entités et redimensionner.
    - no_scale() : désactive l'échelle (dessin brut).
    - trigger_redraw() : force un redessin.
    - trigger_changsize() : recalcule échelle et offset, puis redessine.
    """
    _auto_update_enabled = True  # Par défaut, activé

    def __init__(self, entities=None, box_size= None, conect_line=False, mirror_vert=True, mirror_hor=False, **kwargs):
        ''' Note : hor_raw → x_kivy (horizontal) , vert_raw → y_kivy (vertical) '''
        super().__init__(**kwargs)

        # Initialiser les variables d'échelle et d'offsets
        self.scale = 1.0
        self.extra_offset = [0,0]   # Applique un décalage manuel au dessin (ex: ajouter un axe ou une légende, à gauche ou en bas) "Voir: get_relative_pos()"
        self.offset_hor = self.offset_vert = 0.0      # pour affichage normal
        self.offset_hor_mirror = self.offset_vert_mirror = 0.0   # pour affichage miroir
        self.conect_line = conect_line  # si la liste des entities contiens des lingnes de connections
        self.mirror_vert = mirror_vert  # Miroir sur l'axe Vertical
        self.mirror_hor = mirror_hor  # Miroir sur l'axe Horizontal

        # Initialisation des variable pour les màj-automatiques de taille
        self._need_resize = False
        self._need_reposition = False
        self._update_scheduled = False

        self.box_size = box_size            # Taille de référence pour l'affichage (en pixels)
        self.in_entities = entities or []   # Entités reçues (echelle brut)
        self.raw_entities = []              # Entités dessinées (mise à l'échelle)
        self.min_hor = self.min_vert = float('inf')
        self.max_hor = self.max_vert = float('-inf')
        self.pos_to_box = [0,0] # position de ce widget dans la box qui reçoit le dessin (décallage à appliquer au dessin)
        self.trigger_changsize(self.box_size)

    def update_entities(self, entities):       
        """
        Met à jour la liste des entités à dessiner
            sans modifier l'échelle,
            et force le redessin.
        """
        self.in_entities = entities
        self.trigger_redraw()
        #self.trigger_changsize(self.box_size)

    def update_size_entities(self, box_size=None, entities=None):
        if box_size:
            self.box_size = box_size
        self.trigger_changsize(self.box_size, entities)  

    def no_scale(self):
        self.trigger_changsize(box_size=None, entities=None)

    def get_relative_pos(self):
        """
        Retourne la position relative du widget par rapport à ses parents
        ayant la méthode `get_relative_pos`.
        Ajoute aussi le décalage manuel `self.extra_offset`

        Le calcul s'arrête dès qu’un parent ne possède pas cette méthode.
        Cela permet de contrôler jusqu'où remonter dans la hiérarchie.

        Retour :
            list [x, y] – La position cumulée dans la hiérarchie concernée.
        """
        #return self.pos
        x, y = self.pos
        parent = self.parent

        if parent and hasattr(parent, 'get_relative_pos') and callable(parent.get_relative_pos):
            px, py = parent.get_relative_pos()
            x += px
            y += py

        # Ajout de l’offset manuel
        x += self.extra_offset[0]
        y += self.extra_offset[1]

        return [x, y]

    def get_color_source_parent(self):
        """
        Remonte dans la hiérarchie des parents pour trouver le premier parent
        possédant un attribut 'color'. Cela permet de récupérer la couleur par défaut
        utilisée pour le dessin si elle n’est pas spécifiée.

        Retour :
            Widget ou None – Le parent possédant 'color', ou None si introuvable.

        Ex. d'utilisation:
            color_source = self.get_color_source_parent()
            default_color = getattr(color_source, "color", (1, 1, 1, 1))
        """
        parent = self.parent

        while parent:
            if hasattr(parent, "color"):
                return parent
            parent = parent.parent

        return None

    def set_drawing_offset(self, x=None, y=None):
        """
        Définit un décalage manuel (en pixels) appliqué au dessin du widget.
            Ce décalage est ajouté à la position calculée automatiquement par `get_relative_pos()`

        Utile pour déplacer visuellement le dessin (ex : ajouter un axe ou une légende).
        """        
        ox, oy = self.extra_offset
        if x is None:
            x = ox
        if y is None:
            y = oy
        self.extra_offset = [x, y]

    def trigger_redraw(self):
        self.pos_to_box = self.get_relative_pos() # Décallage à appliquer au dessin, actualiser avant chaque re-dessin
        self.canvas.clear()
        self.raw_entities = []

        # DEBUG: - Pour tester avec juste une ligne
        #self.in_entities = [{"type": "line",  "start": (0,0),  "end": (400,400)}]

        if self.in_entities:
            #source = self.get_color_source_parent()
            #default_color = getattr(source, "color", (1, 1, 1, 1))  # Couleur par défaut
            default_color = (0.4, 0.6, 0.4, 1)

            with self.canvas:
                #last_color = default_color  # On commence avec la couleur par défaut
                last_color = None  # On commence avec la couleur par défaut

                for e in self.in_entities:
                    # Récupère la couleur de l'entité si définie
                    color = e.get("color", default_color)
                    if color == "def":
                        color = default_color  # Si la couleur est "def", utilise la couleur par défaut
                    if color and color != last_color:
                        Color(*color)  # Applique la nouvelle couleur
                        last_color = color  # Met à jour la dernière couleur appliquée

                    if e['type'] == 'line':
                        s = self.to_canvas(e['start'])
                        t = self.to_canvas(e['end'])
                        ligne = Line(points=[s[0], s[1], t[0], t[1]], width=2)
                        #print(f"start:{s[0]-self.pos_to_box[0]} , {s[1]-self.pos_to_box[1]} end:{t[0]-self.pos_to_box[0]} , {t[1]-self.pos_to_box[1]}")
                    elif e['type'] == 'arc':
                        center = self.to_canvas(e['center'])
                        r = e['radius'] * self.scale
                        start = self.to_canvas(e['start'])
                        end = self.to_canvas(e['end'])
                        sa = self.angle_from_center(center, start)
                        ea = self.angle_from_center(center, end)
                        sa, ea = self.adjust_angle_for_dir_draw(sa, ea, e["cw"])
                        ligne = Line(circle=(center[0], center[1], r, sa, ea), width=2)  
                    elif e['type'] == 'cercle':
                        center = self.to_canvas(e['center'])
                        r = e['radius'] * self.scale
                        ligne = Line(circle=(center[0], center[1], r, 0, 360), width=2)

                    else:
                        print(f"[WARN] Entité de type inconnu ignorée : {e.get('type', '???')}")
                        continue
                    self.raw_entities.append(ligne)
                    
                    #Ajouter le dessin du rectangle bbox:
                    ''' Dessiner les bbox (pour DEBUGAGE)
                    # Dessiner le rectangle de la bbox pour chaque entité
                    bbox_min, bbox_max = e["bbox"]
                    bbox_start = self.to_canvas(bbox_min)
                    bbox_end = self.to_canvas(bbox_max)
                    
                    # Crée un rectangle autour de la bbox (un rectangle sans remplissage, seulement un contour)
                    bbox_rect = Line(points=[bbox_start[0], bbox_start[1], bbox_start[0], bbox_end[1], 
                                            bbox_end[0], bbox_end[1], bbox_end[0], bbox_start[1], 
                                            bbox_start[0], bbox_start[1]], width=1, close=True, color=(1, 0, 0, 0.5))
                    #self.raw_entities.append(bbox_rect)'''


    def trigger_changsize(self, box_size=None, entities=None, conect_line=None, search_min_max=True):
        if entities is not None:
            self.in_entities = entities

        self.box_size = box_size
        
        if conect_line is not None:
            self.conect_line = conect_line

        if not self.in_entities:
            self.raw_entities= []
            self.canvas.clear()
            return

        if self.box_size is None:
            self.scale = 1.0
            self.offset_hor = self.offset_vert = 0.0
        elif self.box_size is False:    # petite subtilité pour juste commencer par search_min_max()
            self.canvas.clear()
            return self.search_min_max(self.in_entities, self.conect_line)
        else:
            if search_min_max:
                if self.search_min_max(self.in_entities, self.conect_line) == [[0,0],[0,0]]:
                    return [[0,0],[0,0]]
            
            min_hor = self.min_hor
            min_vert = self.min_vert
            max_hor = self.max_hor
            max_vert = self.max_vert
            # Ajouter une marge de ~20%
            margin_hor = (max_hor - min_hor)*0.1
            margin_vert = 0 #(max_vert - min_vert)*0.2 Pour rester compatible avec l'axe. Au besoin adapter le padding de la boxe
            min_hor -= margin_hor
            max_hor += margin_hor
            min_vert -= margin_vert
            max_vert += margin_vert

            delta_hor = max_hor - min_hor
            delta_vert = max_vert - min_vert
            if delta_hor == 0 : delta_hor = 1
            if delta_vert == 0 : delta_vert = 1

            scale_z = self.box_size[0] / delta_hor
            scale_x = self.box_size[1] / delta_vert
            self.scale = min(scale_z, scale_x)

            self.offset_hor = (self.box_size[0] - delta_hor * self.scale) / 2 - min_hor * self.scale
            self.offset_vert = (self.box_size[1] - delta_vert * self.scale) / 2 - min_vert * self.scale
            self.offset_hor_mirror = (self.box_size[0] - delta_hor * self.scale) / 2 + max_hor * self.scale
            self.offset_vert_mirror = (self.box_size[1] - delta_vert * self.scale) / 2 + max_vert * self.scale
            #print(f"DEBUG_offset_hor: (sizeBox:({self.box_size[0]} : {self.box_size[1]}) - deltaX:{delta_hor * self.scale})/2 - minX:{min_hor * self.scale} = {self.offset_hor}")
        self.trigger_redraw()

    def search_min_max_OLD(self, entities, conect_line=None): 

        # 1. Calcul des min/max (dans l’unité brute)
        #min_hor = min_vert = float('inf')
        #max_hor = max_vert = float('-inf')

        if not entities:
            return [[0,0],[0,0]]

        # Séparer les entités principales et les lignes de contexte (index 0 et -1)
        if conect_line:
            core_entities = entities[1:-1] if len(entities) > 2 else entities
        else:
            core_entities = self.in_entities

        # j'initialise avec le premier point 'sart', pour les autre points, il correspond au point 'end' du précédant
        pt = core_entities[0]['start']
        min_hor = max_hor = float(pt[0])
        min_vert = max_vert = float(pt[1])

        for e in core_entities:
            #for pt in [e['start'], e['end']]:
            if e['type'] == 'arc' or e['type'] == 'cercle':
                c = e['center']
                r = e['radius']
                min_hor = min(min_hor, c[0] - r)
                max_hor = max(max_hor, c[0] + r)
                min_vert = min(min_vert, c[1] - r)
                max_vert = max(max_vert, c[1] + r)
            else:
                pt = e['end']
                min_hor = min(min_hor, pt[0])
                max_hor = max(max_hor, pt[0])
                min_vert = min(min_vert, pt[1])
                max_vert = max(max_vert, pt[1])

        
        self.min_hor = min_hor
        self.min_vert = min_vert
        self.max_hor = max_hor
        self.max_vert = max_vert

        return [[min_hor, min_vert], [max_hor, max_vert]]
    def search_min_max_FORME_PLUS_BBOX(self, entities, conect_line=None): 

        # 1. Calcul des min/max (dans l’unité brute)
        #min_hor = min_vert = float('inf')
        #max_hor = max_vert = float('-inf')

        if not entities:
            return [[0,0],[0,0]]

        # Séparer les entités principales et les lignes de contexte (index 0 et -1)
        if conect_line:
            core_entities = entities[1:-1] if len(entities) > 2 else entities
        else:
            core_entities = self.in_entities

        # j'initialise avec le premier point 'sart', pour les autre points, il correspond au point 'end' du précédant
        pt = core_entities[0]['start']
        min_hor = max_hor = float(pt[0])
        min_vert = max_vert = float(pt[1])

        for e in core_entities:
            #for pt in [e['start'], e['end']]:
            if e['type'] == 'arc' or e['type'] == 'cercle':
                c = e['center']
                r = e['radius']
                min_hor = min(min_hor, c[0] - r)
                max_hor = max(max_hor, c[0] + r)
                min_vert = min(min_vert, c[1] - r)
                max_vert = max(max_vert, c[1] + r)
            else:
                pt = e['end']
                min_hor = min(min_hor, pt[0])
                max_hor = max(max_hor, pt[0])
                min_vert = min(min_vert, pt[1])
                max_vert = max(max_vert, pt[1])

            b = e["bbox"][0]
            c = e["bbox"][1]
            min_hor = min(min_hor, b[0], c[0])
            max_hor = max(max_hor, b[0], c[0])
            min_vert = min(min_vert, b[1], c[1])
            max_vert = max(max_vert, b[1], c[1])

        
        self.min_hor = min_hor
        self.min_vert = min_vert
        self.max_hor = max_hor
        self.max_vert = max_vert

        return [[min_hor, min_vert], [max_hor, max_vert]]
    def search_min_max(self, entities, conect_line=None): 
        ''' Contrôle uniquement sur la taille des bbox'''
        # 1. Calcul des min/max (dans l’unité brute)
        min_hor = min_vert = float('inf')
        max_hor = max_vert = float('-inf')

        if not entities:
            return [[0,0],[0,0]]

        # Séparer les entités principales et les lignes de contexte (index 0 et -1)
        if conect_line:
            core_entities = entities[1:-1] if len(entities) > 2 else entities
        else:
            core_entities = self.in_entities

        # j'initialise avec le premier point 'sart', pour les autre points, il correspond au point 'end' du précédant
        #pt = core_entities[0]['start']
        #min_hor = max_hor = float(pt[0])
        #min_vert = max_vert = float(pt[1])

        for e in core_entities:
            b = e["bbox"][0]
            c = e["bbox"][1]
            min_hor = min(min_hor, b[0], c[0])
            max_hor = max(max_hor, b[0], c[0])
            min_vert = min(min_vert, b[1], c[1])
            max_vert = max(max_vert, b[1], c[1])
        
        # Garantir un delta minimum pour que l'échelle soit pas infinie
        if abs(min_hor - max_hor) < 50 and abs(min_vert - max_vert) < 50:
            max_hor += 25
            min_hor -= 25
            max_vert += 25
            min_vert -= 25



        self.min_hor = min_hor
        self.min_vert = min_vert
        self.max_hor = max_hor
        self.max_vert = max_vert

        return [[min_hor, min_vert], [max_hor, max_vert]]

    def get_min_max(self):
        fact_hor = -1 if self.mirror_hor else 1
        fact_vert = -1 if self.mirror_vert else 1
        return [[self.min_hor * fact_hor, self.min_vert * fact_vert], [self.max_hor * fact_hor, self.max_vert * fact_vert]]
    
    def get_offset(self):
        return [self.offset_hor_mirror if self.mirror_hor else self.mirror_hor, [self.offset_vert_mirror if self.mirror_vert else self.mirror_vert]]

    def to_canvas(self, pos, apply_pos_offset=True):
        """
        Convertit des coordonnées machine (vert_raw, hor_raw)
        vers des coordonnées Kivy (x_kivy, y_kivy)
        """

        hor_raw = pos[0]  # axe horizontal → x en Kivy
        vert_raw = pos[1]  # axe vertical   → y en Kivy

        x_kivy = hor_raw * self.scale * (-1 if self.mirror_vert else 1)
        y_kivy = vert_raw * self.scale * (-1 if self.mirror_hor else 1)

        hor_offset = self.offset_hor_mirror if self.mirror_vert else self.offset_hor
        vert_offset = self.offset_vert_mirror if self.mirror_hor else self.offset_vert

        if not apply_pos_offset:
            return (x_kivy + hor_offset, y_kivy + vert_offset)
        else:
            return (
                x_kivy + hor_offset + self.pos_to_box[0],  # Kivy X (horizontal)
                y_kivy + vert_offset + self.pos_to_box[1]  # Kivy Y (vertical)
            )

    def angle_from_center(self, center, pt):
        # ATTENTION: Kivy à le 0° vers le haut de l'écran, pas vers la droite comme beaucoup d'autres logiciels

        #dx = pt[0] - center[0]
        #dy = pt[1] - center[1]
        dz = pt[0] - center[0]
        dx = pt[1] - center[1]
        angle = math.degrees(math.atan2(dz, dx))
        return angle % 360

    def adjust_angle_for_dir_draw(self, θ_start, θ_end, cw=True):
        # INFO: Kivy dessine toujours dans le sens horaire
        if self.mirror_hor != self.mirror_vert:
            cw = not cw  # inverser le sens si un seul miroir actif

        if not cw:  # on inverse les angles si on veut CCW
            θ_start, θ_end = θ_end, θ_start

        if θ_end < θ_start:
            θ_end += 360

        return θ_start, θ_end

    def set_mirror_val(self, mirror_hor=None, mirror_vert=None):
        if mirror_hor is not None:
            self.mirror_vert = mirror_hor
        if mirror_vert is not None:
            self.mirror_vert = mirror_vert
        self.trigger_redraw()

    '''
    Si-dessous: Des fonctions qui diffèrent de 4 millis, les actions liés à la boxe contenant le dessin :
        - déplacements de la boxe.      -> demande de dessiner à nouveau la pièce dans le canvas
        - redimentionnement de la boxe. -> demande d'adapter l'échelle du dessin, avant de re-dessiner la pièce dans le canvas aux nouvelles dimentions
    - Pourquoi ces 4 millis ? Pour éviter une collisiton des fonctions et de surcharger le logiciel inutillement tout en gardant un affichage très réactif
    '''
    def on_size_changed(self, new_size=None):
        self.box_size = new_size
        self._need_resize = True
        self._schedule_update()
    def on_pos_changed(self):
        self._need_reposition = True
        self._schedule_update()
    def _schedule_update(self):
        ''' Lance le compte-à-rebourd, sauf si désactivé par un parent '''
        if not self._auto_update_enabled:
            return
    
        if not self._update_scheduled:
            self._update_scheduled = True
            Clock.schedule_once(self._deferred_update, 0.04)
    def _deferred_update(self, dt):
        '''Une fois le compte-à-rebourd terminé, exécute le fonction approprié. Et réinitialise pour le prochain changement'''
        _need_resize = self._need_resize
        self._need_resize = self._need_reposition = self._update_scheduled = False

        if _need_resize:
            self.trigger_changsize(self.box_size, conect_line=self.conect_line)
        else:
            self.update_entities(self.in_entities)
    def set_auto_update(self, auto_update_enabled):
        """
        Active ou désactive la mise à jour automatique de cet objet.

        Args:
            auto_update_enabled (bool): 
                - True : l'objet effectue ses mises à jour automatiquement 
                  (avec les fonctions: on_size_changed et on_pos_changed)
                - False : les mises à jour doivent être déclenchées manuellement depuis l'extérieur.
                  Dans ce cas, les appels à on_size_changed et on_pos_changed n'auront aucun effet
                    (car _schedule_update est bloqué).
                  Il faut donc utiliser directement update_entities() ou trigger_changsize().

        """
        self._auto_update_enabled = auto_update_enabled


class DetailView(Widget):
    axis_line = ObjectProperty(None)        # lien vers l'instance, indispensable
    draw_axis_line = BooleanProperty(True)  # contrôle extérieur, afficher ou non l'axe
    break_line = ObjectProperty(None)       # lien vers l'instance, indispensable
    draw_break_line = BooleanProperty(True)  # contrôle extérieur, afficher ou non la brisure
    profile = ObjectProperty(None)          # lien vers l'instance, indispensable
    boxe_size = ListProperty([dp(500), dp(400)])  # Espace disponible dans le parent

    def __init__(self, entities=None, conect_line=True, mirror_vert=True, mirror_hor=False, **kwargs):
        super().__init__(**kwargs)

        # Interne
        self._auto_update_enabled = False           # Modifiable via set_auto_update()
        self._pos_axis_line = 0
        self._pos_break_line = 0
        self._used_axis_line = True
        self._used_break_line = True
        self._axis_position = "Center"
        self._profil_size = [dp(500), dp(400)]      # Taille de dessin du profil

        self._need_update = False
        self._update_scheduled = False

        
        # Initialiser pour donner l'accès à : self.profile.get_min_max(). Ps: utiliser box_size=False pour éviter de tous calculer et dessiner avec une taille de boxe pas encore connue
        self.profile = ProfilPiece(entities=entities , box_size=False, conect_line=conect_line, mirror_vert=mirror_vert, mirror_hor=mirror_hor)
        self.profile.set_auto_update(False) # Désactiver les mise à jour automatique de cette objet, c'est DetailView qui s'en charge

        # Trouver si utiliser et positionner l'axe et la ligne de brizure, puis dimentionner et positionner le dessin du profile
        self.set_use_break_line()
        self.set_axis_position()
        self.set_profil_size()

        # Maintenant ou peut finir d'initialiser ProfilPiece() avec toutes les valeurs utiles qui nous manquaient !
        self.profile.trigger_changsize(box_size=self._profil_size, search_min_max=False)


        # Récupérer la valeur de y=0 du dessin est ajuster la position de l'axe
        if self._axis_position == "Center":
            _ , self._pos_axis_line = self.profile.to_canvas([0,0], apply_pos_offset=False)
            self._pos_break_line = self._pos_axis_line

        # dimensionner la ligne d'axe est la dessiner
        if self._used_axis_line:
            _start = [self.boxe_pos[0], self.boxe_pos[1] + self._pos_axis_line]
            _end = [self.boxe_pos[0] + self.boxe_size[0], self.boxe_pos[1] + self._pos_axis_line]
        else:
            _start = _end = [0,0]
        self.axis_line = DashedLineWidget(start=_start, end=_end)
        # dimensionner la ligne de brizure est la dessiner
        if self.used_break_line:
            _start = [self.boxe_pos[0], self.boxe_pos[1] + self._pos_break_line]
            _end = [self.boxe_pos[0] + self.boxe_size[0], self.boxe_pos[1] + self._pos_break_line]
        else:
            _start = _end = [0,0]
        self.break_line = BreakLine(start=_start, end=_end, zigzag_height=self.break_line.zigzag_height)

        self.add_widget(self.break_line)
        self.add_widget(self.axis_line)
        self.add_widget(self.profile)   # Ajouter le profil en dernier pour qu'il soit dessiné au dessus

    def set_profil_size(self):
        box_x, box_y = self.boxe_size
        #self.profil_pos = self.boxe_pos
        if self._axis_position == "Top":
            delta_line = box_y - self._pos_break_line #A Suppr.: - self.boxe_pos[1] # vue que pos_break_line teint déjà compte de +self.boxe_pos[1]
            box_y -= delta_line
            #self.profil_pos[1] += 0
            self.profile.set_drawing_offset(y=0)
        elif self._axis_position == "Buttom":
            delta_line = box_y - self._pos_break_line #A Suppr.:  - self.boxe_pos[1]
            box_y -= delta_line
            #self.profil_pos[1] += delta_line
            self.profile.set_drawing_offset(y=delta_line)
        else:
            self.profile.set_drawing_offset(y=0)
            pass
        self._profil_size = [box_x, box_y]
        
    def set_use_break_line(self):
        min_pos, max_pos = self.profile.get_min_max()   # Ici en valeur de base (microns)

        scale_x = abs(min_pos[0] - max_pos[0]) / self.boxe_size[0]

        if min_pos[1] >= 0 and max_pos[1] >= 0:
            self._axis_position = "Top"
        elif min_pos[1] <= 0 and max_pos[1] <= 0:
            self._axis_position = "Buttom"
        else:
            self._axis_position = "Center"

        if self._axis_position != "Center":
            delta_y = abs(min_pos[1] - max_pos[1])
            scale_0_y = delta_y / (self.boxe_size[1] - self.break_line.zigzag_height)
            self._used_break_line = scale_0_y > scale_x
        else:
            self._used_break_line = False

    def set_axis_position(self):
        # Utiliser la hauteur du symbole de brisure comme réf d'espacement
        spacing = self.break_line.zigzag_height

        if self._axis_position == "Top":
            self._pos_axis_line = self.boxe_size[1] - (spacing / 2) if self._used_axis_line else 0
            self._pos_break_line = self._pos_axis_line - spacing  if self._used_break_line else 0
        elif self._axis_position == "Buttom":
            self._pos_axis_line = (spacing / 2) if self._used_axis_line else 0
            self._pos_break_line = self._pos_axis_line + spacing if self._used_break_line else 0
        else:   # elif self._axis_position == "Center":
            # Attendre que le dessin retourne la hauteur pour zéro
            pass

    def get_relative_pos(self):
        """
        Retourne la position relative du widget par rapport à ses parents
        ayant la méthode `get_relative_pos`.

        Le calcul s'arrête dès qu’un parent ne possède pas cette méthode.
        Cela permet de contrôler jusqu'où remonter dans la hiérarchie.

        Retour :
            list [x, y] – La position cumulée dans la hiérarchie concernée.

        Remarque :
            Utile pour les systèmes de dessin où certains layouts intermédiaires
            doivent être ignorés dans les coordonnées globales.
        """
        x, y = self.pos
        parent = self.parent

        if parent and hasattr(parent, 'get_relative_pos') and callable(parent.get_relative_pos):
            px, py = parent.get_relative_pos()
            x += px
            y += py

        return [x, y]


    def update_pos_changed(self):
        self.axis_line.trigger_redraw()
        self.break_line.trigger_redraw()
        self.profile.trigger_redraw()

    def update_size_changed(self, new_size=None):
        self.boxe_size = new_size or self.size

        # Recalcule la position des axes et de la ligne de brisure
        self.set_use_break_line() # Fait des mises à jour selon la nouvelle taille
        self.set_axis_position()  # Recalculer  pos_axis_line et pos_break_line
        self.set_profil_size()    # Ajuste la taille profil_size, ajuste pos_axis_line et pos_break_line ainsi que le décalage manuel

        # Met à jour le dessin du profil (sans recalcul des min/max car pas nécessaire ici)
        self.profile.trigger_changsize(box_size=self._profil_size, search_min_max=False)

        # Ajuste position de l'axe si centré selon le nouveau dessin
        if self._axis_position == "Center":
            _, self._pos_axis_line = self.profile.to_canvas([0, 0], apply_pos_offset=False)
            self._pos_break_line = self._pos_axis_line

        # Mise à jour de la ligne d'axe (start et end)
        if self._used_axis_line:
            _start = [self.boxe_pos[0], self.boxe_pos[1] + self._pos_axis_line]
            _end = [self.boxe_pos[0] + self.boxe_size[0], self.boxe_pos[1] + self._pos_axis_line]
        else:
            _start = _end = [0, 0]  # Ceci supprime le dessin, sans supprimer l'objet

        if hasattr(self, 'axis_line'):
            self.axis_line.update_line(_start, _end)
        else:
            print(f"[WARN] widget axis_line inconnu")

        # Mise à jour de la ligne de brisure (start et end)
        if self.used_break_line:
            _start = [self.boxe_pos[0], self.boxe_pos[1] + self._pos_break_line]
            _end = [self.boxe_pos[0] + self.boxe_size[0], self.boxe_pos[1] + self._pos_break_line]
        else:
            _start = _end = [0, 0]  # Ceci supprime le dessin, sans supprimer l'objet

        if hasattr(self, "break_line"):
            self.break_line.update_line(_start, _end)
        else:
            print(f"[WARN] widget ligne de brisure inconnu")

    '''
    Si-dessous: Des fonctions qui diffèrent de 4 millis, les actions liés à la boxe contenant le dessin :
        - déplacements de la boxe.      -> demande de dessiner à nouveau dans le canvas
        - redimentionnement de la boxe. -> demande d'adapter l'échelle du dessin, ..., avant de re-dessiner dans le canvas aux nouvelles dimentions
    - Pourquoi ces 4 millis ? Pour éviter une collisiton des fonctions et de surcharger le logiciel inutillement tout en gardant un affichage très réactif
    '''
    def on_size_changed(self, new_size=None):
        self.boxe_size = new_size or self.size
        self._need_resize = True
        self._schedule_update()
    def on_pos_changed(self):
        self._need_reposition = True
        self._schedule_update()
    def _schedule_update(self):
        ''' Lance le compte-à-rebourd, sauf si désactivé par un parent '''
        if not self._auto_update_enabled:
            return
    
        if not self._update_scheduled:
            self._update_scheduled = True
            Clock.schedule_once(self._deferred_update, 0.04)
    def _deferred_update(self, dt):
        '''Une fois le compte-à-rebourd terminé, exécute le fonction approprié. Et réinitialise pour le prochain changement'''
        _need_resize = self._need_resize
        self._need_resize = self._need_reposition = self._update_scheduled = False

        if _need_resize:
            # TODO: Re.définir les dimentions des différentes class
            self.update_size_changed(self.boxe_size)
        else:
            self.update_pos_changed()
    def set_auto_update(self, auto_update_enabled):
        """
        Active ou désactive la mise à jour automatique de cet objet.

        Args:
            auto_update_enabled (bool): 
                - True : l'objet effectue ses mises à jour automatiquement 
                  (avec les fonctions: on_size_changed et on_pos_changed)
                - False : les mises à jour doivent être déclenchées manuellement depuis l'extérieur.
                  Dans ce cas, les appels à on_size_changed et on_pos_changed n'auront aucun effet
                    (car _schedule_update est bloqué).
                  Il faut donc utiliser directement update_pos_changed() ou update_size_changed().

        """
        self._auto_update_enabled = auto_update_enabled


class DashedLineWidget(Widget):
    ''' (docstring de classe)
    Widget Kivy permettant de dessiner une ligne en pointillés (ou motif personnalisé)
    entre deux points, avec mise à jour automatique en cas de redimensionnement.

    Attributs :
        start (list) : Coordonnées de départ de la ligne [x, y].
        end (list) : Coordonnées de fin de la ligne [x, y].
        dash_pattern (list) : Motif de la ligne, sous forme de longueurs (ex: [15, 5] pour un trait de 15px suivi d’un espace de 5px).
        dash_spacing (float) : Espacement ajouté entre chaque trait du motif.
        line_width (float) : Épaisseur de la ligne.
        line_color (list) : Couleur de la ligne (format RGBA).

    Utilisation :
        - Ajoute ce widget dans un layout.
        - Modifie dynamiquement les propriétés `start` et `end` pour adapter la ligne à la taille ou à la position d’un autre élément.
        - Le motif s’adapte automatiquement à la longueur totale.

    Remarque :
        Si la distance entre les points est insuffisante pour afficher un motif complet,
        la ligne est centrée et mise à l’échelle pour rester visible de manière cohérente.
    '''
    start = ListProperty([0, 0])
    end = ListProperty([400, 0])
    dash_pattern = ListProperty([dp(20), dp(10)])  # Long, espace, etc.
    dash_spacing = NumericProperty(dp(10))
    line_width = NumericProperty(dp(1.5))
    line_color = ListProperty([0.7, 0.7, 0.7, 1])  # Gris

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._pos_to_box = [0,0]   #initialisation de la vaviable (màj dans _redraw())

        self._redraw()

    def _redraw(self, *args):
        self._pos_to_box = self.get_relative_pos()

        self.canvas.clear()
        with self.canvas:
            Color(*self.line_color)

            x1 = self.start[0] + self._pos_to_box[0]
            y1 = self.start[1] + self._pos_to_box[1]
            x2 = self.end[0] + self._pos_to_box[0]
            y2 = self.end[1] + self._pos_to_box[1]

            dx = x2 - x1
            dy = y2 - y1
            dist = (dx**2 + dy**2) ** 0.5
            if dist == 0:
                return

            dir_x = dx / dist
            dir_y = dy / dist

            pattern = self.dash_pattern
            spacing = self.dash_spacing
            total_pattern_length = sum(pattern) + spacing * len(pattern)
            nb_float_pattern = (dist - pattern[1]) / total_pattern_length
            nbr_pattern = max(1, round(nb_float_pattern))

            if 0.8 < nb_float_pattern < 1.8:
                nbr_pattern = 1
                scale = dist / (pattern[1] + total_pattern_length)
                dist_draw = 0
            elif nb_float_pattern >= 1.8:
                scale = dist / (pattern[1] + nbr_pattern * total_pattern_length)
                dist_draw = 0
            else:
                scale = 0.9
                dist_draw = (dist - total_pattern_length - pattern[1]) / 2 * scale

            for _j in range(nbr_pattern):
                for i in range(0, len(pattern), 2):
                    dash_len = pattern[i]
                    x_start = x1 + dist_draw * dir_x
                    y_start = y1 + dist_draw * dir_y
                    x_end = x1 + (dist_draw + dash_len * scale) * dir_x
                    y_end = y1 + (dist_draw + dash_len * scale) * dir_y
                    Line(points=[x_start, y_start, x_end, y_end], width=self.line_width)
                    dist_draw += (dash_len + spacing) * scale
                # Rattrapage de la dérive cumulative (Pas d'effet sur les dessins à un seul pattern)
                if _j + 1 < nbr_pattern:
                    dist_draw = (_j + 1) * total_pattern_length * scale 

            # Dernier tiret (premier de la liste: dash_pattern[])
            x_start = x1 + dist_draw * dir_x
            y_start = y1 + dist_draw * dir_y
            x_end = x1 + (dist_draw + pattern[1]) * dir_x
            y_end = y1 + (dist_draw + pattern[1]) * dir_y
            Line(points=[x_start, y_start, x_end, y_end], width=self.line_width)

    def trigger_redraw(self):
        '''Force explicitement un redessin de ce widget'''
        self._redraw()
  
    def get_relative_pos(self):
        '''
        Calcule la position absolue relative d'un widget en sommant sa propre position
        avec celle de ses parents possédant la méthode `get_relative_pos`.

        Cette méthode permet d'obtenir la position du widget par rapport à un ancêtre
        spécifique dans la hiérarchie des widgets, en cumulant les positions uniquement
        des widgets qui implémentent cette méthode.

        Retour:
            list: Une liste [x, y] représentant la position relative cumulée du widget.
        
        Remarques:
            - Si le parent n'a pas de méthode `get_relative_pos`, la sommation s'arrête.
            - Utile pour gérer précisément les positions dans des hiérarchies complexes
            où seuls certains parents doivent être pris en compte.
        '''
        x, y = self.pos
        parent = self.parent

        if parent and hasattr(parent, 'get_relative_pos') and callable(parent.get_relative_pos):
            px, py = parent.get_relative_pos()
            x += px
            y += py

        return [x, y]    


class BreakLine(Widget):
    '''
    Widget pour dessiner une ligne de brisure (utilisée en dessin technique
    pour représenter une coupure entre deux parties d’un objet allongé).

    Attributs :
        start (list) : Coordonnées de départ de la ligne [x, y].
        end (list) : Coordonnées de fin de la ligne [x, y].
        zigzag_height : Hauteur du symblol
        joint_length : distance des lignes au extrémitées
        max_segment : Distance maxi entre deux symboles
        line_width (float) : Épaisseur de la ligne.
        line_color (list) : Couleur de la ligne (format RGBA).


    Cette ligne est constituée :
        - d’un trait de départ,
        - d’un ou plusieurs motifs de type zigzag (brisure),
        - d’un ou plusieurs traits intérmédiaires,
        - d’un motif en forme de zigzag (ou "brisure"),
        - d’un trait de fin.

    Les paramètres permettent d’ajuster la hauteur des brisures,
    la longueur des segments, et la densité du motif en fonction
    de la distance totale à couvrir.
    '''

    start = ListProperty([0, 0])
    end = ListProperty([400, 0])
    line_color = ListProperty([0.85, 0.85, 0.85, 1]) # Gris plus claire
    line_width = NumericProperty(dp(1))
    zigzag_height = NumericProperty(dp(20))
    joint_length = NumericProperty(dp(40))
    max_segment = NumericProperty(dp(100))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._pos_to_box = ListProperty([0,0])   #initialisation de la vaviable 
        self._redraw()

    def _redraw(self, *args):
        self._pos_to_box = self.get_relative_pos()

        self.canvas.clear()
        with self.canvas:
            Color(*self.line_color)

            x1 = self.start[0] + self._pos_to_box[0]
            y1 = self.start[1] + self._pos_to_box[1]
            x2 = self.end[0] + self._pos_to_box[0]
            y2 = self.end[1] + self._pos_to_box[1]

            dx = x2 - x1
            dy = y2 - y1
            dist = math.hypot(dx, dy)
            if dist == 0:
                return

            dir_x = dx / dist
            dir_y = dy / dist

            h = self.zigzag_height / 2
            zigzag_len = self.zigzag_height * 2
            dist_lines_min = dist - 2 * zigzag_len

            offset_x = offset_y = 0 # centering_offset X Y

            if dist_lines_min < 4 * self.joint_length:
                if dist_lines_min < zigzag_len * 4:     # Ici comme dans DashedLineWidget: Ajouter un décalage pour centrer la ligne
                    joint = zigzag_len
                    inter = 2 * zigzag_len
                    centering_offset = ((joint + zigzag_len) * 2 + inter) - dist
                    offset_x, offset_y = centering_offset * dir_x, centering_offset * dir_y
                else:
                    joint = dist_lines_min / 4
                    inter = dist_lines_min / 2
                nbr_inter = 1
            else:
                joint = self.joint_length
                nbr_inter = max(1, round((dist - 2 * joint - zigzag_len) / (self.max_segment + zigzag_len)))
                inter = (dist - 2 * joint - zigzag_len * (nbr_inter + 1)) / nbr_inter

            last_x = x1 - offset_x
            last_y = y1 - offset_y
            x_end = x1 + joint * dir_x
            y_end = y1 + joint * dir_y
            Line(points=[last_x, last_y, x_end, y_end], width=self.line_width)

            def add_zigzag(x, y):
                zz = []
                zz.append((x + h * dir_x, y + h * dir_y))
                zz.append((zz[-1][0] - 2 * h * dir_x, zz[-1][1] - 2 * h * dir_y))
                zz.append((zz[-1][0] + h * dir_x, zz[-1][1] + h * dir_y))
                return zz

            last_x, last_y = x_end, y_end

            for px, py in add_zigzag(last_x, last_y):
                Line(points=[last_x, last_y, px, py], width=self.line_width)
                last_x, last_y = px, py

            for _ in range(nbr_inter):
                x_end = last_x + inter * dir_x
                y_end = last_y + inter * dir_y
                Line(points=[last_x, last_y, x_end, y_end], width=self.line_width)
                last_x, last_y = x_end, y_end

                for px, py in add_zigzag(last_x, last_y):
                    Line(points=[last_x, last_y, px, py], width=self.line_width)
                    last_x, last_y = px, py

            Line(points=[last_x, last_y, x2 + offset_x, y2 + offset_y], width=self.line_width)

    def trigger_redraw(self):
        '''Force explicitement un redessin de ce widget'''
        self._redraw()

    def update_line(self, start=None, end=None):
        if start is not None:
            self.start = start
        if end is not None:
            self.end = end

        self._redraw()

    def update_style(self, zigzag_height=None, joint_length=None, max_segment=None, 
                    line_width=None, line_color=None):
        if zigzag_height is not None:
            self.zigzag_height = zigzag_height
        if joint_length is not None:
            self.joint_length = joint_length
        if max_segment is not None:
            self.max_segment = max_segment
        if line_width is not None:
            self.line_width = line_width
        if line_color is not None:
            self.line_color = line_color

        self._redraw()

    def get_relative_pos(self):
        '''
        Calcule la position absolue relative d'un widget en sommant sa propre position
        avec celle de ses parents possédant la méthode `get_relative_pos`.

        Cette méthode permet d'obtenir la position du widget par rapport à un ancêtre
        spécifique dans la hiérarchie des widgets, en cumulant les positions uniquement
        des widgets qui implémentent cette méthode.

        Retour:
            list: Une liste [x, y] représentant la position relative cumulée du widget.
        
        Remarques:
            - Si le parent n'a pas de méthode `get_relative_pos`, la sommation s'arrête.
            - Utile pour gérer précisément les positions dans des hiérarchies complexes
            où seuls certains parents doivent être pris en compte.
        '''
        x, y = self.pos
        parent = self.parent

        if parent and hasattr(parent, 'get_relative_pos') and callable(parent.get_relative_pos):
            px, py = parent.get_relative_pos()
            x += px
            y += py

        return [x, y]


class LabelDashedLine(BoxLayout):
    """
    Widget combinant un label et une ligne en pointillés,
    avec positionnement configurable du label (gauche ou droite).
    """
    text = StringProperty("Titre")
    label_first = BooleanProperty(True)  # Si True : Label à gauche, sinon à droite
    color = ListProperty([0.7, 0.7, 0.7, 1])
    thickness = NumericProperty(dp(1.5))
    dash_pattern = ListProperty([dp(10), dp(5)])
    dash_spacing = NumericProperty(dp(5))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(30)
        self.spacing = dp(5)

        self.label = Label(
            text=self.text,
            size_hint_x=None,
            halign='left',
            valign='middle',
            markup=True,
            color=self.color,
        )
        self.label.bind(texture_size=self._resize_label)

        self.line = DashedLineWidget(
            size_hint=(1, None),
            height=self.thickness,
            dash_pattern=self.dash_pattern,
            dash_spacing=self.dash_spacing,
            line_width=self.thickness,
            line_color=self.color,
        )

        self.update_widgets()

    def _resize_label(self, instance, value):
        instance.width = value[0] + dp(10)

    def on_text(self, *args):
        self.label.text = self.text

    def on_label_first(self, *args):
        self.update_widgets()

    def update_widgets(self):
        self.clear_widgets()
        self.line.start = [0, 0]
        self.line.end = [400, 0]  # Valeur temporaire, le redessin s’ajustera
        if self.label_first:
            self.add_widget(self.label)
            self.add_widget(self.line)
        else:
            self.add_widget(self.line)
            self.add_widget(self.label)

    def on_size(self, *args):
        # Met à jour la fin de ligne automatiquement
        self.line.end = [self.line.width, 0]
        self.line.trigger_redraw()

    def on_pos(self, *args):
        self.line.trigger_redraw()



# === OUTILS GÉOMÉTRIQUES COMMUNS ===

# Fonctions Trigonométrique
def normalize_angle(angle):
    ''' 
    Normalise l'angle en radians dans l'intervalle ]-π, π].

    Info : L'inversion de l'angle avant et après normalisation permet de retourner π pour un demi-tour
           (au lieu de -π sans ces inversions).

    Args:
        angle (float): Angle en radians à normaliser.

    Returns:
        float: Angle normalisé dans l'intervalle ]-π, π].
    '''
    return -((-angle + math.pi) % (2 * math.pi) - math.pi)

def get_direction(angle):
    ''' Retourne la direction cardinal correspondant à un angle donné (en radians) '''
    angle_deg = math.degrees(angle)
    if 45 <= angle_deg <= 135:
        return 'top'
    elif -135 <= angle_deg <= -45:
        return 'bottom'
    elif 135 <= angle_deg <= 225:
        return 'left'
    else:
        return 'right'

def compute_angle_rad(v1, v2):
    """
    Calcule l'angle en radians entre deux vecteurs 2D (v1 -> v2), 
    avec le signe déterminé par le produit vectoriel (sens trigonométrique).
    """
    if not v1 or not v2:
        return 0

    # Produit scalaire
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    # Produit vectoriel (z-component)
    cross = v1[0]*v2[1] - v1[1]*v2[0]

    angle = math.atan2(cross, dot)  # renvoie un angle signé [-π, π]
    return angle

def cotan(x):
    ''' retourne la cotangente de l'angle'''
    return 1 / math.tan(x)

def is_clockwise(dir_in, dir_out):
    """
    Détermine si la rotation de dir_in vers dir_out est dans le sens horaire.

    Utilise le produit vectoriel pour savoir si on tourne à gauche ou à droite.
    - Si le résultat est positif : rotation horaire (CW)
    - Si négatif : anti-horaire (CCW)

    Args:
        dir_in (tuple | list): Vecteur d'entrée (ex : B → A)
        dir_out (tuple | list): Vecteur de sortie (ex : B → C)

    Returns:
        bool: True si le sens est horaire (CW), False sinon (CCW)
    """
    cross = dir_in[0] * dir_out[1] - dir_in[1] * dir_out[0]
    return cross > 0

# Fonctions pour vecteur
def normalize_vector(point_dest, origine=(0,0)):
    '''
    Normalisation d'un point_dest (x, y) dans la direction de l'origine à la destination donnée. 
    Renvoie un point_dest unitaire de longueur 1 dans la même direction.
        origine -> point de départ du point_dest (souvent l'origine du système de coordonnées)
        point_dest -> point d'arrivée du point_dest (la direction du segment à normaliser)

    Args: 
        point_dest (tuple | list): Le point de destination du vecteur sous forme (x, y).
        origine (tuple | list): Le point de départ du vecteur sous forme (x, y), défaut (0, 0).

    Returns:
        tuple: Le vecteur normalisé sous forme (x, y) de longueur 1, ou
        None si la longueur du vecteur est égale à zéro (vecteur nul).
    '''
    v = (point_dest[0] - origine[0] , point_dest[1] - origine[1])
    length = math.hypot(v[0], v[1])
    if length == 0:
        return None
    return (v[0] / length, v[1] / length)

def dot_scalaire_vector(v1, v2):
    """
    Produit scalaire entre deux vecteurs 2D supposés normalisés.
    Si ce n'est pas le cas, ils sont normalisés automatiquement.
    """
    nv1 = normalize_vector(v1)
    nv2 = normalize_vector(v2)
    return nv1[0]*nv2[0] + nv1[1]*nv2[1]

def bissectrice_normalised(dir_1, dir_2, point_start=[0, 0], normalised_dir=False):
    """
    Calcule la bissectrice normalisée de deux vecteurs définis par dir_1 et dir_2, 
    en prenant en compte l'angle entre eux, et renvoie 
    la direction de la bissectrice ou un message d'erreur.
    
    Args:
        dir_1: point du segment 1 (x, y)
        dir_2: point du segment 2 (x, y)
        point_start: point de départ pour la direction des segments (x, y)
        normalised_dir: Si True, considère que dir_1 et dir_2 sont déjà normalisés

    Returns: 
        tuple (x, y) : direction de la bissectrice normalisée
        ou str : message d'erreur :
            "Les segments sont opposés"
            "Les segments sont colinéaires"
            "Segment trop court"
    """
    # Épsilons pour éviter des bissectrices à direction incertaine : Correspondent au sinus de l’angle minimum autorisé.
    epsilon = 0.002   # ≈ 180° ± 0.1°
    epsilon_b = 0.002 # ≈   0° ± 0.1°
    #epsilon_b = 0.05  # ~   0° +/- 3°

    # Calcul des vecteurs BA et BC
    v_ba = (dir_1[0] - point_start[0], dir_1[1] - point_start[1])
    v_bc = (dir_2[0] - point_start[0], dir_2[1] - point_start[1])

    # Normalisation si nécessaire
    if not normalised_dir:
        n_ba = normalize_vector(v_ba)
        n_bc = normalize_vector(v_bc)
        if n_ba is None or n_bc is None:
            return "Segment trop court"
    else:
        n_ba = v_ba
        n_bc = v_bc

    # Vérification : segments opposés ou colinéaires
    if abs(n_ba[0] + n_bc[0]) < epsilon and abs(n_ba[1] + n_bc[1]) < epsilon:
        return "Les segments sont opposés"
    elif abs(n_ba[0] - n_bc[0]) < epsilon_b and abs(n_ba[1] - n_bc[1]) < epsilon_b:
        return "Les segments sont colinéaires"

    # Calcul de la bissectrice
    bisect = normalize_vector((n_ba[0] + n_bc[0], n_ba[1] + n_bc[1]))
    return bisect if bisect is not None else "Segment trop court"

def intersection_of_lines(pnt_in, dir_ac, pnt_base, dir_out):
    """
    Calcule l'intersection entre deux droites paramétriques :
      - Droite 1 : partant de `pnt_in` dans la direction `dir_ac`
      - Droite 2 : partant de `pnt_base` dans la direction `dir_out`

    Paramètres :
        pnt_in   (list | tuple): point de départ de la première droite
        dir_ac   (list | tuple): direction de la première droite (ex: aa → cc)
        pnt_base (list | tuple): point de départ de la seconde droite (ex: B)
        dir_out  (list | tuple): direction de la seconde droite (ex: B → C)

    Retourne :
        list: coordonnées [x, y] du point d'intersection
        None: si les droites sont parallèles (pas d'intersection)
    """

    # Déterminant (produit croisé)
    det = -dir_ac[0] * dir_out[1] + dir_ac[1] * dir_out[0]

    if abs(det) < 1e-10:
        return None  # Droites parallèles → pas d'intersection

    # Résolution manuelle du système
    dx = pnt_in[0] - pnt_base[0]
    dy = pnt_in[1] - pnt_base[1]
    print(f" point_base:{pnt_base} , point_in:{pnt_in}")

    t = (dx * dir_out[1] - dy * dir_out[0]) / det

    # Intersection = pnt_base + t * dir_ac
    #return [pnt_base[0] + t * dir_ac[0], pnt_base[1] + t * dir_ac[1]]
    return [pnt_in[0] + t * dir_ac[0], pnt_in[1] + t * dir_ac[1]]


# Création de forme
def create_fillet(point_before, point_intersect, point_after, radius, list_formated_auto=False, dict_formated_auto=False):
    """
    Crée un congé (arc de cercle) entre les segments point_before-point_intersect et point_intersect-point_after.

    Args:
        point_before (tuple): Point (x, y) avant le point d'intersection.
        point_intersect (tuple): Point (x, y) d'intersection entre les deux segments.
        point_after (tuple): Point (x, y) après le point d'intersection.
        radius (float): Rayon du congé.
        list_formated_auto (bool): Si True, retourne une liste formatée pour être directement envoyée à `create_entities_from_raw()`.
                                   Si False, retourne un dictionnaire avec les informations de l'arc (type, centre, rayon, points de tangence, direction).

    Returns: (list_formated_auto == False)
        dict: Dictionnaire représentant l'arc de congé avec les clés:
              - 'type': 'arc'
              - 'center': centre du cercle
              - 'radius': rayon
              - 'start': point de départ de l'arc
              - 'end': point de fin de l'arc
              - 'cw': booléen indiquant le sens de l'arc (True = horaire, False = anti-horaire)

    Returns: (list_formated_auto == True)
        list: Liste pour représenter l'arc dans un format adapté à `create_entities_from_raw()`:
              [
                  "a",   : Type de segment (arc)
                  start, : Point de début du segment
                  end,   : Point de fin du segment
                  center, : Point du centre de l'arc
                  radius,  : Rayon
                  dir.    : Direction (True -> horaire, False -> anti-horaire)
              ]
    Version: Optimisée sans utilisation de trigonomètrie
    """
    # espillons pour éviter de faire des congés impossibles: (Valeur adaptable selon l'utilisation)
    #espilon = 0.002 # ce qui représent un angle d'environ 180° +/- 0.1°
    #espilon_b = 0.05 # ce qui représent un angle d'environ  0° +/- 3°
    

    # Produit vectoriel pour savoir si on tourne à gauche ou à droite (horaire/anti-horaire)
    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]     

    def error_return(B, list_formated_auto, not_opposé=True):
        if list_formated_auto:
            #ex arc :["a" , start , end , centre , rayon , dir.]
            return ["a",B,B,B,0,not_opposé]
        
        return {
            "type": "arc",
            "center": B,
            "radius": 0,
            "start": B,
            "end": B,
            "cw": not_opposé}  # Sens arbitraire ici
        
    # Vecteurs des segments normalisé
    n_ba = normalize_vector(point_before, point_intersect)                     # B->A normalisé
    n_bc = normalize_vector(point_after, point_intersect)                      # B->C normalisé
    if n_ba is None or n_bc is None:
        return error_return(point_intersect, list_formated_auto)
    n_b_ce = bissectrice_normalised(n_ba, n_bc, normalised_dir=True)    # B->centre normalisé (bissectrice)
    if isinstance(n_b_ce, str):
        notoppose= False if n_b_ce != "Les segments sont opposés" else True
        return error_return(point_intersect, list_formated_auto, not_opposé=notoppose)

    # Déterminer le sens de l'arc (horaire ou anti-horaire)
    cw = cross(n_ba, n_bc) > 0  # Sens horaire si cw=True, sinon anti-horaire
       
    # Vecteurs perpendiculaires aux segments (pour les tangentes)
    if cw:
        # Horaire (cw) -> correspond à la direction de dessin de l'arc
        n_ce_a = [-n_ba[1], n_ba[0]]  # Perpendiculaire à B-A : de Ce -> B-A
        v_ce_c = [n_bc[1] * radius, -n_bc[0] * radius]  # Perpendiculaire à B-C : de Ce -> B-C
    else:
        # Anti-horaire (ccw)
        n_ce_a = [n_ba[1], -n_ba[0]]  # Perpendiculaire à B-A : de Ce -> B-A
        v_ce_c = [-n_bc[1] * radius, n_bc[0] * radius]  # Perpendiculaire à B-C : de Ce -> B-C
    v_ce_a = [n_ce_a[0] * radius, n_ce_a[1] * radius]

    # Produit scalaire pour déterminer la projection ("Rapport diagonale/largeur du rectangle")
    dot_proj = abs(n_b_ce[0]*n_ce_a[0] + n_b_ce[1]*n_ce_a[1])
    # définir la longeur de la diagonal
    d = radius / dot_proj

    # Centre du congé "Ce position"
    Ce = (point_intersect[0] + n_b_ce[0]*d, point_intersect[1] + n_b_ce[1]*d) #Ce = (B[0] + n_b_ce[0]*d, B[1] + n_b_ce[1]*d)

    # Calcul des points de tangence (start et end)
    start = [Ce[0] - v_ce_a[0], Ce[1] - v_ce_a[1]]
    end = [Ce[0] - v_ce_c[0], Ce[1] - v_ce_c[1]]

    #print(f"DEBUG_create_fillet: point_before:{point_before} point_intersect:{point_intersect} point_after:{point_after}")
    #print(f"DEBUG_create_fillet: Tangence: start:{start}   end:{end}  || centre:{center}  rayon:{radius}")
    
    # round_point
    def rpt(p, digits=3):
        return [round(p[0], digits), round(p[1], digits)]
    
    if list_formated_auto:
        return ["a", rpt(start), rpt(end), rpt(Ce), radius, cw]
    
    if dict_formated_auto:
        return {
            "type": "a",
            "start": rpt(start),
            "end": rpt(end),
            "center": rpt(Ce),
            "radius": radius,
            "dir": cw  # ou 'cw', mais tu as choisi 'dir'
        }

    return {
        "type": "arc",
        "center": rpt(Ce),
        "radius": radius,
        "start": rpt(start),
        "end": rpt(end),
        "cw": cw}

# Mise en forme des segments pour ProfilPièce()
def create_entities_for_proofil(raw_list, reverse=False, default_color=None, error_color=None, id_pnt=None):
    """
    Spécialiste DRO : Uniformise le profil complet avec une couleur par défaut (ex: vert ou rouge foncé)
    et une couleur d'erreur (ex: rouge vif), tout en conservant 'origin_color' intact pour les fonctions
    inverses de reconstruction de listes de points.

    Args:
        raw_list (list): Liste de dict des définitions brutes.
        reverse (bool): Si True, inverse l'ordre et le sens des entités.
        default_color: Couleur unifiée à utiliser si le segment est valide.
        error_color: Couleur à utiliser en cas d'erreur détectée (produit scalaire ou flag).
        id_pnt: Identifiant par défaut à insérer.

    Returns:
        list: Liste d'entités prêtes à dessiner uniformément.
    """
    entities = []
    raw = None
    error = False
    
    # Sécurisation des couleurs au format RGBA Kivy
    error_color = normalize_color(error_color or (1, 0, 0, 1))         # Rouge vif par défaut
    default_color = normalize_color(default_color or (0, 1, 0.5, 1))   # Vert fluo par défaut
    ERROR_MARKER = "#error"

    # Calcul du point de départ selon le sens de parcours
    last_end = None
    if not reverse:
        for _raw in raw_list:
            if "start" in _raw:
                last_end = _raw["start"]
                break
    else:
        for idx in range(len(raw_list)-1, -1, -1):
            _raw = raw_list[idx]
            if "end" in _raw:
                last_end = _raw["end"]
                break

    def compute_raw(idx_raw):
        nonlocal raw, last_end, error, error_color, default_color, id_pnt
        ent_type = raw["type"]

        # Extraction de la couleur d'origine pour sécuriser la fonction inverse
        origin_color = raw.get("color", None)
        ident = raw.get("id_pnt", id_pnt)

        # Gestion des flags d'erreurs
        if "error" in raw and raw["error"]:
            error = True
            color = ERROR_MARKER

        # Détermination de la couleur uniforme d'affichage
        if error or origin_color == ERROR_MARKER:
            error = False if origin_color != ERROR_MARKER else True
            color = error_color
        else:
            color = default_color

        # --- Création des entités géométriques ---
        if ent_type == "l":  # Droite de connexion dépendante
            ref_point = None    
            if not reverse:
                start, end = raw["start"], raw["end"]
                for _raw in raw_list[idx_raw + 1:]:
                    if "start" in _raw:
                        ref_point = _raw["start"]
                        break
                next_start = ref_point or end
            else:
                start, end = raw["end"], raw["start"]
                for idx in range(idx_raw - 1, -1, -1):
                    _raw = raw_list[idx]
                    if "end" in _raw:
                        ref_point = _raw["end"]
                        break
                next_start = ref_point or end

            if next_start is not None:
                dx1, dy1 = end[0] - start[0], end[1] - start[1]
                dx2, dy2 = next_start[0] - last_end[0], next_start[1] - last_end[1]
                
                # Produit scalaire de sécurité pour détecter les inversions
                dot_product = dx1 * dx2 + dy1 * dy2
                if dot_product < 0:
                    color = error_color
                    error = True
                    if entities:
                        entities[-1]["color"] = error_color

                # AJOUT : On passe bien 'color' pour la DRO et 'origin_color' pour la mémoire inverse
                entities.append(creat_entry_line(last_end, next_start, color, origin_color, ident))

        elif ent_type == "d":  # Droite autonome
            start, end = (raw["end"], raw["start"]) if reverse else (raw["start"], raw["end"])
            if start != end:
                entities.append(creat_entry_line(start, end, color, origin_color, ident))

        elif ent_type == "a":  # Arc de cercle
            start, end = (raw["end"], raw["start"]) if reverse else (raw["start"], raw["end"])
            center, radius, cw = raw["center"], raw["radius"], raw["dir"] if not reverse else not raw["dir"]
            if radius != 0:
                entities.append(creat_entry_arc(start, end, center, radius, cw, color, origin_color, ident))
            else:
                end = last_end  # Arc fictif
                if not cw:
                    error = True

        elif ent_type == "c":  # Cercle complet
            center, radius = raw["center"], raw["radius"]
            end = last_end  # Ne modifie pas last_end
            if radius != 0:
                entities.append(creat_entry_circle(center, radius, color, origin_color, ident))

        else:
            print(f"[WARN] Type inconnu dans la DRO : {ent_type}")
            end = last_end

        return end

    # Parcours principal de la liste brute
    len_list = len(raw_list)
    for idx in range(len_list):
        index = idx if not reverse else (len_list - 1 - idx)
        raw = raw_list[index]
        last_end = compute_raw(index)

    return entities
def create_entities_from_raw(raw_list, reverse=False, error_color=None, id_pnt=None):
    """ create_entities_from_raw(raw_list, reverse=False)
    Crée une liste d'entités formatées (ligne, arc, cercle) à partir d'une liste brute,
    avec gestion du sens de parcours, vérification de raccordement, et détection d'inversion de direction.

    Args:
        raw_list (list): Liste de dict des définitions brutes (type, points, etc.).
        (la ligne s'adapte aux points des segments: précédent et suivant; la droite à son start et end fixe)
            ex ligne : {"type":"l", "start":[0,0], "end":[0,0], "color":(0.5,0.5,0.5,1), "id_pnt":None} 
            ex droite : {"type":"d", "start":[0,0], "end":[0,0], "color":(0.5,0.5,0.5,1), "id_pnt":None} 
            ex arc : {"type":"a", "start":[0,0], "end":[0,0], "center":[0,0], "radius":0, "dir":True}
            ex cercle: {"type":"c", "center":[0,0], "radius":0, "color":#rrggbb, "id_pnt":10}
            args:
                type   (str):   une lettre désignant le type de segment
                start  ([float,float]): position X Y du point de départ (début du trait)
                end    ([float,float]): position X Y du point d'arrivé  (fin du trait)
                center ([float,float]): position X Y du centre pour segment arrondi
                radius  (float): dimention du rayon
                dir    (bool):  direction de dessin :vrai sens horaire ; faux sens anti-horaire
                color: "Optionnel" couleur format (R,G,B,A) ou "#exa"
                id_pnt: "Optionnel" identifiant du point d'incertion
        reverse (bool): Si True, inverse l'ordre et le sens des entités.
        error_color: Couleur à utiliser en cas d'erreur détectée
        id_pnt :    Identifiant à incérer dans le point

    Returns:
        list: Liste d'entités prêtes à dessiner.
    """
    entities = []
    raw = None
    error = False
    error_color = normalize_color(error_color or th_drl["erreur_profil"])   # Couleur (RGBA) en cas d'erreur détecté
    # Flag pour signaler une erreur dans le premier trait !
    ERROR_MARKER = "#error" # ATTENTION, laisser le "#" pour que l'élément soit concidérer comme "une couleur" (notation comme couleur exadécimal "#RRGGBBAA"!)

    # Point de départ : dépend du sens et du type de la dernière entité
    last_end = None
    if not reverse:
        for _raw in raw_list:
            if "start" in _raw:
                last_end = _raw["start"]
                break
    else:
        for idx in range(len(raw_list)-1, -1, -1):
            _raw = raw_list[idx]
            if "end" in _raw:
                last_end = _raw["end"]
                break

    def compute_raw(idx_raw):
        nonlocal raw, last_end, error, error_color, id_pnt
        ent_type = raw["type"]

        # Gestion de la couleur (si présente à la fin)
        color = raw.get("color", "def")
        origin_color = raw.get("color", None)
        ident = raw.get("id_pnt", id_pnt)

        if "error" in raw and raw["error"]:
            error = True
            color = ERROR_MARKER # color = ERROR_MARKER permet de propager la couleur d'erreur au segment suivant

        if error:
            error = False if color != ERROR_MARKER else True
            color = error_color

        # Création des entités
        if ent_type == "l":     # droite de connextion dépandente du end pécédent et du start suivant
            # Détection de direction inversée (raccordement incohérent)        
            ref_point = None    # Trouver le prochain segment qui a une clé 'start' ou 'end' (selon reverse)
            if not reverse:
                start, end = raw["start"], raw["end"]
                for _raw in raw_list[idx_raw + 1:]:
                    if "start" in _raw:
                        ref_point = _raw["start"]
                        break
                next_start = ref_point or end
            else:
                start, end = raw["end"], raw["start"]
                for idx in range(idx_raw -1, -1, -1):
                    _raw = raw_list[idx]
                    if "end" in _raw:
                        ref_point = _raw["end"]
                        break
                next_start = ref_point or end


            if next_start is not None:
                dx1 , dy1 = end[0] - start[0] , end[1] - start[1]
                dx2 , dy2 = next_start[0] - last_end[0] , next_start[1] - last_end[1]
                # Calcul du produit scalaire pour vérifier si les directions sont opposées
                dot_product = dx1 * dx2 + dy1 * dy2
                if dot_product < 0:
                    color = error_color
                    error = True
                    if entities:
                        entities[-1]["color"] = error_color

                #print(f"DEBUG: -----longueur {len_original /len_dest} ---- original:{len_original}  dest:{len_dest}")
                entities.append(creat_entry_line(last_end, next_start, color, origin_color, ident))

        elif ent_type == "d":        # droite autonome (utilise son propre start et end)
            if reverse:    # Ordre des points selon reverse
                start, end = raw["end"], raw["start"]
            else:
                start, end = raw["start"], raw["end"]

            if start != end:
                entities.append(creat_entry_line(start, end, color, origin_color, ident))

        elif ent_type == "a":        
            if reverse:    # Ordre des points selon reverse
                start, end = raw["end"], raw["start"]
            else:
                start, end = raw["start"], raw["end"]

            center, radius, cw = raw["center"], raw["radius"], raw["dir"] if not reverse else not raw["dir"]
            if radius != 0:
                entities.append(creat_entry_arc(start, end, center, radius, cw, color, origin_color, ident))
            else:
                end = last_end  # arc fictif → aucun changement de position
                if not cw:
                    error = True

        elif ent_type == "c":
            center, radius = raw["center"], raw["radius"]
            end = last_end  # ne pas modifier last_end
            if radius != 0:
                entities.append(creat_entry_circle(center, radius, color, origin_color, ident))

        else:
            print(f"[WARN] Type inconnu : {ent_type}")
            end = last_end

        return end


    # Parcours principal
    #for next_raw in (reversed(raw_list) if reverse else raw_list):
    len_list = len(raw_list)
    index = 0
    for idx in range(len_list):
        index = idx if not reverse else (len_list - 1 - idx)
        raw = raw_list[index]
        last_end = compute_raw(index)

    return entities

def extract_raw_from_entity(entity, use_origin_color=True, reverse=False):
    """
    Transforme une entité (dictionnaire prêt à dessiner) en un dictionnaire brut.

    Args:
        entity (dict): Une entité ("line", "arc", "cercle") au format dict.
        use_origin_color (bool): Si True, utilise 'origin_color' si dispo, sinon 'color'.
        reverse (bool): Si True, inverse le sens des segments.

    Returns:
        dict: Un dictionnaire brut décrivant l'entité.
    """
    if not isinstance(entity, dict):
        print(f"[WARN] Type invalide pour entity: {type(entity)}")
        return None

    typ = entity.get("type")
    color = entity.get("origin_color") if use_origin_color else entity.get("color")
    id_pnt = entity.get("id_pnt", None)
    error = None

    if entity.get("origin_color"):
        error = (entity.get("origin_color") != entity.get("color"))

    if typ == "line":
        start = entity["end"] if reverse else entity["start"]
        end = entity["start"] if reverse else entity["end"]
        return {
            "type": "d",
            "start": start,
            "end": end,
            "color": color,
            "id_pnt": id_pnt,
            "error": error
        }

    elif typ == "arc":
        start = entity["end"] if reverse else entity["start"]
        end = entity["start"] if reverse else entity["end"]
        center = entity["center"]
        radius = entity["radius"]
        cw = not entity["cw"] if reverse else entity["cw"]
        return {
            "type": "a",
            "start": start,
            "end": end,
            "center": center,
            "radius": radius,
            "dir": cw,
            "color": color,
            "id_pnt": id_pnt,
            "error": error
        }

    elif typ == "cercle":
        center = entity["center"]
        radius = entity["radius"]
        return {
            "type": "c",
            "center": center,
            "radius": radius,
            "color": color,
            "id_pnt": id_pnt,
            "error": error
        }

    else:
        print(f"[WARN] Type inconnu pour extraction brute : {typ}")
        return None

def creat_entry_line(start_point, end_point, color, origin_color=None, id_pnt=None):
    bbox=calculate_bbox_for_line(start_point, end_point)
    n_color = normalize_color(color)
    n_n_color = normalize_color(origin_color) if origin_color else n_color
    return {"type": "line", "start": start_point, "end": end_point, "bbox":bbox, "color": n_color, "origin_color":n_n_color, "id_pnt": id_pnt}

def creat_entry_arc(start_point, end_point, center_point, radius, cw, color, origin_color=None, id_pnt=None):
    bbox=calculate_bbox_for_arc(start_point, center_point, end_point, cw)
    n_color = normalize_color(color)
    n_n_color = normalize_color(origin_color) if origin_color else n_color
    #print(f"DEBUG_creat_entry_arc start_point:{start_point} center_point:{center_point} end_point:{end_point}")
    #print(f"DEBUG_creat_entry_arc bbox:{bbox[0]} : {bbox[1]}")
    return {
        "type": "arc", "start": start_point, "end": end_point, "center": center_point,
            "radius": radius, "cw":  cw, "bbox":bbox, "color": n_color, "origin_color":n_n_color, "id_pnt": id_pnt}

def creat_entry_circle(center_point, radius, color, origin_color=None, id_pnt=None):
    bbox=calculate_bbox_for_circle(center_point, radius)
    n_color = normalize_color(color)
    n_n_color = normalize_color(origin_color) if origin_color else n_color
    return {"type": "cercle", "center": center_point, "radius": radius, "bbox":bbox, "color": n_color, "origin_color":n_n_color, "id_pnt": id_pnt}

# bounding box
def calculate_bbox_for_line(A, B):
    x_min = min(A[0],B[0])
    x_max = max(A[0],B[0])
    y_min = min(A[1],B[1])
    y_max = max(A[1],B[1])
    return ([x_min, y_min],[x_max, y_max])

def calculate_bbox_for_arc(A, B, C, cw=True):
    """
    Calcule la bounding box pour un arc de cercle ou un cercle complet.
    """

    # convertir les anti-horaire en horaire
    if not cw:
        A, C = C, A
    
    v_a =(A[0]-B[0], A[1]-B[1])
    v_c =(C[0]-B[0], C[1]-B[1])
    r = math.hypot(v_a[0],v_a[1])

    def get_quadrant_cw(vect):
        x, y = vect
        
        # 12h°° -> 3h°° : 1er secteur horaire
        if x >= 0 and y > 0:
            return 0        #{"quart":0, "demi": 0 if x <= y else 1}
        
        # 3h°° -> 6h°° : 2e secteur horaire
        elif x > 0 and y <= 0:
            return 1        #{"quart":1, "demi": 0 if x >= -y else 1}
        
        # 6h°° -> 9h°° : 3e secteur horaire
        elif x <= 0 and y < 0:
            return 2        #{"quart":2, "demi": 0 if -x <= -y else 1}
        
        # 9h°° -> 12h°° : 4e secteur horaire
        elif x < 0 and y >= 0:
            return 3        #{"quart":3, "demi": 0 if -x >= y else 1}

    quart_a = get_quadrant_cw(v_a)
    quart_c = get_quadrant_cw(v_c)
    '''
    q1 = quart_a - quart_c
    if q1 < 0:
        q1 +=4
    '''
    q1 = quart_c - quart_a
    if q1 < 0:
        q1 +=4
        
    if quart_a == 0:
        v1 = v_a[0] , v_a[1]
        v2 = v_c[0] , v_c[1]
    elif quart_a == 1:
        v1 = -v_a[1] , v_a[0]
        v2 = -v_c[1] , v_c[0]
    elif quart_a == 2:
        v1 = -v_a[0] , -v_a[1]
        v2 = -v_c[0] , -v_c[1]
    elif quart_a == 3:
        v1 = v_a[1] , -v_a[0]
        v2 = v_c[1] , -v_c[0]

    #ref départ
    min_0 = max_0 = v1[0]
    min_1 = max_1 = v1[1]


    if q1 == 0:    
        if v1[0] <= v2[0]:    #if v1[0]> v2[0]: pour un cercle (A=C) ou if v1[0] <= v2[0]: Pour un arc (A=C) (en gros un cercle ou un point
            max_0 = v2[0]
            min_1 = v2[1]
        else:            # Presque un tour complet
            max_0 = r    # Juste on a passé 3h°°
            min_1 = -r   # Juste on a passé 6h°°
            min_0 = -r   # Juste on a passé 9h°°
            max_1 = r    # Juste on a passé 12h°°
    else:
        max_0 = r        # Juste on a passé 3h°°
        if q1 ==1:
            min_0 = min(v1[0],v2[0]) # Le plus à gauche des deux (le plus prêt de l'axe Y)
            min_1 = v2[1]            # C'est le point le plus en bas de tous l'arc
        elif q1 ==2:
            min_0 = v2[0]            # C'est le point le plus à gauche de tout l'arc
            min_1 = -r   # Juste on a passé 6h°°
        else:   #if q1 ==3:
            min_1 = -r   # Juste on a passé 6h°°
            min_0 = -r   # Juste on a passé 9h°°
            max_1 = max(v1[1],v2[1])  # C'est le plus haut des deux (le plus loing de l'axe X)
    
    #print(f"DEBUG_calculate_bbox_for_arc: max_0:{max_0} min_x:{min_0} max_y:{max_1} min_y:{min_1} q1:{q1} quart_a:{quart_a} quart_c:{quart_c}")
    
    # On retourne nos min et max 0 et 1 de quart_a
    if quart_a == 0:
        max_x = max_0
        min_x = min_0
        max_y = max_1
        min_y = min_1
    elif quart_a == 1:
        max_x = max_1
        min_x = min_1
        max_y = -min_0
        min_y = -max_0
    elif quart_a == 2:
        max_x = -min_0
        min_x = -max_0
        max_y = -min_1
        min_y = -max_1
    elif quart_a == 3:
        max_x = -min_1
        min_x = -max_1
        max_y = max_0
        min_y = min_0
        
    return ([B[0]+min_x, B[1]+min_y],[B[0]+max_x, B[1]+max_y])

def calculate_bbox_for_circle(B, radius):
    return ([B[0]-radius, B[1]-radius],[B[0]+radius, B[1]+radius])


# Autres outils
# >>> A déplacer dans theme_manager.py ???
def normalize_color(color):
    """
    Normalise une couleur au format (r, g, b, a) en float [0.0–1.0].
    Accepte :
        - Tuple/list (r, g, b)
        - Tuple/list (r, g, b, a)
        - Hexadécimal "#rrggbb" ou "#rrggbbaa"
    Retourne :
        (r, g, b, a)
    """
    if color == "def":  # définir la couleur par défaut
        color = th_drl["profil"]

    if isinstance(color, str):
        color = color.strip()
        if color.startswith("#"):
            hex_color = color.lstrip("#")
            if len(hex_color) == 6:
                r, g, b = [int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4)]
                a = 1.0
            elif len(hex_color) == 8:
                r, g, b, a = [int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4, 6)]
            else:
                raise ValueError(f"Hex color invalide : {color}")
            return (r, g, b, a)
        else:
            raise ValueError(f"Chaîne de couleur non supportée : {color}")

    elif isinstance(color, (list, tuple)):
        if len(color) == 3:
            return tuple(color) + (1.0,)
        elif len(color) == 4:
            return tuple(color)
        else:
            raise ValueError(f"Tuple/list couleur invalide : {color}")

    else:
        raise TypeError(f"Type couleur non pris en charge : {type(color)}")

