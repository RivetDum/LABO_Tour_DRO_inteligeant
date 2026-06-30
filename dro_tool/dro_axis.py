# dro_tool / dro_axis.py         # ⚙️ popups / outils liés aux axes


from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class AxisSimplePopup(Popup):
    def __init__(self, axis_name="?", **kwargs):
        super().__init__(**kwargs)

        self.axis_name = axis_name
        self.title = f"Réglage de l’axe {self.axis_name}"
        self.size_hint = (0.4, 0.3)

        # --- Contenu principal de la popup ---
        layout = BoxLayout(orientation="vertical", spacing=10, padding=15)

        # Label principal
        lbl = Label(text=f"Axe sélectionné : [b]{self.axis_name}[/b]", markup=True, font_size="18sp")

        # Bouton pour fermer
        btn_close = Button(text="Fermer", size_hint_y=None, height=50)
        btn_close.bind(on_release=self.dismiss)

        layout.add_widget(lbl)
        layout.add_widget(btn_close)

        # Ajoute le layout dans le contenu de la popup
        self.add_widget(layout)
