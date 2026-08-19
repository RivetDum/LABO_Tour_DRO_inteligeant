# cutting_tool/cutting_widgets/__init__.py
import os
from kivy.lang import Builder
# 1. Exposer le fichier commun pour l'import 'from cutting_tool.cutting_widgets import common_cut_tool'
from . import common_cut_tool

# Chargement automatique du KV unique pour tout le sous-dossier
kv_path = os.path.join(os.path.dirname(__file__), "popup_widget.kv")
if os.path.exists(kv_path):
    Builder.load_file(kv_path)
