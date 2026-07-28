# theme_manager.py

#from ui_configurator.theme_ui import UiTheme
#from copy import deepcopy

#_current_theme = None  # Thème courant
#_fallback_theme = None  # Thème de secours en cas de bug

draw_line= {    # couleurs et épaisseur de dessin
    "liaison": "#838d83",
    "liaison_w": 2,
    "detail": "#11de1b",
    "detail_w": 2,
    "erreur_detail": "#ff0055",
    "erreur_detail_w": 4,
    "profil_save": "#fb96bd",
    "profil_save_w": 2,
    "erreur_profil_save": "#ff0055",
    "erreur_profil_save_w": 4,
    "profil_cao": "#36a8f4",
    "profil_cao_w": 2,
    "erreur_profil_cao": "#ff0055",
    "erreur_profil_cao_w": 4,
    "profil_fao": "#ffd255",
    "profil_fao_w": 2,
    "erreur_profil_fao": "#ff0055",
    "erreur_profil_fao_w": 2,
    "profil_big_bbox": "#81ff5e",
    "profil_big_bbox_w": 1,
    "profil_bbox": "#a0ff86",
    "profil_bbox_w": 1,
    "detail_bbox": "#a0ff86",
    "detail_bbox_w": 1,
    "tool_profil": "#A6A6A6",   # contour: corp du burin
    "tool_profil_w": 4,
    "tool_insert": "#d4ff00",   # remplissage: plaquette carbure de coupe
    "tool_offset": "#e5a3ff",   # remplissage: rond  représentant l'offset d'usinage autour de la pointe de l'outil
    # ci-dessous, à remplacer par ci-dessus
    "profil": "#fb96bd",
    "profil_w": 2,
    "erreur_profil": "#ff0055",
    "erreur_profil_w": 2,
}