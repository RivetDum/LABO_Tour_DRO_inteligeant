# machine_tool/machine_data.py
import time
from config import SETTINGS

class MachineState:
    def __init__(self):
        axis_cfg = SETTINGS.get("axis", {})
        
        # Uniquement des valeurs physiques brutes (Rayon pour X, microns pour tous)
        self.z_machine = int(axis_cfg.get("hor", {}).get("last_position_micron", 0)) 
        self.x_machine = int(axis_cfg.get("vert", {}).get("last_position_micron", 0)) 
        self.y_machine = int(axis_cfg.get("sup", {}).get("last_position_micron", 0))  
        self.spindle_machine = int(axis_cfg.get("s", {}).get("last_position_micron", 0)) 

        # ====================================================================
        # CONFIGURATION FIXE (Sera lue/écrite dans mcu_param.json)
        # TODO: A faire : màj depuis le mcu_param.json
        # ====================================================================
        self.port_usb = "/dev/ttyACM0"
        self.baudrate = 921200
        
        self.used_wifi = False  
        self.port_wifi = 8888
        self.ip_wifi = "192.168.4.1"    
        self.ip_wifi_mcu = ["192.168.5.1", "192.168.6.1"]   
        self.nbr_attentes_wifi_actives = 0  # 0 = USB pur, >=1 = Forcer la double écoute Wi-Fi (+300)

        # ====================================================================
        # CADENCES DE COMMUNICATION AUTOMATIQUES
        # TODO: A faire : màj depuis le mcu_param.json
        # ====================================================================
        self.freq_emission_mcu = 200     # Fréquence brute émise par le boîtier (Hz)
        self.freq_emission_kivy = 120    # Fréquence d'envoi Kivy -> MCU (Hz)
        if (self.freq_emission_kivy + 10) > self.freq_emission_mcu :
            # sécurité pour garantir les émmisions de Kivy plus basse que celle du MCU. Car le MCU va envoyer et lire à la même fréquence !
            self.freq_emission_kivy = self.freq_emission_mcu - 10
        self.freq_lecture_kivy = int(self.freq_emission_mcu * 1.5) # Sur-échantillonnage à 300 Hz
        
        # Barrière de sécurité fixée à l'équivalent de 10 messages MCU manqués
        self.delai_perte_comm_sec = 10.0 / self.freq_emission_mcu # Ex: 10 / 200 = 0.050s (50ms)

        # Initialisation du chronomètre matériel haute précision
        self.last_timmer_comm = time.perf_counter() - self.delai_perte_comm_sec

        # ====================================================================
        # STATUTS VIVANTS POUR L'IHM KIVY
        # ====================================================================
        self.mode_reprise_crash = False  
        self.mcu_en_ligne = False        
        self.canal_comm_actif = None     
        self.mcu_mode = "OFF"            

        # ====================================================================
        # VARIABLES DE RETOUR POUR LES CONFIRMATIONS CRITIQUES (ACK)
        # ====================================================================
        self.ack_msg_id = -1
        self.ack_octets_recus = -1

    def OBSELET_generer_dictionnaire_dro(self):
        """Envoie les valeurs de base brutes."""
        return {
            "vert": self.x_machine,
            "hor": self.z_machine,
            "sup": self.y_machine,
            "s": self.spindle_machine
        }
    
    def OBSOLET_mettre_a_jour_positions(self, z, x, y, spindle):
        """Appelé par le décodeur binaire pour rafraîchir les cotes en microns."""
        self.z_machine = z
        self.x_machine = x
        self.y_machine = y
        self.spindle_machine = spindle

    def alerte_time_msg_in(self, receve_time, receve_source):
        """
        Surveille le rythme d'arrivée des trames pour gérer l'affichage de l'alerte.
        Fige l'état de panne pendant 3s à la reconnexion pour étouffer le clignotement.
        """
        # ====================================================================
        # CAS 1 : UN MESSAGE SOUVERAIN EST ARRIVÉ (USB ou Wi-Fi)
        # ====================================================================
        if receve_source in ["USB", "WIFI"]:
            self.canal_comm_actif = receve_source
            
            # --- CAS 1.A : RÉGIME PERMANENT DE CROISIÈRE ---
            if self.mcu_en_ligne:    
                self.last_timmer_comm = receve_time
                
            # --- CAS 1.B : QUARANTAINE DE RECONNEXION D'ATELIER ---
            else:                   
                # Au premier message après le crash, l'écart temporel est > 3.0s.
                # On réenclenche la machine, on rafraîchit la montre, et l'IHM
                # se débloquera au tour suivant si le flux reste stable à 200Hz.
                if receve_time - self.last_timmer_comm > 3.0: 
                    self.mcu_en_ligne = True
                    self.last_timmer_comm = receve_time
                    print(f"[🟢 ALERTE] Liaison rétablie et validée sur {receve_source}.")
                else:
                    # Tant que les messages arrivent toutes les 5ms, l'écart reste < 3.0s.
                    # Le code glisse ici : l'IHM reste rouge (mcu_en_ligne = False), 
                    # mais les microns bougent déjà en arrière-plan. C'est parfait.
                    pass

        # ====================================================================
        # CAS 2 : PANNE PHYSIQUE OU TRAME COMPLÈTEMENT CORROMPUE
        # ====================================================================
        else:    
            if receve_time - self.last_timmer_comm > self.delai_perte_comm_sec:
                if self.mcu_en_ligne: 
                    self.mcu_en_ligne = False
                    self.canal_comm_actif = None
                    
                    # 🚨 DÉCLENCHEMENT DU COMPTEUR D'ALERTE D'AFFICHAGE KIVY
                    print(f"[🚨 ALERTE] Commande coupée. Aucun message depuis {int(self.delai_perte_comm_sec * 1000)} ms.")
                    
                    # TODO: Injecter l'affichage de votre Pop-up ou bandeau rouge Kivy ici

    def OBSOLET_end_time_flag_diag_wifi(self, dt=None):
        """
        Sécurité de Timeout Diagnostic.
        Appelée automatiquement par l'horloge Clock Kivy après 1.5 seconde.
        Si le drapeau est encore True, c'est que le boîtier n'a pas répondu.
        """
        if self.attente_diagnostic_wifi:
            # 1. Coupure immédiate du mode double écoute (Fermeture de l'offset 300)
            self.attente_diagnostic_wifi = False
            
            # 2. Nettoyage de la commande pour éviter les boucles infinies
            self.pong_wifi = False
            
            # 3. Déclenchement de l'alerte console
            print("[🚨 ALERTE] TIMEOUT DIAGNOSTIC : Le module Wi-Fi de la machine ne répond pas !")
            
            # TODO : Ouvrir votre Pop-up graphique Kivy :
            # "Le Wi-Fi de la machine ne répond pas ! Voulez-vous désactiver le Wi-Fi dans vos paramètres ?"
            
        else:
            # Le drapeau est déjà à False. Cela prouve que 'traiter_pong_diagnostic' 
            # a intercepté le Pong de l'ESP32 à temps et a déjà désactivé le flag.
            print("[🟢 DIAG] Diagnostic réussi ! Le Wi-Fi de la machine est opérationnel.")
            pass


    def save_json(self):
        pass

'''-------------------------------------------'''
''' A placer dans la class de paramètrage ou de diagnostique (boutons écrans)'''
class Temporaire_a_modifier:
    def change_test_wifi(self, change=False, newstatus=True):
        """ 
        Pilote l'état du Wi-Fi et gère l'arbitrage des pings universels ou exclusifs.
        change=True  -> Indique au MCU d'appliquer la modification matérielle de l'antenne.
        newstatus    -> True = Allumage / Maintien actif, False = Coupure de l'antenne.
        """
        from kivy.clock import Clock

        # 1. Sécurité préventive : annulation d'un éventuel timer de diagnostic en cours
        Clock.unschedule(self.machine.end_time_flag_diag_wifi)

        # 2. Configuration des variables de contrôle pour le dictionnaire de bits
        self.machine.wifi_change_configuration = bool(change)
        self.machine.wifi_status_desire = bool(newstatus)
        
        # Juste par sécurité, si les pong ou pong_wifi sont déjà actif par une autre fonction,
        # on attend 0,5 secondes avant de relancer cette fonction ? cela pourrait éviter des croisements indésirés ?
        # Ou alors remplacer ces variable par des list[id_msg, status_pong, status_pongwifi], mais je penses inutile ?
        if self.machine.pong or self.machine.pong_wifi:
            #activation d'une autre tentative dans X temps
            return #puis on sort ?
        
        self.machine.pong = False
        self.machine.pong_wifi = False

        # 3. 🧠 VOTRE LOGIQUE D'ARBITRAGE DES PINGS (DÉCONNEXION VS USINAGE)
        if newstatus: 
            # Le Wi-Fi est actif, on lève le bit 12 pour valider le canal bidirectionnel
            self.machine.pong_wifi = True
            self.machine.attente_diagnostic_wifi = True
        else:
            # On coupe le Wi-Fi ! Le bit 12 reste à False, mais on lève le bit 11 (Ping universel)
            # pour que le MCU confirme la coupure en renvoyant l'acquittement par l'USB !
            self.machine.pong = True
            # Pas besoin d'activer l'offset 300 (attente_diagnostic_wifi) car le retour se fera par l'USB standard
            self.machine.attente_diagnostic_wifi = False

        # 4. On bombarde l'ordre binaire compacté 200 sur le câble
        self.calculator.empaqueter_et_envoyer(200)

        # 5. Lancement conditionnel du Chien de garde de 1.5 seconde
        if newstatus: 
            Clock.schedule_once(self.machine.end_time_flag_diag_wifi, 1.5)
            print(f"[DIAG] Test Wi-Fi bidirectionnel lancé (Timeout: 1.5s).")
        else:
            print(f"[DIAG] Ordre de coupure Wi-Fi transmis. Quittancement attendu sur l'USB.")
