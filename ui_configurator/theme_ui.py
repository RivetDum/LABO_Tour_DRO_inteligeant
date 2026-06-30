#ui_configurator - theme_ui.py

class UiTheme:
   def __init__(self):
      self.app_thm={
             "draw_line": {
                "liaison_line": "#838d83",
                "detail_line": "#11de1b",
                "erreur_detail_line": "#ff4081",
                "profil_line": "#96fbbe",
                "erreur_profil_line": "#ff4081",
                "profil_big_bbox": "#81ff5e",
                "profil_bbox": "#a0ff86",
                "detail_bbox": "#a0ff86"
                }
      }

fallback_theme={} # theme utlisateur de remplacement en cas d'erreur