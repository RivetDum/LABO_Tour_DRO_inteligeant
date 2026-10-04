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


class ProfilCanvas(Widget):
    """ (docstring de classe)
    Widget personnalisé pour dessiner des entités géométriques (lignes, arcs et plaquettes)
    à l'intérieur d'une boîte de dessin. Gère le redimensionnement et la mise à l'échelle
    automatique ou fixe selon la taille du widget parent (BoxLayout) ou l'échelle transmise.

    Attributs :
    - a_entities, b_entities : Listes d'entités brutes en microns [µm] (Pièce / Outil).
    - box_dest               : Lien vers le BoxLayout de destination (pour relevé de taille [Px] et position).
    - scale                  : Facteur d'échelle graphique appliqué au dessin en [Px/µm].
    - offset_0               : Coordonnée absolue [Px] de l'écran correspondant au point 0,0 de la pièce.
    - a_segments, b_segments : Listes des segments convertis en pixels fixes [Px], prémâchés pour Kivy.

    Méthodes principales :
    - update_size_entities() : Met à jour la box de destination et réaligne l'ancrage spatial de la Trinité.
    - update_offset()        : Modifie les offsets statiques de positionnement (glisser de la souris opérateur).
    - move_axes_machine()    : Reçoit les microns des règles de l'ESP32. Tracé dynamique à calcul ultra-allégé.
    - search_auto_scale()    : Calcule et renvoie l'échelle idéale [Px/µm] pour afficher la pièce "Pleine Page".
    - set_scale()            : Paramètre le zoom manuel ou enclenche le calcul automatique (force le recalcul global).
    - up_drawing()           : Portier public qui cadence les demandes de rafraîchissement sur le métronome de 25ms.
    """

    def __init__(self, box, offset_pos=[0, 0], offset_move=None, scale=None, mirror_vert=True, mirror_hor=False, conect_line=False,
                 A_entities=None, A_outline_width=2.1, A_fill_color=None,
                 B_entities_machine=None, B_outline_width=1.9, B_fill_color=None, 
                 **kwargs):
        super().__init__(**kwargs)

        # ==========================================================
        # CONFIGURATION GÉNÉRALE 1ère partie
        # ==========================================================
        self.box_dest = box            # Lien vers la boîte de l'écran pour calculer sa taille et sa position
        self.mirror_vert = mirror_vert  # TODO:à mettre en place. Utiliser un mirroir vertical pour le dessin (et les offset ?)
        self.mirror_hor = mirror_hor    # TODO:à mettre en place. Utiliser un mirroir horizontal pour le dessin (et les offset ?)        
        self.auto_scale = True if scale is None else False  # Utiliser le zoom automatique en fonction de la taille de la box
        self.auto_scale_entities_def = "defCode AB" # = "A et/ou B" les list[_entities] à utiliser par défaut
        self.auto_scale_entities_last = self.auto_scale_entities_def # Valeur de la dernière demande de zoom automatique
        self.scale = scale if (scale is not None and scale > 0) else 0.1    # ne jamais passer scale à 0 !!     Échelle graphique du dessin en[Px/µm]
        self.scale_def = self.scale     # TODO: devra être importée depuis les paramètres ==> Échelle par défaut en[Px/µm]
        self.connect_line = conect_line                     # Utiliser le premier et dernier segment pour calculer le zoom automatique
        self.offset_base = [0.5,0.5]
        #self.offset_base = offset_pos or [0,0] # TODO: devra être importée depuis les paramètres ==> Offset visuel de base EN RATIO de la taille de l'écran, définit le pnt0,0 de référance
        #self.offset_add_ratio = False   # True : self.offset_add = ratio de boxe_size / False : self.offset_add = valeurs en pixels    
        self.offset_screen = [0,0]       # Offset représantant les déplacement à la sourie de l'opérateur (en pixel)
        self.offset_move = offset_move or [0,0]  # offset représantant les mouvement des axes machine (en um , multiplier par zoom avant l'emplois)
        box_x = self.box_dest.pos[0] if hasattr(self.box_dest, 'pos') else 0   # Position absolue en "X" du boxLayout reçu en lien
        box_y = self.box_dest.pos[1] if hasattr(self.box_dest, 'pos') else 0
        base_pixelx, base_pixely = self.offset_ratio_to_pixel(self.offset_base) #TODO: fonction à écrire
        self.offset_0 = [box_x + base_pixelx + self.offset_screen[0], box_y + base_pixely + self.offset_screen[1]] # position absolue de la coordonnée 0,0 pour notre dessin

        # ==========================================================
        # CONFIGURATION LISTE 1 : LE DESSIN ACTUEL (Pièce)
        # ==========================================================
        self.a_entities = A_entities or []          # Liste des segments bruts (sans échelle)
        self.a_segments = []                        # Liste des segments précalculés en pixels fixes
        self.a_width = A_outline_width or 0         # Épaisseur du trait, si 0 -> pas de contour
        self.a_fill_color = A_fill_color            # Couleur de remplissage (None -> pas de remplissage)

        # ==========================================================
        # CONFIGURATION LISTE 2 : LA MACHINE (Optionnelle)
        # ==========================================================
        self.b_entities = B_entities_machine or []  # Liste des segments bruts machine (sans échelle)
        self.b_segments = []                        # Liste des segments précalculés en pixels fixes
        self.b_width = B_outline_width or 0         # Épaisseur du trait large machine
        self.b_fill_color = B_fill_color            # Couleur de remplissage machine (ex: None)

        # ==========================================================
        # CONFIGURATION GÉNÉRALE 2ème partie
        # ==========================================================
        self.recalc_a = self.recalc_b = False   # définit si .precalculer_profils_statiques() doit recalculer .a_segments et.b_segments
        self.update_draw = False                # définit si à la fin du timer un recalcul ou re-dessin et demandé
        
        # on fait tourner une fois le debounce à vide pour temporiser les màj de la fonction suivante (self.set_scale()), qui va màj l'affichage
        self.timer_update_draw = True          # définit si un timer de debounce_affichage et en cours (True vu que l'on active ce debounce à la ligne suivante)
        self._timer_debounce_on()       # On utilise le debounce pour une petite temporisation avant de raffraichir l'affichage

        self.set_scale(scale=self.scale, auto_scale=self.auto_scale)    # pour forcer les calculs et l'affichage à ce mettre à jour

    # Fonction de debounce pour les calculs lourd et la màj graphique
    def up_drawing(self):
        """
        PORTIER : Reçoit toutes les requêtes de l'IHM (Souris, Manivelles, Zoom).
        """
        if self.timer_update_draw is False:
            # L'écran est au repos : on recalcul et on dessine tout de suite, puis on allume le métronome
            self._time_auto_draw(restart=True)
        else:
            # Le timer tourne déjà : on lève le drapeau qui dit à la fin de ton debounce recommence il y a de nouveau changement.
            self.update_draw = True
    def _time_auto_draw(self, restart=False):
        """
        CADENCEUR CHIRURGICAL : Gère l'exécution des calculs et du tracé 
        selon l'état des drapeaux et du métronome de 25ms.
        """
        if restart or self.update_draw: # si des modifications sont pas encore dessinées
            # On verrouille le statut du métronome en cours (comme il va être re-lancé on le laisse marqué comme actif)
            self.timer_update_draw = True
            # On nettoie le drapeau pour pouvoir détecter les mouvements pendant le temps de debounce !
            self.update_draw = False
            local_code_last = self.auto_scale_entities_last
            self.auto_scale_entities_last = self.auto_scale_entities_def # on le réinitialise tout de suite si un changement arrive avant la fin de la fonction
            local_recalc_a = self.recalc_a
            local_recalc_b = self.recalc_b
            self.recalc_a = self.recalc_b = False   # ici on a màj tous les flags avant l'exécution des fonctions lourdes en temps

            # --- 1. FILTRE DU PRÉCALCUL GÉOMÉTRIQUE LOURD ---
            if local_recalc_a or local_recalc_b:
                
                # Si on est en mode auto, on recalcule le zoom 
                # pile au moment du battement, profitant des dimensions finales de la box !
                if self.auto_scale:
                    # 1. On calcule l'échelle sur le code actuellement demandé par l'IHM
                    nouvelle_echelle = self.search_auto_scale(local_code_last)
                    
                    if nouvelle_echelle is not False:
                        self.scale = nouvelle_echelle
                    
                    # 2. LA CORRECTION : On ne mémorise le code utilisé QU'APRÈS l'exécution !
                    #self.last_code = self.auto_scale_entities_def

                # On lance le précalcul statique avec la nouvelle échelle toute fraîche
                self.precalculer_profils_statiques(local_recalc_a, local_recalc_b)


            # --- 2. TRAÇAGE À L'ÉCRAN ---
            # S'exécute à chaque battement actif (Usinage / Manivelle / Glisser)
            self.trigger_redraw()

            # --- 3. RELANCE DU BOUCLIER TEMPOREL ---
            # On ré-arme le chrono pour contrôler les modifications qu'il y aura u dans 25ms ET si non on autorise un redessin imédiat
            self._timer_debounce_on()
            
        else:
            # Fin du mouvement : Le timer a expiré et aucun nouveau déplacement n'a eu lieu.
            # On éteint proprement le métronome, le système revient au repos à 0% de CPU.
            self.timer_update_draw = False
    def _timer_debounce_on(self):
        """
        L'HORLOGE KIVY : Patiente sagement 25 millisecondes avant de 
        ré-interroger le cadenceur pour vérifier s'il y a de nouveaux changements.
        """
        self.timer_update_draw = True   # On force à true si cela avait été oublié à l'appel de la fonction
        
        # On utilise une fonction anonyme (lambda) pour forcer Kivy à appeler 
        # time_auto_draw avec l'argument restart=False (votre logique de battement suivant).
        # Le paramètre dt (delta_time) est automatiquement transmis par l'horloge Kivy.
        Clock.schedule_once(lambda dt: self._time_auto_draw(restart=False), 0.025)  # 25ms

    # Fonction qui peuvent modifier le dessin
    def update_size_entities(self, box_dest=None, a_entities=None, b_entities=None):
        """
        Gère le changement de géométrie et/ou le redimensionnement de la box.
        """
        #recalc_a = recalc_b = False


        # On recalcule systématiquement offset_0 à partir de l'objet de destination actuel
        if box_dest is not None:  # si box_dest reçu n'est pas None (un lien vers un BoxLayout, mais aussi True, ...) on force une màj
            # Sécurité : On vérifie strictment si c'est un objet de type BoxLayout
            if box_dest and isinstance(box_dest, BoxLayout):
                self.box_dest = box_dest
            base_pixelx, base_pixely = self.offset_ratio_to_pixel(self.offset_base)
            pos_x = self.box_dest.pos[0] if hasattr(self.box_dest, 'pos') else 0
            pos_y = self.box_dest.pos[1] if hasattr(self.box_dest, 'pos') else 0
            self.offset_0 = [pos_x + base_pixelx + self.offset_screen[0], pos_y + base_pixely + self.offset_screen[1]]
            #recalc_a = recalc_b = True  # .offset_0 à changé, on doit refaire le pré-calcul statique des 2 listes de segments
            self.recalc_a = self.recalc_b = True
            #DEBUG imprimer la taille et position de la box et offset_0
            #print(f"\n[DEBUG update_size_entities - up_box] Taille Box  : {self.box_dest.size if hasattr(self.box_dest, 'size') else 'Inconnue'}")
            #print(f"[DEBUG update_size_entities - up_box] Position Box  : {pos_x}/{pos_y}")
            #print(f"[DEBUG update_size_entities - up_box] offset_ratio_to_pixel: {base_pixelx} / {base_pixely}")
        #print(f"[DEBUG update_size_entities - up_box] offset_0 : [self.offset_0]")


        if a_entities is not None:
            self.a_entities = a_entities or []
            #recalc_a = True
            self.recalc_a = True
        if b_entities is not None:
            self.b_entities = b_entities or []
            #recalc_b = True
            self.recalc_b = True
        
        #self.precalculer_profils_statiques(recalc_a, recalc_b)
        #self.trigger_redraw()    # DESSIN : On force Kivy à effacer la toile et à tout repeindre
        self.up_drawing()   # fonction qui lance les màj en fonction de self.timer_update_draw
        
    def OLD_update_entities_auto_scale_auto_center(self, box_dest=None, a_entities=None, b_entities=None, code_entities=None, save_code=True, margin=[0.2, 0.2]):
        """ ⚠️ ATTENTION : Ne pas utiliser cette fonction où
                self.offset_move représente la position réelle des axes de la machine ⚠️

        Fonction pour la màj d'affichage auto_centré et zoom_pleine_page, màj des segments et des mouvements-dimenssions de box

        arg:
            - box_dest : la box de destination pour y mesurer la taille et position
            - a_entities, b_entities : les listes d'entités à dessiner
            - code_entities : le code désignant les _entities à utiliser pour les mesures et définit s'il faut supprimer des lignes de connexion dans les calculs
            - save_code : définit si le code reçu doit remplacer le code par défaut actuel (self.auto_scale_entities_def)
        """

        last_offset_move = self.offset_move.copy()  # Valeur avant modification, pour le retour

        # =====================================================================
        # 🧱 1. ENREGISTREMENT ET CHARGEMENT SUR LE BÂTI
        # =====================================================================
        if box_dest is not None:
            if box_dest and isinstance(box_dest, BoxLayout):
                self.box_dest = box_dest
                
            if  hasattr(self.box_dest, 'size') and hasattr(self.box_dest, 'pos'):
                pos_x = self.box_dest.pos[0]
                pos_y = self.box_dest.pos[1]
                box_w = self.box_dest.size[0]
                box_h = self.box_dest.size[1] 
            else:
                pos_x = 0
                pos_y = 0
                box_w = 100
                box_h = 100
            # On force le ratio au centre exact [0.5, 0.5]
            base_pixelx = box_w  / 2
            base_pixely = box_h / 2
            self.offset_0 = [pos_x + base_pixelx + self.offset_screen[0], pos_y + base_pixely + self.offset_screen[1]]
            self.recalc_a = self.recalc_b = True

        marge_box = margin
        
        if a_entities is not None: 
            self.a_entities = a_entities or []
            self.recalc_a = True
            
        if b_entities is not None: 
            self.b_entities = b_entities or []
            self.recalc_b = True

        # =====================================================================
        # 🎛️ 2. GESTION DYNAMIQUE DU CODES de sélection d'entities
        # =====================================================================
        code_recherche = self.auto_scale_entities_def
        if code_entities and isinstance(code_entities, str):
            code_recherche = code_entities  # Sélection du code : on prend le code reçu
            if save_code:    # LOGIQUE d'intention : on sauvegarde comme valeur par défaut
                self.auto_scale_entities_def = code_entities

        self.auto_scale_entities_last = code_entities   # pour le prochain appel à self._time_auto_draw()

        # =====================================================================
        # 📐 3. LE SCAN UNIQUE ET L'ALIGNEMENT VECTORIEL
        # =====================================================================
        # On passe votre code_recherche validé à l'aiguillage universel
        bbox = self.search_min_max(code_recherche)
        
        if bbox:
            # ÉTAPE A : Calcul de la loupe idéale à partir de la bbox_um (0 microseconde perdue)
            nouvelle_echelle = self.compute_scale_from_bbox(bbox, margin=marge_box)
            if nouvelle_echelle and nouvelle_echelle > 0:
                self.scale = nouvelle_echelle
                self.recalc_a = self.recalc_b = True
            else:
                print(f"[ERROR-AVERTISSEMENT update_entities_auto_scale_auto_center] nouvelle_echelle : {nouvelle_echelle} (Normal une fois au démarrage!)")
                return

            # ÉTAPE B : Recentrage géométrique parfait au milieu exact de la box
            # On lui injecte la nouvelle échelle calculée !
            nouvelle_offset = self.compute_center_from_bbox(bbox_um=bbox, scale_ref=nouvelle_echelle, offset_px=self.offset_screen)
            if nouvelle_offset:
                self.offset_move[0], self.offset_move[1] = -1*nouvelle_offset["en_um"][0], -1*nouvelle_offset["en_um"][1]
                # ici pas de drapeau pour self._time_auto_draw() à lever
        '''# DEBUG <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<    
            print(f"[DEBUG update_entities_auto_scale_auto_center] box_size: {self.box_dest.size}") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] box_pos : {self.box_dest.pos}") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] bbox  : {bbox}") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] scale : {nouvelle_echelle}") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] offset: [px] {nouvelle_offset["en_px"]}")
            print(f"[DEBUG update_entities_auto_scale_auto_center] offset: [um] {self.offset_move}")
            print(f"[DEBUG >>>> update_entities_auto_scale_auto_center >> a_entities") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] self.a_entities  : \n{self.a_entities}") 
            print(f"[DEBUG <<<< update_entities_auto_scale_auto_center <<<< end print") '''
        # =====================================================================
        # 🏎️ 4. RÉVEIL DU CADENCEUR ASYNCHRONE
        # =====================================================================
        # On force le précalcul et on réveille le portier de 25ms pour repeindre l'IHM
        self.up_drawing()
        return {"last_offset_move" : last_offset_move, "new_offset_move": self.offset_move}
    def update_entities_auto_scale_auto_center(self, box_dest=None, a_entities=None, b_entities=None, code_entities=None, save_code=True, margin=[0.2, 0.2]):
        # Correction du recentrage sur le mouvement de la souris (en px) plutôt que sur les mouvements machine (en um)

        """ ⚠️ ATTENTION : Ne pas utiliser cette fonction où
                self.offset_move représente la position réelle des axes de la machine ⚠️

        Fonction pour la màj d'affichage auto_centré et zoom_pleine_page, màj des segments et des mouvements-dimenssions de box

        arg:
            - box_dest : la box de destination pour y mesurer la taille et position
            - a_entities, b_entities : les listes d'entités à dessiner
            - code_entities : le code désignant les _entities à utiliser pour les mesures et définit s'il faut supprimer des lignes de connexion dans les calculs
            - save_code : définit si le code reçu doit remplacer le code par défaut actuel (self.auto_scale_entities_def)
        """

        last_offset_move = self.offset_move.copy()  # Valeur avant modification, pour le retour

        # =====================================================================
        # 🧱 1. ENREGISTREMENT ET CHARGEMENT SUR LE BÂTI
        # =====================================================================
        if box_dest is not None:
            if box_dest and isinstance(box_dest, BoxLayout):
                self.box_dest = box_dest
            
        if  hasattr(self.box_dest, 'size') and hasattr(self.box_dest, 'pos'):
            pos_x = self.box_dest.pos[0]
            pos_y = self.box_dest.pos[1]
            box_w = self.box_dest.size[0]
            box_h = self.box_dest.size[1] 
            centre_box_x = self.box_dest.center_x
            centre_box_y = self.box_dest.center_y
        else:
            #pos_x = 0
            #pos_y = 0
            #box_w = 100
            #box_h = 100
            centre_box_x = 50
            centre_box_y = 50
        # On force le ratio au centre exact [0.5, 0.5]
        #base_pixelx = box_w  / 2
        #base_pixely = box_h / 2
        #centre_box_x = pos_x + base_pixelx
        #centre_box_y = pos_y + base_pixely
        #self.offset_0 = [centre_box_x, centre_box_y]    # On garde [self.offset_screen] pour placer le dessin au centre (sur offset_0)

        marge_box = margin
        #marge_box = [0.3,0.3]
        #self.offset_move = [0,0]
        
        if a_entities is not None: 
            self.a_entities = a_entities or []
            self.recalc_a = True
            
        if b_entities is not None: 
            self.b_entities = b_entities or []
            self.recalc_b = True

        # =====================================================================
        # 🎛️ 2. GESTION DYNAMIQUE DU CODES de sélection d'entities
        # =====================================================================
        code_recherche = self.auto_scale_entities_def
        if code_entities and isinstance(code_entities, str):
            code_recherche = code_entities  # Sélection du code : on prend le code reçu
            if save_code:    # LOGIQUE d'intention : on sauvegarde comme valeur par défaut
                self.auto_scale_entities_def = code_entities

        self.auto_scale_entities_last = code_entities   # pour le prochain appel à self._time_auto_draw()

        # =====================================================================
        # 📐 3. LE SCAN UNIQUE ET L'ALIGNEMENT VECTORIEL
        # =====================================================================
        # On passe votre code_recherche validé à l'aiguillage universel
        bbox_draw = self.search_min_max(code_recherche)  #return (en um): [[Xmin, Ymin], [Xmax, Ymax]] (sans adaptation des miroirs)
                
        if bbox_draw:
            # ÉTAPE A : Calcul de la loupe idéale à partir de la bbox_um
            nouvelle_echelle = self.compute_scale_from_bbox(bbox_draw, margin=marge_box)
            if nouvelle_echelle and nouvelle_echelle > 0:
                self.scale = nouvelle_echelle
                self.recalc_a = self.recalc_b = True
            else:
                print(f"[ERROR-AVERTISSEMENT update_entities_auto_scale_auto_center] nouvelle_echelle : {nouvelle_echelle} (Normal une fois au démarrage!)")
                return

            # ÉTAPE B : Recentrage géométrique parfait au milieu exact de la box
            '''NEW_VERSION:'''
            #Ps: On peut plus prendre les valeurs en Px de bbox_draw car l'échelle à changé !
            delta_um_x =(bbox_draw[1][0]-bbox_draw[0][0]) #* (1 + marge_box[0] * 2)
            delta_um_y = (bbox_draw[1][1]-bbox_draw[0][1]) #* (1 + marge_box[1] * 2)
            new_ofst_um = [bbox_draw[0][0] + delta_um_x /2, bbox_draw[0][1] + delta_um_y /2]
            # On simule un déplacement à la souris pour centrer le dessin (valeurs en Pixels)
            #self.offset_screen = [-new_ofst_um[0] * nouvelle_echelle, new_ofst_um[1] * nouvelle_echelle]            
            self.offset_screen = [-new_ofst_um[0] * self.scale, new_ofst_um[1] * self.scale]        
            #self.offset_screen = [4771.805555555556, 1218.3333333333333]        
            self.offset_0 = [
                centre_box_x + self.offset_screen[0],
                centre_box_y + self.offset_screen[1]
            ] 
        '''# DEBUG <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<    
            print(f"[DEBUG auto_scale_center] scale: {self.scale}, ofst_um {new_ofst_um}, ofst_Px {self.offset_screen}") 
            
            print(f"[DEBUG update_entities_auto_scale_auto_center] box_size: {self.box_dest.size}") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] box_pos : {self.box_dest.pos}") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] bbox  : {bbox}") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] scale : {nouvelle_echelle}") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] offset: [px] {nouvelle_offset["en_px"]}")
            print(f"[DEBUG update_entities_auto_scale_auto_center] offset: [um] {self.offset_move}")
            print(f"[DEBUG >>>> update_entities_auto_scale_auto_center >> a_entities") 
            print(f"[DEBUG update_entities_auto_scale_auto_center] self.a_entities  : \n{self.a_entities}") 
            print(f"[DEBUG <<<< update_entities_auto_scale_auto_center <<<< end print") '''
        # =====================================================================
        # 🏎️ 4. RÉVEIL DU CADENCEUR ASYNCHRONE
        # =====================================================================
        # On force le précalcul et on réveille le portier de 25ms pour repeindre l'IHM
        self.up_drawing()
        return {"last_offset_move" : last_offset_move, "new_offset_move": self.offset_move}

    def update_offset(self, offset_screen=None, offset_base=None, not_calc_new=False):
        """
        Modification des offsets de positionnement (Souris [Px] ou Ratio point_zéro).
        arg:
            - offset_screen : c'est les déplacement du dessin par l'opérateur en[pixel] . (glisser à la souris)
            - offset_base   : c'est le placement de la référence par défaut en[ratio de la fenêtre]) .
            - not_calc_new  : À utiliser uniquement si une autre fonction recalcul et redessinne drtoit derrière
        """
        recalc = False

        if offset_screen is not None:
            self.offset_screen = offset_screen
            recalc = True

        if offset_base is not None:
            self.offset_base = offset_base
            recalc = True

        if recalc:
            pos_x = self.box_dest.pos[0] if hasattr(self.box_dest, 'pos') else 0
            pos_y = self.box_dest.pos[1] if hasattr(self.box_dest, 'pos') else 0
            base_pixelx, base_pixely = self.offset_ratio_to_pixel(self.offset_base)
            self.offset_0 = [pos_x + base_pixelx + self.offset_screen[0], pos_y + base_pixely + self.offset_screen[1]]
            self.recalc_a = self.recalc_b = True

            if not not_calc_new:
                #self.precalculer_profils_statiques(recalc_a=True, recalc_b=True)
                #self.trigger_redraw()
                self.up_drawing()   # fonction qui lance les màj en fonction de self.timer_update_draw

    def offset_ratio_to_pixel(self, ratio_list):
        """
        CONVERTISSEUR GÉOMÉTRIQUE : Convertit un ratio de positionnement [0.0 à 1.0]
        en pixels réels [Px] d'après les dimensions actuelles de self.box_dest.
        """
        # Sécurité franche : Si ratio_list est invalide ou vide, on se cale au centre (0.5, 0.5)
        if not isinstance(ratio_list, (list, tuple)) or len(ratio_list) != 2:
            ratio_list = [0.5, 0.5]

        # 1. On récupère la taille en pixels du cadre Kivy parent
        box_width = self.box_dest.size[0] if hasattr(self.box_dest, 'size') else 100
        box_height = self.box_dest.size[1] if hasattr(self.box_dest, 'size') else 100

        # 2. Application de la règle mécanique : Pixel = Dimension_Cadre * Ratio
        pixel_x = box_width * ratio_list[0]
        pixel_y = box_height * ratio_list[1]

        return pixel_x, pixel_y

    def move_axes_machine(self, offset_move, not_calc_new=False):
        """
        Reçoit le déplacement en direct des axes en [µm].
        arg:
            - offset_move : C'est les valeurs [profondeur, rayon] en [µm] revoyé par les règles de le tour (chariot inclinable compris)
            - not_calc_new  : À utiliser uniquement si une autre fonction recalcul et redessinne droit derrière
        """
        if offset_move is not None:
            self.offset_move = offset_move
            if not not_calc_new:
                # Ici pas de précalculs, vue que ces variables sont ajouter pendant le dessin
                #self.trigger_redraw()
                self.up_drawing()   # fonction qui lance les màj en fonction de self.timer_update_draw

    def set_scale(self, scale, auto_scale=None):
        """
        Modifie ou verrouille l'échelle graphique de dessin [Px/µm].
        arg:
            - auto_scale:
                >> None  : Ne change rien au mode automatique actuel (True ou False).
                >> False : Désactive le zoom automatique.
                >> True  : Active le zoom auto avec le code par défaut (self.auto_scale_entities_def).
                >> str   : Active le zoom auto et force l'utilisation de ce code ("a", "b", "a B", ...).
        """
        # --- 1. GESTION DU MODE AUTOMATIQUE (Vos 4 états) ---
        if auto_scale is None:
            # On ne change rien à l'état actuel de self.auto_scale !
            pass
            
        elif auto_scale is True or isinstance(auto_scale, str):
            # On active le mode automatique
            self.auto_scale = True
            
            # Sélection du code de recherche (str spécifique ou valeur par défaut)
            self.auto_scale_entities_last = auto_scale if isinstance(auto_scale, str) else self.auto_scale_entities_def
            # Calcul de la taille idéale
            #nouvelle_echelle = self.search_auto_scale(code_recherche)
            #if nouvelle_echelle is not False:
            #    self.scale = nouvelle_echelle
            #else:
            #    self.scale = self.scale_def if self.scale_def > 0 else 1.0
                
        else: # auto_scale est explicitement False
            # On coupe le mode automatique
            self.auto_scale = False

        # --- 2. GESTION DE L'ÉCHELLE NUMÉRIQUE EN MODE MANUEL ---
        # On n'applique la valeur 'scale' que si le mode automatique n'est pas actif
        if not self.auto_scale:
            if scale is None or scale <= 0:
                self.scale = self.scale_def if self.scale_def > 0 else 1.0
            else:
                self.scale = scale

        # --- 3. DÉLÉGATION À L'ENTONNOIR --- (c'est cette fonction qui va mettre l'affichage à jour)
        self.update_size_entities(True, self.a_entities, self.b_entities)
        
        return self.scale
    def get_scale(self):
        """
        Retourne l'échelle graphique actuelle en [Px/µm], et l'état d'activation de l'échelle automatique
        """
        return {"scale": self.scale, "auto _scale": self.auto_scale, "code_search": self.auto_scale_entities_def}

    # fonction utilisées pour le zoom automatique et le centrage du dessin
    def set_auto_scale_code(self, code_str):
        """
        Modifie la configuration du zoom automatique.
        """
        if not isinstance(code_str, str) or not code_str:
            return

        # 2. Mise à jour de la configuration d'usine par défaut
        self.auto_scale_entities_def = code_str
        self.auto_scale_entities_last = code_str

        # On signale qu'un recalcul d'échelle est requis au prochain battement
        self.recalc_a = self.recalc_b = True
        self.update_size_entities(box_dest=None, a_entities=self.a_entities, b_entities=self.b_entities)
    def get_auto_scale_code(self):
        """
        Retourne un dictionnaire contenant la configuration d'usine 
        et l'intention de zoom automatique actuelle.
        """
        return {
            "default_code": self.auto_scale_entities_def,
            "last_code": self.auto_scale_entities_last
        }

    def search_auto_scale(self, code_entities=None, margin=[0.1, 0.1]):
        """ Gardée pour compatibilité : cherche la bbox puis calcule l'échelle. """
        if isinstance(code_entities, str):
            if code_entities.lower() == "def":
                self.auto_scale_entities_last = self.auto_scale_entities_def
            else:
                self.auto_scale_entities_last = code_entities 
        else: pass
        bbox = self.search_min_max(self.auto_scale_entities_last)
        return self.compute_scale_from_bbox(bbox, margin)
    def compute_scale_from_bbox(self, bbox_um, margin=[0.1, 0.1]):
        """
        SOUS-FONCTION CHIRURGICALE : Calcule l'échelle idéale [Px/µm] 
        à partir d'une bbox déjà connue en mémoire. Évite les doublons de scan.
        """
        if not bbox_um or len(bbox_um) != 2:
            return False

        min_hor, min_vert = bbox_um[0]
        max_hor, max_vert = bbox_um[1]

        # Application des marges en microns [µm]
        delta_hor = (max_hor - min_hor) * (1 + margin[0] * 2)   # Marge en % à appliquer à gauche et à droite
        delta_vert = (max_vert - min_vert) * (1 + margin[1] * 2)
        
        if delta_hor == 0: delta_hor = 1
        if delta_vert == 0: delta_vert = 1

        # Récupération de la taille de la box
        box_width = self.box_dest.size[0] if hasattr(self.box_dest, 'size') else 100
        box_height = self.box_dest.size[1] if hasattr(self.box_dest, 'size') else 100

        scale_z = box_width / delta_hor
        scale_x = box_height / delta_vert

        echelle_ideale = min(scale_z, scale_x)
        return echelle_ideale if echelle_ideale > 0 else False
    def compute_center_from_bbox(self, bbox_um, scale_ref=None, offset_px=[0.0, 0.0]):
        """
        SOUS-FONCTION MAÎTRESSE : Calcule le centre géométrique de la bbox_um
        et retourne un dictionnaire contenant le centre converti en Pixels d'affichage
        et en Microns machine, en intégrant l'offset de glissement manuel [Z, X] futur.
        """
        if not bbox_um or len(bbox_um) != 2:
            return {"en_px": [0.0, 0.0], "en_um": [0.0, 0.0]}

        # 1. Alignement de l'échelle : Priorité à scale_ref s'il est fourni
        local_scale = self.scale if scale_ref is None else scale_ref

        # 2. On trouve le milieu géométrique pur en microns [µm] de la forme
        min_x_kivy, min_y_kivy = bbox_um[0]
        max_x_kivy, max_y_kivy = bbox_um[1]
        micron_x_kivy = (min_x_kivy + max_x_kivy) / 2
        micron_y_kivy = (min_y_kivy + max_y_kivy) / 2

        # 3. ÉQUATION PURE, NEUTRE ET ÉVOLUTIVE (Prête pour les futurs glissements de souris)
        centre_micron_x = micron_x_kivy + (offset_px[0] / local_scale)
        centre_micron_y = micron_y_kivy + (offset_px[1] / local_scale)
        
        centre_pixel_x = (micron_x_kivy * local_scale) + offset_px[0]
        centre_pixel_y = (micron_y_kivy * local_scale) + offset_px[1]

        return {
            "en_px": [centre_pixel_x, centre_pixel_y], 
            "en_um": [centre_micron_x, centre_micron_y]
        }
    
    def get_center_draw(self, codesearch= None):
        """
        Retourne le point centrale du dessin en um et pixel"""
        if not isinstance(codesearch, str):
            codesearch = self.auto_scale_entities_def

        bbox_um = self.search_min_max(codesearch)   #retourne la boîte englobante des entities

        delta_x = (bbox_um[1][0] - bbox_um[0][0]) / 2
        delta_y = (bbox_um[1][1] - bbox_um[0][1]) / 2
        center_um = [bbox_um[0][0] + delta_x, bbox_um[0][1] + delta_y]
        center_px = [center_um[0] * self.scale , center_um[1] * self.scale]

        return {"center_um":center_um, "center_px": center_px}

    def search_min_max(self, codesearch):
        """
        AIGUILLAGE UNIVERSEL : Recherche la Bounding Box globale selon le code fourni.
        Ex: "A + b" -> Liste A entière + Liste B sans lignes de connexion.
        return (en um): [[Xmin, Ymin], [Xmax, Ymax]] (sans adaptation des miroirs)
        """
        if not isinstance(codesearch, str):
            codesearch = self.auto_scale_entities_def
            
        # Logique d'analyse de votre chaîne de caractères
        arg_a = "a" in codesearch.lower()
        arg_b = "b" in codesearch.lower()
        
        # Si la lettre est en MAJUSCULE (A ou B) -> On garde toutes les lignes (connect_line=False)
        # Si la lettre est en minuscule (a ou b) -> On élimine les lignes de connexion (connect_line=True) (ligne[0] et ligne[-1])
        connect_a = False if "A" in codesearch else True
        connect_b = False if "B" in codesearch else True

        val_a = None
        val_b = None

        if arg_a:
            val_a = self._entities_min_max(entities=self.a_entities, connect_line=connect_a)
            
        if arg_b:
            val_b = self._entities_min_max(entities=self.b_entities, connect_line=connect_b)
        
        # --- CONCATÉNATION ET FUSION DES DEUX LISTES (Le verdict final) ---
        if arg_a and arg_b and val_a and val_b:
            return [
                [min(val_a[0][0], val_b[0][0]), min(val_a[0][1], val_b[0][1])], 
                [max(val_a[1][0], val_b[1][0]), max(val_a[1][1], val_b[1][1])]
            ]
        elif arg_a:
            return val_a
        elif arg_b:
            return val_b
        else:
            return False
    def _entities_min_max(self, entities, connect_line=False): 
        """
        MOTEUR : Calcule la Bounding Box d'une unique liste à partir de sa clé 'bbox'.
        Retourne [[min_x, min_y], [max_x, max_y]] en microns [µm].
        """
        min_hor = min_vert = float('inf')
        max_hor = max_vert = float('-inf')

        # Si la liste est vide, on renvoie une boîte neutre à zéro
        if not entities:
            return [[0, 0], [0, 0]]

        # Séparation des lignes de connexion si demandé
        if connect_line:
            core_entities = entities[1:-1] if len(entities) > 2 else entities
        else:
            core_entities = entities

        # Parcours ultra-rapide basé sur les bboxes précalculées
        for e in core_entities:
            if "bbox" in e:
                b = e["bbox"][0]
                c = e["bbox"][1]
                min_hor = min(min_hor, b[0], c[0])
                max_hor = max(max_hor, b[0], c[0])
                min_vert = min(min_vert, b[1], c[1])
                max_vert = max(max_vert, b[1], c[1])
        
        # Sécurité de delta minimum (50 µm) pour éviter l'échelle infinie
        if abs(min_hor - max_hor) < 50 and abs(min_vert - max_vert) < 50:
            max_hor += 25
            min_hor -= 25
            max_vert += 25
            min_vert -= 25

        # On renvoie purement le résultat géométrique !
        return [[min_hor, min_vert], [max_hor, max_vert]]

    # Fonction de préparation du dessin et de dessin
    def precalculer_profils_statiques(self, recalc_a=True, recalc_b=True):
        """
        Calcule et stocke la position absolue de chaque entité en pixels [Px].
        Intègre offset_0 et la rotation de 180° des miroirs au repos.
        """
        # 🔍 DEBUG PRÉCALCUL : On affiche l'environnement spatial à cet instant précis
        #print(f"\n[DEBUG] Starting precalculer_profils_statiques recalc_a: {recalc_a} / recalc_b: {recalc_a}")
        #print(f"\n[DEBUG] Zoom avant recalcul: {self.scale} ")

        # --- Gestion des signes des miroirs (Rotation 180°) + échelle ---
        # Vos variables combinées magiques [Px/µm] (signe inclus !)
        scalex = self.scale * (-1.0 if self.mirror_hor else 1.0)
        scaley = self.scale * (-1.0 if self.mirror_vert else 1.0)

        # Récupération du point d'ancrage 0,0 absolu de l'écran [Px]
        ox = self.offset_0[0]
        oy = self.offset_0[1]

        # --- TRAITEMENT DE LA LISTE A : LE DESSIN (PIÈCE OU OUTIL) ---
        if recalc_a:
            if self.a_entities:
                # La liste contient des formes -> on appelle la sous-fonction
                self.a_segments = self._traiter_liste_segments(self.a_entities, ox, oy, scalex, scaley)
            else:
                # La liste source est vide [] -> on nettoie immédiatement pour éviter les fantômes
                self.a_segments = []

        # --- TRAITEMENT DE LA LISTE B : LA MACHINE (USINAGE) ---
        if recalc_b:
            if self.b_entities:
                # La liste contient des formes -> on appelle la sous-fonction
                self.b_segments = self._traiter_liste_segments(self.b_entities, ox, oy, scalex, scaley)
            else:
                # La liste source est vide [] ou None -> on nettoie immédiatement
                self.b_segments = []
    def _traiter_liste_segments(self, liste_brute, ox, oy, scalex, scaley):
        """
        SOUS-FONCTION SÉCURISÉE : Parcourt une liste d'entités post-traitées en microns [µm]
        et calcule les coordonnées pixels [Px] pour des LIGNES, ARCS et CERCLES.
        Exige STRICTEMENT les formats longs unifiés de l'usine pour garantir l'inspection d'erreurs.
        """
        liste_pixels = []
        
        for entite in liste_brute:
            seg = entite.copy()
            up_ok = False
            ent_type = entite.get("type")
            
            # =================================================================
            # --- CAS 1 : LES LIGNES UNIQUES SÉCURISÉES ("line") ---
            # =================================================================
            if ent_type == "line" and "start" in entite and "end" in entite:
                seg["pixel_start"] = [
                    ox + (entite["start"][0] * scalex), 
                    oy + (entite["start"][1] * scaley)
                ]
                seg["pixel_end"] = [
                    ox + (entite["end"][0] * scalex), 
                    oy + (entite["end"][1] * scaley)
                ]
                up_ok = True

            # =================================================================
            # --- CAS 2 : LES POLYGONES / CORPS DE PLAQUETTES ("mesh") ---
            # =================================================================
            elif ent_type == "mesh" and "vertices" in entite:
                pixels_vertices = []
                for pt in entite["vertices"]:
                    px = ox + (pt[0] * scalex)
                    py = oy + (pt[1] * scaley)
                    pixels_vertices.extend([px, py, 0.0, 0.0])
                
                seg["pixel_vertices"] = pixels_vertices
                up_ok = True

            # =================================================================
            # --- CAS 3 : LES CERCLES ("cercle") ET ARCS DE CERCLE ("arc") ---
            # =================================================================
            elif "center" in entite and "radius" in entite:
                # 🔍 DEBUG PRÉCALCUL : On affiche l'environnement spatial à cet instant précis
                #if ent_type == "cercle":
                #    print(f"\n[DEBUG CADRE] Taille Box Kivy réelle : {self.box_dest.size if hasattr(self.box_dest, 'size') else 'Inconnue'}")
                #    print(f"[DEBUG CADRE] Position Box Kivy réelle : {self.box_dest.pos if hasattr(self.box_dest, 'pos') else 'Inconnue'}")
                #    print(f"[DEBUG ANCRAGE] Origine Écran (ox, oy) : [{ox:.2f}, {oy:.2f}]")
                #    print(f"[DEBUG MICRONS] Cercle Brut reçu -> Centre: {entite['center']} | Rayon: {entite['radius']}")


                cx_px = ox + (entite["center"][0] * scalex)
                cy_px = oy + (entite["center"][1] * scaley)
                r_px = entite["radius"] * self.scale  
                diam_px = r_px * 2
                
                seg["pixel_center"] = [cx_px, cy_px]
                seg["pixel_radius"] = r_px
                seg["pixel_box_pos"] = [cx_px - r_px, cy_px - r_px]
                seg["pixel_box_size"] = [diam_px, diam_px]
                
                # --- SUBTILITÉ A : LE CERCLE COMPLET ---
                if ent_type == "cercle" or ent_type == "round":
                    up_ok = True
                    
                # --- SUBTILITÉ B : L'ARC DE CERCLE PARFAIT ---
                elif ent_type == "arc" and "start" in entite and "end" in entite:
                    #angle_s_brut = self.calculer_angle_kivy(entite["center"], entite["start"])
                    #angle_e_brut = self.calculer_angle_kivy(entite["center"], entite["end"])
                    arc_start = [ox + (entite["start"][0] * scalex), oy + (entite["start"][1] * scaley)]
                    arc_end = [ox + (entite["end"][0] * scalex), oy + (entite["end"][1] * scaley)]
                    angle_s_brut = self.calculer_angle_kivy(seg["pixel_center"], arc_start)
                    angle_e_brut = self.calculer_angle_kivy(seg["pixel_center"], arc_end)
                    
                    sens_horaire = entite.get("cw", True)
                    angle_s_kivy, angle_e_kivy = self.ajuster_angles_tracé(angle_s_brut, angle_e_brut, cw=sens_horaire)
                    
                    seg["pixel_angles"] = [angle_s_kivy, angle_e_kivy]
                    up_ok = True

            # =================================================================
            # 🛡️ VOTRE DOUBLE BARRIÈRE DE SÉCURITÉ INDUSTRIELLE "ERROR"
            # =================================================================
            if not up_ok:
                seg["original_type"] = ent_type
                seg["type"] = "ERROR"
                
                # ALERTE CHIRURGICALE : Votre idée du Else pour débusquer l'intrus
                if ent_type in ["l", "c", "a"]:
                    print(f"🚨 CRITIQUE : Type court '{ent_type}' intercepté ! Il a sauté l'étape du post-traitement de sécurité.")
                else:
                    print(f"⚠️ ATTENTION : Type inconnu ou intraitable reçu : '{ent_type}'. Segment masqué.")
                
            liste_pixels.append(seg)
            
        return liste_pixels

    def calculer_angle_kivy(self, center, pt):
        """
        Calcule l'angle d'un point par rapport à un centre, au format Kivy.
        Rappel : Kivy place le 0° vers le HAUT de l'écran (Axe Y).
        Prend des coordonnées en microns [µm], retourne un angle en degrés [0° - 360°].
        """
        import math
        # Inversion des axes par rapport à la trigo standard pour caler le 0° vers le haut
        dz = pt[0] - center[0]  # Axe horizontal Z
        dx = pt[1] - center[1]  # Axe vertical X
        
        angle = math.degrees(math.atan2(dz, dx))
        return angle % 360.0
    def ajuster_angles_tracé(self, angle_start, angle_end, cw=True):
        """
        Ajuste les angles de départ et de fin pour respecter la contrainte Kivy.
        Rappel : Kivy dessine TOUJOURS dans le sens horaire.
        """
        # RÈGLE CINÉMATIQUE : Si un seul miroir est actif, le sens de rotation s'inverse !
        if self.mirror_hor != self.mirror_vert:
        #if self.mirror_hor == self.mirror_vert:
            cw = not cw

        # Si le tracé réel doit se faire en sens anti-horaire (CCW), 
        # on inverse le départ et la fin pour forcer Kivy à tourner dans le bon sens visuel
        if not cw:
            angle_start, angle_end = angle_end, angle_start
            

        # On garantit que l'angle de fin est géométriquement supérieur à l'angle de départ
        if angle_end < angle_start:
            angle_end += 360.0

        return angle_start, angle_end

    def trigger_redraw(self):
        """
        PINCEAU RAPIDE (60Hz) : Efface le canvas et repeint les profils.
        Gère les couleurs de remplissage globales, la couleur spécifique par segment,
        et injecte l'épaisseur dynamique lue depuis le dictionnaire du segment !
        """
        from kivy.graphics import Color, Line, Ellipse, Mesh

        self.canvas.clear()
        
        # --- GESTION DES SIGNES ET DÉPLACEMENTS MACHINE ---
        mx_move = -1.0 if self.mirror_hor else 1.0
        my_move = -1.0 if self.mirror_vert else 1.0
        move_px = self.offset_move[0] * self.scale * mx_move
        move_py = self.offset_move[1] * self.scale * my_move

        with self.canvas:
            # =================================================================
            # COUCHE 1 : LE PROFIL DE LA MACHINE (En Rouge, en dessous)
            # =================================================================
            if self.b_segments:
                for seg in self.b_segments:
                    # --- 1. LES LIGNES DE CONTOUR (Couleur et épaisseur spécifiques) ---
                    Color(*seg.get("color", self.b_fill_color))  
                    # 🚀 AIGUILLAGE D'ÉPAISSEUR MACHINE : Priorité au segment, repli sur le défaut !
                    epaisseur_b = seg.get("width", self.b_width)

                    # --- 2. LES CONTOURS DE PROFIL (Couleur de trait d'IHM) ---
                    if seg["type"] == "line" and "pixel_start" in seg:
                        if epaisseur_b > 0:
                            px1, py1 = seg["pixel_start"]
                            px2, py2 = seg["pixel_end"]
                            Line(points=[px1 + move_px, py1 + move_py, px2 + move_px, py2 + move_py], width=epaisseur_b)
                            
                    elif seg["type"] == "arc" and "pixel_box_pos" in seg:
                        if epaisseur_b > 0:
                            bx = seg["pixel_box_pos"][0] + move_px
                            by = seg["pixel_box_pos"][1] + move_py
                            bw, bh = seg["pixel_box_size"][0], seg["pixel_box_size"][1]
                            a_start, a_end = seg["pixel_angles"][0], seg["pixel_angles"][1]
                            Line(ellipse=(bx, by, bw, bh, a_start, a_end), width=epaisseur_b)
                    
                    elif seg["type"] == "cercle" and "pixel_center" in seg:
                        if epaisseur_b > 0:
                            cx, cy = seg["pixel_center"][0], seg["pixel_center"][1]
                            Line(circle=(cx + move_px, cy + move_py, seg["pixel_radius"]), width=epaisseur_b)

                    # --- 3. LES FORMES REMPLIES (Couleur globale d'IHM) ---
                    elif seg["type"] == "mesh" and "pixel_vertices" in seg:
                        v_deplaces = seg["pixel_vertices"].copy()
                        for i in range(0, len(v_deplaces), 4):
                            v_deplaces[i] += move_px
                            v_deplaces[i+1] += move_py
                        Mesh(vertices=v_deplaces, indices=list(range(len(v_deplaces) // 4)), mode="triangle_fan")
                    
                    elif seg["type"] == "round" and "pixel_box_pos" in seg:
                        bx = seg["pixel_box_pos"][0] + move_px
                        by = seg["pixel_box_pos"][1] + move_py
                        bw, bh = seg["pixel_box_size"][0], seg["pixel_box_size"][1]
                        Ellipse(pos=(bx, by), size=(bw, bh))

            # =================================================================
            # COUCHE 2 : LE PROFIL DE LA PIÈCE (En Vert, au-dessus)
            # =================================================================
            if self.a_segments:
                for seg in self.a_segments:
                    # --- 1. LES LIGNES DE CONTOUR (Couleur et épaisseur spécifiques) ---
                    Color(*seg.get("color", self.a_fill_color))
                    # 🚀 AIGUILLAGE D'ÉPAISSEUR PIÈCE : Priorité au segment, repli sur le défaut !
                    epaisseur_a = seg.get("width", self.a_width)

                    # --- 2. LES CONTOURS DE PROFIL
                    if seg["type"] == "line" and "pixel_start" in seg:
                        if epaisseur_a > 0:
                            px1, py1 = seg["pixel_start"][0], seg["pixel_start"][1]
                            px2, py2 = seg["pixel_end"][0], seg["pixel_end"][1]
                            Line(points=[px1 + move_px, py1 + move_py, px2 + move_px, py2 + move_py], width=epaisseur_a)
                            
                    elif seg["type"] == "arc" and "pixel_box_pos" in seg:
                        if epaisseur_a > 0:
                            bx = seg["pixel_box_pos"][0] + move_px
                            by = seg["pixel_box_pos"][1] + move_py
                            bw, bh = seg["pixel_box_size"][0], seg["pixel_box_size"][1]
                            a_start, a_end = seg["pixel_angles"][0], seg["pixel_angles"][1]
                            Line(ellipse=(bx, by, bw, bh, a_start, a_end), width=epaisseur_a)
                    
                    elif seg["type"] == "cercle" and "pixel_center" in seg:
                        if epaisseur_a > 0:
                            cx, cy = seg["pixel_center"][0], seg["pixel_center"][1]
                            Line(circle=(cx + move_px, cy + move_py, seg["pixel_radius"]), width=epaisseur_a)

                    # --- 3. LES FORMES REMPLIES ---
                    elif seg["type"] == "mesh" and "pixel_vertices" in seg:
                        v_deplaces = seg["pixel_vertices"].copy()
                        for i in range(0, len(v_deplaces), 4):
                            v_deplaces[i] += move_px
                            v_deplaces[i+1] += move_py
                        Mesh(vertices=v_deplaces, indices=list(range(len(v_deplaces) // 4)), mode="triangle_fan")
                    
                    elif seg["type"] == "round" and "pixel_box_pos" in seg:
                        bx = seg["pixel_box_pos"][0] + move_px
                        by = seg["pixel_box_pos"][1] + move_py
                        bw, bh = seg["pixel_box_size"][0], seg["pixel_box_size"][1]
                        Ellipse(pos=(bx, by), size=(bw, bh))


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
    end = ListProperty([100, 0])
    dash_pattern = ListProperty([dp(20), dp(10)])  # Long, espace, etc.
    dash_spacing = NumericProperty(dp(10))
    line_width = NumericProperty(dp(10))
    line_color = ListProperty([1, 0.2, 0.2, 1])  # Gris

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._pos_to_box = [0,0]   #initialisation de la vaviable (màj dans _redraw())

        #self._redraw()

    def on_kv_post(self, base_widget):
        """
        🎯 SÉCURITÉ KIVY : Déclenché automatiquement dès que l'IHM et le fichier .kv 
        sont entièrement chargés et liés. C'est le moment idéal pour le premier dessin.
        """
        self._redraw()        

    def _redraw(self, *args):
        self._pos_to_box = self.get_relative_pos()
        self._redraw_pos()
    def drawing_to_possize(self, pos=[0,0], size=[0,0]):
        self._pos_to_box = pos
        self.start = [0,0]
        self.end = size
        self.line_width = dp(10)
        self.line_color = [1, 0.2, 0.2, 1]  # Gris
        self._redraw_pos()
    def redraw_pos(self, start, end):
        """
        🎯 LE COMPAGNON IDÉAL À 60Hz :
        Met à jour uniquement les points de coordonnées sans toucher au conteneur,
        puis repeint instantanément la ligne d'axe.
        """
        self.start = start
        self.end = end
        self._redraw_pos()

    def _redraw_pos(self):
        self.canvas.clear()
        
        # Récupération des coordonnées réelles à l'écran
        x1 = self.start[0] + self._pos_to_box[0]
        y1 = self.start[1] + self._pos_to_box[1]
        x2 = self.end[0] + self._pos_to_box[0]
        y2 = self.end[1] + self._pos_to_box[1]

        dx = x2 - x1
        dy = y2 - y1
        dist = (dx**2 + dy**2) ** 0.5
        if dist <= 0:
            return

        # Vecteurs directeurs unitaires
        dir_x = dx / dist
        dir_y = dy / dist

        # Extraction des paramètres
        long_dash = self.dash_pattern[0]
        short_dash = self.dash_pattern[1] if len(self.dash_pattern) > 1 else long_dash
        space = self.dash_spacing

        # Un bloc complet "Trait d'axe" équivaut à : Long + Espace + Court + Espace
        block_len = long_dash + space + short_dash + space

        # On veut que la ligne commence ET se termine par un trait long (Esthétique industrielle)
        # Distance restante à combler après le premier et le dernier trait long obligatoire
        disponibilite = dist - long_dash
        
        if disponibilite <= 0:
            # Si la ligne est plus courte qu'un seul trait long, on dessine une ligne continue
            with self.canvas:
                Color(*self.line_color)
                Line(points=[x1, y1, x2, y2], width=self.line_width)
            return

        # Calcul du nombre de blocs complets [Espace + Court + Espace + Long] imbriquables
        nb_blocs = int(disponibilite // block_len)
        
        # S'il n'y a pas assez de place pour un bloc complet, on force au moins 1 pour le style
        if nb_blocs == 0:
            nb_blocs = 1

        # Calcul du coefficient d'ajustement (scale) pour étirer/ajuster parfaitement le motif à la longueur
        longueur_theorique = long_dash + (nb_blocs * block_len)
        scale = dist / longueur_theorique

        # Application du coefficient d'échelle aux dimensions de dessin
        s_long = long_dash * scale
        s_short = short_dash * scale
        s_space = space * scale

        # Initialisation du curseur de parcours de la ligne
        current_dist = 0

        with self.canvas:
            Color(*self.line_color)

            # 1. Premier Trait Long
            x_s = x1 + current_dist * dir_x
            y_s = y1 + current_dist * dir_y
            current_dist += s_long
            x_e = x1 + current_dist * dir_x
            y_e = y1 + current_dist * dir_y
            Line(points=[x_s, y_s, x_e, y_e], width=self.line_width)

            # 2. Boucle de répétition des blocs d'alternance
            for _ in range(nb_blocs):
                # Saut de l'espace
                current_dist += s_space

                # Trait Court
                x_s = x1 + current_dist * dir_x
                y_s = y1 + current_dist * dir_y
                current_dist += s_short
                x_e = x1 + current_dist * dir_x
                y_e = y1 + current_dist * dir_y
                Line(points=[x_s, y_s, x_e, y_e], width=self.line_width)

                # Saut de l'espace
                current_dist += s_space

                # Trait Long
                x_s = x1 + current_dist * dir_x
                y_s = y1 + current_dist * dir_y
                current_dist += s_long
                x_e = x1 + current_dist * dir_x
                y_e = y1 + current_dist * dir_y
                Line(points=[x_s, y_s, x_e, y_e], width=self.line_width)

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

class BboxShowWidget(Widget):
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
    start = ListProperty([-2, -2])
    end = ListProperty([2, 2])
    line_width = NumericProperty(dp(10))
    line_color = ListProperty([0.2, 0.4, 0.2, 1])  # Gris

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._pos_to_box = [0,0]   #initialisation de la vaviable (màj dans _redraw())

        #self._redraw()

    def on_kv_post(self, base_widget):
        """
        🎯 SÉCURITÉ KIVY : Déclenché automatiquement dès que l'IHM et le fichier .kv 
        sont entièrement chargés et liés. C'est le moment idéal pour le premier dessin.
        """
        self._redraw()        

    def _redraw(self, *args):
        self._pos_to_box = self.get_relative_pos()
        self._redraw_pos()
    def drawing_to_possize(self, pos=[0,0], size=[0,0]):
        self._pos_to_box = pos
        self.start = [0,0]
        self.end = size
        self.line_width = dp(3)
        self.line_color = [1, 0.2, 0.2, 1]  # Gris
        self._redraw_pos()

    def redraw_bbox(self, bbox):
        """
        🎯 LE COMPAGNON IDÉAL À 60Hz :
        Met à jour uniquement les points de coordonnées sans toucher au conteneur,
        puis repeint instantanément la ligne d'axe.
        """
        if bbox and len(bbox) == 2:
            self.start = bbox[0]
            self.end = bbox[1]
        else:
            self.start = []
            self.end = []
        self._redraw_pos()

    def _redraw_pos(self):
        self.canvas.clear()

        if len(self.start) == 2 and len(self.end) == 2:
            with self.canvas:
                Color(*self.line_color)
                Line(rectangle=(self.start[0], self.start[1], self.end[0]-self.start[0], self.end[1]-self.start[1]), width=self.line_width)
            return
        else:
            return

        ##########################################################################################
        # OLD ################################### OLD ###################################### OLD #            
        
        # Récupération des coordonnées réelles à l'écran
        x1 = self.start[0] + self._pos_to_box[0]
        y1 = self.start[1] + self._pos_to_box[1]
        x2 = self.end[0] + self._pos_to_box[0]
        y2 = self.end[1] + self._pos_to_box[1]

        dx = x2 - x1
        dy = y2 - y1
        dist = (dx**2 + dy**2) ** 0.5
        if dist <= 0:
            return

        # Vecteurs directeurs unitaires
        dir_x = dx / dist
        dir_y = dy / dist

        # Extraction des paramètres
        long_dash = self.dash_pattern[0]
        short_dash = self.dash_pattern[1] if len(self.dash_pattern) > 1 else long_dash
        space = self.dash_spacing

        # Un bloc complet "Trait d'axe" équivaut à : Long + Espace + Court + Espace
        block_len = long_dash + space + short_dash + space

        # On veut que la ligne commence ET se termine par un trait long (Esthétique industrielle)
        # Distance restante à combler après le premier et le dernier trait long obligatoire
        disponibilite = dist - long_dash
        
        if disponibilite <= 0:
            # Si la ligne est plus courte qu'un seul trait long, on dessine une ligne continue
            with self.canvas:
                Color(*self.line_color)
                Line(points=[x1, y1, x2, y2], width=self.line_width)
            return

        # Calcul du nombre de blocs complets [Espace + Court + Espace + Long] imbriquables
        nb_blocs = int(disponibilite // block_len)
        
        # S'il n'y a pas assez de place pour un bloc complet, on force au moins 1 pour le style
        if nb_blocs == 0:
            nb_blocs = 1

        # Calcul du coefficient d'ajustement (scale) pour étirer/ajuster parfaitement le motif à la longueur
        longueur_theorique = long_dash + (nb_blocs * block_len)
        scale = dist / longueur_theorique

        # Application du coefficient d'échelle aux dimensions de dessin
        s_long = long_dash * scale
        s_short = short_dash * scale
        s_space = space * scale

        # Initialisation du curseur de parcours de la ligne
        current_dist = 0

        with self.canvas:
            Color(*self.line_color)

            # 1. Premier Trait Long
            x_s = x1 + current_dist * dir_x
            y_s = y1 + current_dist * dir_y
            current_dist += s_long
            x_e = x1 + current_dist * dir_x
            y_e = y1 + current_dist * dir_y
            Line(points=[x_s, y_s, x_e, y_e], width=self.line_width)

            # 2. Boucle de répétition des blocs d'alternance
            for _ in range(nb_blocs):
                # Saut de l'espace
                current_dist += s_space

                # Trait Court
                x_s = x1 + current_dist * dir_x
                y_s = y1 + current_dist * dir_y
                current_dist += s_short
                x_e = x1 + current_dist * dir_x
                y_e = y1 + current_dist * dir_y
                Line(points=[x_s, y_s, x_e, y_e], width=self.line_width)

                # Saut de l'espace
                current_dist += s_space

                # Trait Long
                x_s = x1 + current_dist * dir_x
                y_s = y1 + current_dist * dir_y
                current_dist += s_long
                x_e = x1 + current_dist * dir_x
                y_e = y1 + current_dist * dir_y
                Line(points=[x_s, y_s, x_e, y_e], width=self.line_width)

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
    #print(f" point_base:{pnt_base} , point_in:{pnt_in}")

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

def create_drawing_mesh(arcs_net):
    '''Créateur de forme pleinne (par ex pour l'inserte du burin)
    Arg: une liste de dict (d'arc ou de points) sous cette forme
        # Pour les arcs:   {"type": "arc", "center": [x,y], "start": [x,y], "end": [x,y], "radius": rayon}
        # Pour les points: {"type": "None","center": [x,y], "radius": 0}
    Return: une liste de dict contenent un mesh ET pour les arcs (congés) des rounds.
    '''
    segments_insert = []
    mesh_point = []
    
    for i, arc in enumerate(arcs_net):
        if arc is None:
            continue

        c_trans = arc["center"]
        if arc["type"] == "arc":
            s_trans = arc["start"]
            e_trans = arc["end"]
            
            segments_insert.append(creat_entry_round(c_trans, arc["radius"]))
            mesh_point.extend([s_trans, e_trans])
        else:
            # Si type == "None", c_trans contient en fait la coordonnée du point d'arête brute
            mesh_point.extend([c_trans])
        
    segments_insert.append({"type": "mesh", "vertices": mesh_point})
    return segments_insert

# Ebauche pour trajectoire d'outil
def OLD_arc_vecteur(point_before, point_intersect, point_after, r_piece, offset_target, r_bec_burin, dict_formated_auto=True):
    """
    🖥️ COMPOSANT FAO - GENERATEUR D'ARC-VECTEUR (Version 1.1 - Correction r < 0)
    Calcule la projection brute et pure d'un sommet, y compris les rayons négatifs.
    """
    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]

    def normalize_vector(p1, p2):
        vx, vy = p2[0] - p1[0], p2[1] - p1[1]
        l = math.hypot(vx, vy)
        return [vx / l, vy / l] if l > 1e-6 else None

    # 1. Directions originales (Vecteurs unitaires de la liste brute)
    n_ba = normalize_vector(point_before, point_intersect)
    n_bc = normalize_vector(point_after, point_intersect)

    if n_ba is None or n_bc is None:
        return {"arc": None, "v_in": n_ba, "v_out": n_bc, "error": True}

    # 2. Détermination de la concavité d'origine (Profil toujours horaire)
    is_convex = cross(n_ba, n_bc) > 0  
    
    # Valeur totale du décalage (Rayon de bec + surépaisseur)
    total_offset = r_bec_burin + offset_target
    
    # 3. Calcul du rayon théorique exact (sans garde-fou pour l'instant)
    if is_convex:
        r_final = r_piece + total_offset
        cw_final = True
    else:
        r_final = r_piece - total_offset
        cw_final = False

    # 4. Axe médian (Bissectrice normalisée du sommet brut)
    bis_x = n_ba[0] + n_bc[0]
    bis_y = n_ba[1] + n_bc[1]
    l_bis = math.hypot(bis_x, bis_y)
    
    if l_bis < 1e-6:
        return {"arc": None, "v_in": n_ba, "v_out": n_bc, "error": True}
    n_b_ce = [bis_x / l_bis, bis_y / l_bis]

    # 5. Vecteurs perpendiculaires de tangence (Ce -> Points de tangence)
    # C'est ici qu'on applique la règle géométrique pure
    if is_convex:
        n_ce_a = [-n_ba[1], n_ba[0]]
        n_ce_c = [n_bc[1], -n_bc[0]]
    else:
        n_ce_a = [n_ba[1], -n_ba[0]]
        n_ce_c = [-n_bc[1], n_bc[0]]

    # Rapport de projection sur la diagonale (Produit scalaire)
    dot_proj = abs(n_b_ce[0] * n_ce_a[0] + n_b_ce[1] * n_ce_a[1])
    if dot_proj < 1e-6:
        return {"arc": None, "v_in": n_ba, "v_out": n_bc, "error": True}

    # 🎯 LA RÉPARATION CHIRURGICALE DU RAYON NÉGATIF :
    # On utilise la valeur absolue pour la distance géométrique de la bissectrice 'd'
    # mais le SHT (le signe du rayon) va piloter l'inversion des vecteurs de tangence !
    d = abs(r_final) / dot_proj

    # Position du Centre théorique (Le centre d'origine de la pièce reste la référence)
    Ce = [point_intersect[0] + n_b_ce[0] * d, point_intersect[1] + n_b_ce[1] * d]

    # Calcul des vecteurs de rayon (Ce -> Start / Ce -> End)
    # Si r_final < 0, l'inversion mathématique se fait ici : les points repartent en arrière !
    v_ce_a = [n_ce_a[0] * r_final, n_ce_a[1] * r_final]
    v_ce_c = [n_ce_c[0] * r_final, n_ce_c[1] * r_final]

    # Points de tangence bruts déplacés
    start = [Ce[0] - v_ce_a[0], Ce[1] - v_ce_a[1]]
    end = [Ce[0] - v_ce_c[0], Ce[1] - v_ce_c[1]]

    def rpt(p, digits=3):
        return [round(p[0], digits), round(p[1], digits)]

    arc_data = {
        "type": "a" if dict_formated_auto else "arc",
        "start": rpt(start),
        "end": rpt(end),
        "center": rpt(Ce),
        "radius": r_final, # Conserve la valeur négative pour informer la fonction 4 points
        "dir" if dict_formated_auto else "cw": cw_final
    }

    return {
        "arc": arc_data,
        "v_in": n_ba,
        "v_out": n_bc,
        "error": False
    }
def OLD_raccordement_4_points(p1, p2, p3, p4, r_tool, dict_formated_auto=True):
    """
    🖥️ UNIFICATEUR DE PARCOURS MCU (Version 2.2 - Support Rayon 0)
    Prend 2 segments déjà décalés à leur vraie place (P1->P2 et P3->P4).
    Calcule le raccordement idéal, accepte r_tool = 0.0 pour les finitions à angle vif.
    """
    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]

    def normalize(pA, pB):
        vx, vy = pB[0] - pA[0], pB[1] - pA[1]
        l = math.hypot(vx, vy)
        return [vx / l, vy / l] if l > 1e-6 else None

    # 1. Vecteurs directeurs des lignes d'offset réelles
    u1 = normalize(p1, p2)
    u2 = normalize(p3, p4)

    if u1 is None or u2 is None:
        return {"arc": None, "error": True, "msg": "Segment vide"}

    # 2. Recherche de l'intersection virtuelle de nos deux droites décalées
    # Droite 1: a1*x + b1*y = c1
    a1, b1 = u1[1], -u1[0]
    c1 = a1 * p2[0] + b1 * p2[1]

    # Droite 2: a2*x + b2*y = c2
    a2, b2 = u2[1], -u2[0]
    c2 = a2 * p3[0] + b2 * p3[1]

    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-6:
        return {"arc": None, "error": True, "msg": "Segments parallèles"}

    # Point d'intersection réel des trajectoires du centre de l'outil
    S_inter = [(c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det]

    # 3. Détermination de la concavité (Profil horaire)
    is_convex = cross(u1, u2) > 0
    cw_final = True if is_convex else False

    def rpt(p, digits=3):
        return [round(p[0], digits), round(p[1], digits)]

    # 🎯 LE CAS MAGIQUE DU RAYON ZÉRO (Finition pure)
    # Si le rayon demandé est nul, l'arc s'effondre en un point d'angle vif unique
    if abs(r_tool) < 1e-6:
        arc_data = {
            "type": "a" if dict_formated_auto else "arc",
            "start": rpt(S_inter),
            "end": rpt(S_inter),
            "center": rpt(S_inter),
            "radius": 0.0,
            "dir" if dict_formated_auto else "cw": cw_final
        }
        return arc_data

    # 4. Calcul classique avec bissectrice si r_tool > 0 (Ébauche ou arrondi)
    v_in = [-u1[0], -u1[1]]
    v_out = [u2[0], u2[1]]

    bis_x = v_in[0] + v_out[0]
    bis_y = v_in[1] + v_out[1]
    l_bis = math.hypot(bis_x, bis_y)

    if l_bis < 1e-6:
        return {"arc": None, "error": True, "msg": "Segments opposés"}

    n_b_ce = [bis_x / l_bis, bis_y / l_bis]

    if is_convex:
        n_ce_a = [-u1[1], u1[0]]
    else:
        n_ce_a = [u1[1], -u1[0]]

    dot_proj = abs(n_b_ce[0] * n_ce_a[0] + n_b_ce[1] * n_ce_a[1])
    d_bis = r_tool / dot_proj

    # Position du centre de l'outil
    Ce = [S_inter[0] + n_b_ce[0] * d_bis, S_inter[1] + n_b_ce[1] * d_bis]

    # Points de tangence réels ajustés
    if is_convex:
        start = [Ce[0] + u1[1] * r_tool, Ce[1] - u1[0] * r_tool]
        end = [Ce[0] + u2[1] * r_tool, Ce[1] - u2[0] * r_tool]
    else:
        start = [Ce[0] - u1[1] * r_tool, Ce[1] + u1[0] * r_tool]
        end = [Ce[0] - u2[1] * r_tool, Ce[1] + u2[0] * r_tool]

    arc_data = {
        "type": "a" if dict_formated_auto else "arc",
        "start": rpt(start),
        "end": rpt(end),
        "center": rpt(Ce),
        "radius": round(r_tool, 3),
        "dir" if dict_formated_auto else "cw": cw_final
    }

    return arc_data

def calculer_sommet_mcu(point_before, point_intersect, point_after, r_piece, offset_target, r_bec_burin, r_mini_trajectoire=0.0, dict_formated_auto=True):
    """
    🖥️ NOYAU FAO UNIFIÉ (Version 3.0 - Sommet Unique)
    Fusionne la projection brute et le raccordement de sécurité.
    Prend un sommet brut et retourne l'entité de transition outil parfaite (Arc ou Angle vif).
    """
    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]

    def normalize_vector(p1, p2):
        vx, vy = p2[0] - p1[0], p2[1] - p1[1]
        l = math.hypot(vx, vy)
        return [vx / l, vy / l] if l > 1e-6 else None

    # 1. Extraction des directions pures de la liste brute
    n_ba = normalize_vector(point_before, point_intersect)  # Vecteur entrant
    n_bc = normalize_vector(point_after, point_intersect)   # Vecteur sortant

    if n_ba is None or n_bc is None:
        return {"type": "L", "end": point_intersect, "error": True}

    # 2. Détermination de la concavité (Profil horaire : cross > 0 Convexe / cross < 0 Concave)
    is_convex = cross(n_ba, n_bc) > 0  
    
    # Équation d'offset brute (Rayon outil + Surépaisseur d'usinage)
    total_offset = r_bec_burin + offset_target
    
    if is_convex:
        r_final = r_piece + total_offset
        cw_final = True
    else:
        r_final = r_piece - total_offset
        cw_final = False

    # 3. Axe médian du sommet (Bissectrice normalisée)
    bis_x = n_ba[0] + n_bc[0]
    bis_y = n_ba[1] + n_bc[1]
    l_bis = math.hypot(bis_x, bis_y)
    
    if l_bis < 1e-6:
        return {"type": "L", "end": point_intersect, "error": True}
    n_b_ce = [bis_x / l_bis, bis_y / l_bis]

    # 4. Vecteurs normaux de tangence (Ce -> Profil)
    if is_convex:
        n_ce_a = [-n_ba[1], n_ba[0]]
        n_ce_c = [n_bc[1], -n_bc[0]]
    else:
        n_ce_a = [n_ba[1], -n_ba[0]]
        n_ce_c = [-n_bc[1], n_bc[0]]

    # Rapport de projection sur la diagonale (Produit scalaire)
    dot_proj = abs(n_b_ce[0] * n_ce_a[0] + n_b_ce[1] * n_ce_a[1])
    if dot_proj < 1e-6:
        return {"type": "L", "end": point_intersect, "error": True}

    # 🎯 LE FILTRE UNIFIÉ D'ATELIER (Gestion r < r_mini ou négatif)
    # r_mini_trajectoire peut être configuré à 0.0 pour les finitions à angles vifs
    if r_final < r_mini_trajectoire:
        r_final = max(0.0, r_mini_trajectoire)
        cw_final = True if is_convex else False  # Conserve son sens machine initial

    def rpt(p, digits=3):
        return [round(p[0], digits), round(p[1], digits)]

    # 🎯 CAS MAGIQUE : ANGLE VIF POUR LES MOTEURS (Finition pure à 0 µm)
    if r_final < 1e-6:
        # Si le rayon de trajectoire est nul, toutes les lignes de centres convergent.
        # Le point d'intersection réel de tes droites décalées se calcule via la bissectrice à d=0
        # par rapport aux parallèles théoriques. Plus simplement : c'est le point d'angle vif décalé.
        # Pour le trouver sans faire de système linéaire, on utilise la projection de l'offset total sur la bissectrice :
        d_vif = total_offset / dot_proj
        if not is_convex:
            S_inter = [point_intersect[0] - n_b_ce[0] * d_vif, point_intersect[1] - n_b_ce[1] * d_vif]
        else:
            S_inter = [point_intersect[0] + n_b_ce[0] * d_vif, point_intersect[1] + n_b_ce[1] * d_vif]

        return {
            "type": "a" if dict_formated_auto else "arc",
            "start": rpt(S_inter),
            "end": rpt(S_inter),
            "center": rpt(S_inter),
            "radius": 0.0,
            "dir" if dict_formated_auto else "cw": cw_final,
            "v_out": n_bc
        }

    # 5. CAS CLASSIQUE : CALCUL DE L'ARC DE RAYON R > 0 (Ébauche ou congés préservés)
    d = abs(r_final) / dot_proj

    # Positionnement géométrique du centre outil
    # Si le rayon brut était négatif, l'outil s'est inversé, le centre s'ajuste
    if not is_convex:
        Ce = [point_intersect[0] - n_b_ce[0] * d, point_intersect[1] - n_b_ce[1] * d]
    else:
        Ce = [point_intersect[0] + n_b_ce[0] * d, point_intersect[1] + n_b_ce[1] * d]

    # Calcul des points de tangence réels (Trim automatique)
    start = [Ce[0] - n_ce_a[0] * r_final, Ce[1] - n_ce_a[1] * r_final]
    end = [Ce[0] - n_ce_c[0] * r_final, Ce[1] - n_ce_c[1] * r_final]

    return {
        "type": "a" if dict_formated_auto else "arc",
        "start": rpt(start),
        "end": rpt(end),
        "center": rpt(Ce),
        "radius": round(abs(r_final), 3),
        "dir" if dict_formated_auto else "cw": cw_final,
        "v_out": n_bc  # On exporte le vecteur sortant pour la fonction globale de chaînage
    }


# Mise en forme des segments pour ProfilCanvas()
def re_paint_entities(raw_list, draw_type="profil", liaison_line=None, liaison_color=None):
    """
    🎯 LE PISTOLET À PEINTURE DRO EVOLUÉ : 
    Reçoit une liste d'entités et un 'draw_type' (ex: 'profil_cao', 'detail', 'liaison').
    Va chercher automatiquement la couleur et l'épaisseur associées dans draw_line.
    Gère aussi automatiquement la version "erreur" si un problème est détecté sur l'entité.
    Liaison line et color sont pour définir des lignes aditionnel de couleur différante à chaque
    extrémitée du profil. [liaison_line] comporte None ou le nombre de segments de chaque extrémitée
    à colorier différament. (par ex: les lignes de liaison pour le détail d'un Shape, ou
    les barrières d'usinage pour un profil ouvert)
    """
    entities = []
    barriere_nbr = liaison_line if liaison_line else 0

    # 🔍 1. Récupération dynamique du style nominal depuis votre dictionnaire
    # on le récupère avant de potentiellement prendre le type par défaut
    fill_type = f"{draw_type}_fill" 
    error_type = f"erreur_{draw_type}"

    # 🔍 2. Récupération dynamique du style associé
    if draw_type not in th_drl:    # Si le type demandé n'existe pas, on bascule par sécurité sur "profil"
        draw_type = "profil"  
    nominal_color_hex = th_drl[draw_type]
    nominal_width = th_drl.get(f"{draw_type}_w", 2)

    if error_type not in th_drl: error_type = "erreur_profil"        
    error_color_hex = th_drl.get(error_type, "#ff0055")
    error_width = th_drl.get(f"{error_type}_w", 4)

    if not liaison_color: liaison_color= th_drl.get("liaison", "#ff0055")
    barriere_width =  th_drl.get("liaison_w", 1)

    # 🔍 3. Récupération dynamique du style de remplissage associé
    # Si la variante de remplissage spécifique n'existe pas, on cherche "profil_fill", ou  on prend une couleur par défaut
    #print(f"DEBUG Construction de fill color, fill_type: {fill_type}")
    
    if fill_type not in th_drl: fill_type = "profil_fill"    
    fill_color_hex = th_drl.get(fill_type, "#ff0055")

    # Convertir immédiatement en RGBA Kivy pour optimiser la boucle
    nominal_color = normalize_color(nominal_color_hex)
    error_color = normalize_color(error_color_hex)
    barriere_color = normalize_color(liaison_color)
    fill_color = normalize_color(fill_color_hex)

    # 🔄 4. Traitement de la liste d'entités
    working_list = raw_list
    rawmax = len(raw_list)-1
    last_is_error = False

    for idx, raw in enumerate(working_list):
        seg = raw.copy()
        
        ent_type = raw.get("type")
        if not ent_type:
            continue

        # Sauvegarde de la couleur d'origine par sécurité
        #TODO: devrait pouvoir être supprimé avec l'utilisation de cette fonction de coloriage !
        seg["origin_color"] = raw.get("color", nominal_color)

        # 🚨 Détection des erreurs
        is_error = False
        # 🎨 Application de la couleur erreur au segment suivant une erreur
        if last_is_error:       # Le segment précédant comporte une erreur
            is_error = True     # Appliquer la couleur d'erreur à ce segment
            last_is_error = False

        if "error" in raw and raw["error"]:
            is_error = True     # Appliquer la couleur d'erreur à ce segment
            last_is_error = True     # tourne le flag pour la boucle suivante
            #Ici il faut colorier en erreur le segment précédent
            if idx > 0:
                entities[-1]["color"] = error_color
                entities[-1]["width"] = error_width

        # 🎨 Application de la charte graphique 🎯 DISTINCTION INDUSTRIELLE : Remplissage vs Contour
        if ent_type in ["mesh", "round"]:
            seg["color"] = fill_color
            seg["width"] = 0  # Pas d'épaisseur de ligne pour une forme pleine
        else:
            if is_error:
                seg["color"] = error_color
                seg["width"] = error_width
            elif idx < barriere_nbr or idx > rawmax - barriere_nbr:
                    seg["color"] = barriere_color
                    seg["width"] = barriere_width
            else:
                    seg["color"] = nominal_color
                    seg["width"] = nominal_width

        entities.append(seg)

    return entities

def create_entities_from_raw(raw_list, id_pnt=None, add_cpt_error=False):
    """
    🎯 GÉOMÈTRE PUR (ZÉRO COULEURS) :
    Calcule les Bbox et détecte mathématiquement les inversions de marche.
    Si une anomalie est trouvée, injecte simplement "error": True.
    """
    entities = []
    raw = None
    last_end = None
    error_cpt = 0

    # Recherche du premier point de départ
    for _raw in raw_list:
        if "start" in _raw:
            last_end = _raw["start"]
            break

    def compute_raw(idx_raw):
        nonlocal raw, last_end, id_pnt, error_cpt
        ent_type = raw["type"]
        
        # Un simple drapeau local pour ce segment
        is_segment_error = False
        entry_loop = None  
        ident = raw.get("id_pnt", id_pnt)

        # Si le dictionnaire brut contient déjà une erreur (ex: saisie aberrante)
        if raw.get("error", False):
            is_segment_error = True
            error_cpt += 1

        # --- CAS L : Ligne de connexion dépendante ---
        if ent_type == "l":     
            ref_point = None    
            start, end = raw["start"], raw["end"]
            for _raw in raw_list[idx_raw + 1:]:
                if "start" in _raw:
                    ref_point = _raw["start"]
                    break
            next_start = ref_point or end

            if next_start is not None:
                dx1, dy1 = end[0] - start[0], end[1] - start[1]
                dx2, dy2 = next_start[0] - last_end[0], next_start[1] - last_end[1]
                dot_product = dx1 * dx2 + dy1 * dy2
                
                # Tolérance flottante sur l'inversion
                if dot_product < -0.001:
                    is_segment_error = True
                    error_cpt += 1

                # On passe None pour la couleur, re_paint s'en chargera
                entry_loop = creat_entry_line(last_end, next_start, id_pnt=ident)

        # --- CAS D : Droite autonome ---
        elif ent_type == "d":        
            start, end = raw["start"], raw["end"]
            if start != end:
                dx1, dy1 = raw["end"][0] - raw["start"][0], raw["end"][1] - raw["start"][1]
                dx2, dy2 = raw["vec_dir"]
                dot_product = dx1 * dx2 + dy1 * dy2
                
                if dot_product < -0.001:
                    is_segment_error = True
                    error_cpt += 1

                entry_loop = creat_entry_line(start, end, id_pnt=ident)

        # --- CAS A : Arc de cercle ---
        elif ent_type == "a":        
            start, end = raw["start"], raw["end"]
            center, radius, cw = raw["center"], raw["radius"], raw["dir"]
            
            if radius != 0:
                entry_loop = creat_entry_arc(start, end, center, radius, cw, id_pnt=ident)
            else:
                end = last_end  
                if not cw:
                    is_segment_error = True

        # --- CAS C, R, M (Identiques, sans passer de couleurs...) ---
        elif ent_type == "c":
            entry_loop = creat_entry_circle(raw["center"], raw["radius"], id_pnt=ident)
            end = last_end
        elif ent_type == "r":
            entry_loop = creat_entry_circle(raw["center"], raw["radius"], id_pnt=ident)
            entry_loop["type"] = "rond"
            end = last_end
        elif ent_type == "m":
            entry_loop = {"type": "mesh", "vertices": raw["vertices"], "id_pnt": ident}
            end = last_end

        # INJECTION DU BOOLÉEN ET AJOUT
        if entry_loop is not None:
            entry_loop["error"] = is_segment_error
            entities.append(entry_loop)

        return end if entry_loop is not None else last_end

    # Boucle linéaire
    for idx in range(len(raw_list)):
        raw = raw_list[idx]
        last_end = compute_raw(idx)

    # Retourne:
    if add_cpt_error:
        return (entities, error_cpt)
    
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
        # 🎯 SÉCURISATION DU VECTEUR DIRECTEUR AU DÉPAQUETAGE
        # 1. On tente d'aller récupérer le vecteur directeur d'origine s'il était stocké
        # 2. Si l'entité n'en avait pas (ligne standard), on calcule son vecteur à la volée [dx, dy]
        #vec_dir = entity.get("vec_dir", [entity["end"][0] - entity["start"][0], entity["end"][1] - entity["start"][1]])
        start = entity["end"] if reverse else entity["start"]
        end = entity["start"] if reverse else entity["end"]
        vec_dir = [end[0] - start[0], end[1] - start[1]]

        return {
            "type": "d",
            "start": start,
            "end": end,
            "color": color,
            "id_pnt": id_pnt,
            #"error": error,
            "vec_dir": vec_dir  # 🌟 Ré-injection de la clé magique pour éliminer le KeyError !
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
            #"error": error
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

def transformer_geometrie_insert(points_kivy, lead_angle_deg, invert=False):
    """
    🎯 LE PIVOT GÉOMÉTRIQUE :
    Prend les points d'un insert au format [[hor, vert], r] en microns.
    Applique l'inversion visuelle (miroir sur l'axe horizontal) et la rotation du lead_angle.
    Tout pivote autour du centre du bec (0,0).
    """
    points_transformes = []
    angle_rad = math.radians(lead_angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    for pt in points_kivy:
        # Extraction de la structure CAO imbriquée
        hor, vert = pt[0][0], pt[0][1]
        rayon = pt[1]

        # 1. 🔄 L'inversion visuelle (Miroir sur l'axe horizontal selon votre formule)
        if invert:
            hor = -hor  # Inverse le sens horizontal (Z)

        # 2. 📐 Matrice de rotation trigonométrique standard autour de (0,0)
        # Formule de rotation 2D classique adaptée à votre repère hor/vert
        new_hor = hor * cos_a - vert * sin_a
        new_vert = hor * sin_a + vert * cos_a

        # On reconstruit la structure Kivy stricte [[hor, vert], r]
        points_transformes.append([[new_hor, new_vert], rayon])

    return points_transformes

def creat_entry_line(start_point, end_point, id_pnt=None):
    bbox=calculate_bbox_for_line(start_point, end_point)
    return {"type": "line", "start": start_point, "end": end_point, "bbox":bbox, "id_pnt": id_pnt}

def creat_entry_arc(start_point, end_point, center_point, radius, cw, id_pnt=None):
    bbox=calculate_bbox_for_arc(start_point, center_point, end_point, cw)
    return {
        "type": "arc", "start": start_point, "end": end_point, "center": center_point,
            "radius": radius, "cw":  cw, "bbox":bbox, "id_pnt": id_pnt}

def creat_entry_circle(center_point, radius, id_pnt=None):
    bbox=calculate_bbox_for_circle(center_point, radius)
    return {"type": "cercle", "center": center_point, "radius": radius, "bbox":bbox, "id_pnt": id_pnt}
def creat_entry_round(center_point, radius, id_pnt=None):
    # Comme pour le cercle, mais en round.
    # Info: celcle = fillet; round = fill
    bbox=calculate_bbox_for_circle(center_point, radius)
    return {"type": "round", "center": center_point, "radius": radius, "bbox":bbox, "id_pnt": id_pnt}

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
def normalize_color(color):
    """
    Normalise une couleur au format (r, g, b, a) en float [0.0 à 1.0].
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

