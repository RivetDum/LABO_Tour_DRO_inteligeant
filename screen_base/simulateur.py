# screen_base \ simulateur.py

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, Rectangle

class SimulationPanel(BoxLayout):
    """
    Pupitre vertical de développement pour simuler les mouvements du tour.
    Injecte les microns physiques directement dans l'objet MachineState.
    """
    def __init__(self, machine_instance, **kwargs):
        super().__init__(**kwargs)
        self.machine = machine_instance

        #Juste pour  tester, je vais forcer l'offset d'outil:
        self.machine.offset_tool_hor = -1000    # 1mm
        self.machine.offset_tool_vert = -1000    # -1mm

        
        # 📐 ORIENTATION GLOBALE DU PANNEAU : Vertical
        self.orientation = 'vertical'
        self.spacing = 10
        self.padding = 10
        
        # Fond visuel distinct (Bleu nuit industriel discret)
        with self.canvas.before:
            Color(0.12, 0.16, 0.22, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        # En-tête du panneau
        self.add_widget(Label(
            text="[ SIMULATEUR MCU ]", 
            color=(0, 1, 1, 1), 
            bold=True, 
            size_hint_y=None, 
            height=30
        ))

        # 🎛️ CONTENEUR DES SLIDERS : Rangés côte à côte (horizontalement)
        # Chaque colonne contiendra son étiquette de texte et son slider vertical
        zone_sliders = BoxLayout(orientation='horizontal', spacing=5, padding=(0,0,0,20), size_hint=(1, 1))

        # --- COLONNE AXE Z (Longitudinal) ---
        colonne_z = BoxLayout(orientation='vertical', spacing=2)
        self.lbl_z = Label(text="Z\n0\nµm", halign='center', size_hint_y=None, height=60)
        self.slider_z = Slider(
            orientation='vertical', # 🔄 Pivotement vertical pour un maximum de course
            min=-200000, 
            max=100000, 
            value=int(getattr(self.machine, 'z_machine', 0)), 
            step=10
        )
        self.slider_z.bind(value=self.simuler_axe_z)
        colonne_z.add_widget(self.slider_z)
        colonne_z.add_widget(self.lbl_z)
        zone_sliders.add_widget(colonne_z)

        # --- COLONNE AXE X (Transversal / Diamètre) ---
        colonne_x = BoxLayout(orientation='vertical', spacing=5)
        self.lbl_x = Label(text="X\n0\nµm", halign='center', size_hint_y=None, height=60)
        self.slider_x = Slider(
            orientation='vertical', # 🔄 Pivotement vertical
            min=-50000, 
            max=100000, 
            value=int(getattr(self.machine, 'x_machine', 0)), 
            step=10
        )
        self.slider_x.bind(value=self.simuler_axe_x)
        colonne_x.add_widget(self.slider_x)
        colonne_x.add_widget(self.lbl_x)
        zone_sliders.add_widget(colonne_x)

        # --- COLONNE AXE Y (Chariot Supérieur / Porte-outils) ---
        colonne_y = BoxLayout(orientation='vertical', spacing=5)
        self.lbl_y = Label(text="Y (Sup)\n0\nµm", halign='center', size_hint_y=None, height=60)
        self.slider_y = Slider(
            orientation='vertical', # 🔄 Pivotement vertical
            min=-30000, 
            max=30000,             # Course typiquement plus courte sur le chariot sup.
            value=int(getattr(self.machine, 'y_machine', 0)), 
            step=10
        )
        self.slider_y.bind(value=self.simuler_axe_y)
        colonne_y.add_widget(self.slider_y)
        colonne_y.add_widget(self.lbl_y)
        zone_sliders.add_widget(colonne_y)

        # Injection de la zone de contrôle dans le layout principal
        self.add_widget(zone_sliders)

        # --- COMMANDE BASSE : SÉCURITÉ ARU ---
        bt_reste = Button(
            text="RESTE (Z X Y = 0)", 
            bold=False, 
            size_hint_y=None, 
            height=40, 
            background_color=(0, 1, 1, 1)
        )
        bt_reste.bind(state=self.reste_pos)
        self.add_widget(bt_reste)

        self.btn_estop = ToggleButton(
            text="SIMULER E-STOP", 
            bold=True, 
            size_hint_y=None, 
            height=40, 
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.btn_estop.bind(state=self.simuler_estop)
        self.add_widget(self.btn_estop)

        # Forcer le premier affichage des valeurs au démarrage
        self.simuler_axe_z(None, self.slider_z.value)
        self.simuler_axe_x(None, self.slider_x.value)
        self.simuler_axe_y(None, self.slider_y.value)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def simuler_axe_z(self, instance, value):
        self.machine.z_machine = value
        self.lbl_z.text = f"Z\n{int(value):,}\nµm".replace(",", " ")

    def simuler_axe_x(self, instance, value):
        self.machine.x_machine = value
        self.lbl_x.text = f"X\n{int(value):,}\nµm".replace(",", " ")

    def simuler_axe_y(self, instance, value):
        # Injection directe dans y_machine (utilisé par votre sauvegarde de session)
        self.machine.y_machine = value
        self.lbl_y.text = f"Y (Sup)\n{int(value):,}\nµm".replace(",", " ")

    def simuler_estop(self, instance, state):
        if state == 'down':
            self.machine.estop_actif = True
            instance.text = "🚨 ARU ACTIF"
        else:
            self.machine.estop_actif = False
            instance.text = "SIMULER E-STOP"

    def reste_pos(self, instance, state):
        #self.slider_z.value = 0
        #self.slider_x.value = 0
        #self.slider_y.value = 0
        self.machine.reset_hor_to_dro(0)
        self.machine.reset_vert_to_dro(0)
        self.machine.reset_sup_to_dro(0)
        # 2️⃣ Synchronisation visuelle des sliders du pupitre de dev
        # Assigner la valeur au slider va automatiquement appeler simuler_axe_x/z et rafraîchir les étiquettes !
        self.slider_z.value = self.machine.z_machine
        self.slider_x.value = self.machine.x_machine
        self.slider_y.value = self.machine.y_machine