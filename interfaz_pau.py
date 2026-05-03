import customtkinter as ctk
import tkinter as tk 
from tkinter import messagebox
import threading
from queue import Queue
import time
import os
import numpy as np
from scipy.io import savemat, loadmat
from PIL import Image, ImageTk

# =================================================================
# CONFIGURACIÓN
# =================================================================
SONGS_MAT = "songs.mat"
UNICORN_MAT = "speller_selections.mat"

# Mapeo de Notas (Para COMPOSICION)
NOTA_MAP = {
    "D": "D", "R": "R", "M": "M", "F": "F", 
    "S": "S", "L": "L", "I": "I", "O": "O"
}

# =================================================================
# GESTIÓN DE CANCIONES
# =================================================================

def cargar_canciones():
    """Carga las canciones desde songs.mat como dict {nombre: {titulo, notas, artista}}."""
    if not os.path.exists(SONGS_MAT):
        return {}
    try:
        data = loadmat(SONGS_MAT, squeeze_me=True, struct_as_record=False)
        if "songs" not in data:
            return {}
        
        songs_struct = data["songs"]
        canciones = {}
        
        if hasattr(songs_struct, "__dict__"):
            for nombre, contenido in songs_struct.__dict__.items():
                if nombre.startswith("_"):
                    continue
                if isinstance(contenido, dict):
                    canciones[nombre] = contenido
                elif isinstance(contenido, np.ndarray):
                    canciones[nombre] = {
                        "title": nombre,
                        "artist": "Usuario",
                        "lyrics": "",
                        "notes": contenido.tolist()
                    }
        elif isinstance(songs_struct, dict):
            for nombre, contenido in songs_struct.items():
                if isinstance(contenido, dict):
                    canciones[nombre] = contenido
                else:
                    canciones[nombre] = {
                        "title": nombre,
                        "artist": "Usuario",
                        "lyrics": "",
                        "notes": contenido.tolist() if isinstance(contenido, np.ndarray) else [contenido]
                    }
                    
        return canciones
    except Exception as e:
        print("Error al cargar songs.mat:", e)
        return {}

def guardar_todas_canciones(canciones):
    """Guarda todas las canciones en songs.mat."""
    savemat(SONGS_MAT, {"songs": canciones})

def guardar_cancion(nombre, notas, titulo=None, artista="Usuario", lyrics=""):
    """Añade/actualiza una canción en songs.mat."""
    canciones = cargar_canciones()
    canciones[nombre] = {
        "title": titulo if titulo else nombre,
        "artist": artista,
        "lyrics": lyrics,
        "notes": notas
    }
    guardar_todas_canciones(canciones)
    print(f"Canción '{nombre}' guardada en {SONGS_MAT}.")

# =================================================================
# CONFIGURACIÓN GLOBAL SIMULADA DE DATOS
# =================================================================
DATA_STATE = {
    "mode": "MENU",
    "last_selection": "N/A",
    "composed_notes": [],
    "songs": cargar_canciones(),
    "predefined_songs": {
        "C": {
            "title": "Cumpleaños Feliz",
            "artist": "Tradicional", 
            "lyrics": "Cumpleaños feliz, cumpleaños feliz...\nTe deseamos todos, cumpleaños feliz.",
            "notes": ["Do", "Do", "Re", "Do", "Fa", "Mi"]
        },
        "N": {
            "title": "Noche de Paz", 
            "artist": "Tradicional",
            "lyrics": "Noche de paz, noche de amor...\nTodo duerme en derredor.",
            "notes": ["Sol", "Do", "Re", "Mi", "Fa", "Sol"]
        },
        "V": {
            "title": "Feliz Navidad",
            "artist": "Tradicional",
            "lyrics": "Feliz Navidad, Feliz Navidad...\nFeliz Navidad, próspero año y felicidad.",
            "notes": ["Do", "Do", "Re", "Do", "Fa", "Mi"]
        }
    },
    "message": "Sistema operativo. Esperando comando BCI.",
    "current_song_id": None,
    "current_song_type": None,
}

# Cola de comandos de interfaz
UI_QUEUE = Queue()

# =================================================================
# DIÁLOGO PERSONALIZADO DE GUARDADO
# =================================================================

class GuardarCancionDialog(ctk.CTkToplevel):
    """Diálogo modal para preguntar el nombre de la canción."""
    def __init__(self, master, prompt_text):
        super().__init__(master)
        self.transient(master)
        self.title("Guardar Canción")
        self.result = None

        bg_color = "#F2EFE9"
        button_font = ("Arial", 12, "bold")

        self.configure(fg_color=bg_color)

        main_frame = ctk.CTkFrame(self, fg_color=bg_color)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text=prompt_text, 
                    font=("Times New Roman", 14),
                    text_color="#9E2A2F",
                    fg_color=bg_color).pack(pady=10)

        self.entry = ctk.CTkEntry(main_frame, font=("Arial", 14), width=30)
        self.entry.pack(pady=10)
        self.entry.focus_set()

        button_frame = ctk.CTkFrame(main_frame, fg_color=bg_color)
        button_frame.pack(pady=10)

        ctk.CTkButton(button_frame, text="OK", command=self.on_ok,
                     font=button_font, fg_color="#D2691E",
                     text_color="white", width=100).pack(side="left", padx=10)

        ctk.CTkButton(button_frame, text="Cancelar", command=self.on_cancel,
                     font=button_font, fg_color="#B22222",
                     text_color="white", width=100).pack(side="left", padx=10)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window()

    def on_ok(self):
        self.result = self.entry.get().strip()
        self.destroy()

    def on_cancel(self):
        self.destroy()

# =================================================================
# INTERFAZ PRINCIPAL (ESTILO interfaz2.py)
# =================================================================

class NeuroPianistApp:
    """Clase principal de la interfaz con estilo de interfaz2.py."""

    # Paleta de colores de interfaz2.py
    COLOR_BG_PRIMARY = "#F2EFE9"        # Beige claro (fondo principal)
    COLOR_BG_SECONDARY = "#FFF8E7"      # Beige más claro para cards
    COLOR_ACCENT_1 = "#FF6F61"          # Coral para botón 1
    COLOR_ACCENT_2 = "#D2691E"          # Marrón para botón 2
    COLOR_ACCENT_3 = "#B22222"          # Rojo oscuro para botón 3
    COLOR_ACCENT_4 = "#F7A8B8"          # Rosa para botón 4
    COLOR_TEXT_PRIMARY = "#9E2A2F"      # Rojo vino para títulos
    COLOR_TEXT_SECONDARY = "#333333"    # Gris oscuro para texto
    COLOR_BORDER = "#CCCCCC"            # Gris para bordes

    def __init__(self, master):
        self.master = master
        master.title("NeuroPianist – Brain-Controlled Music")
        master.geometry("1200x700")
        
        # Configurar CTK para Light Mode
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        
        self.data_state = DATA_STATE
        
        # PRIMERO: Configurar el fondo principal
        master.configure(fg_color=self.COLOR_BG_PRIMARY)
        
        # Cargar imagen de fondo - usar path relativo
        try:
            bg_img = Image.open("base.png")
            # Redimensionar para ajustarse a la ventana
            bg_img = bg_img.resize((1200, 700), Image.Resampling.LANCZOS)
            self.bg_image = ImageTk.PhotoImage(bg_img)
            
            # Crear label con la imagen de fondo usando tkinter directamente
            self.bg_label = tk.Label(master, image=self.bg_image)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            
            # Asegurar que el fondo esté detrás de todo
            self.bg_label.lower()
            
        except Exception as e:
            print(f"Advertencia: No se pudo cargar 'base.png'. Error: {e}")
            print(f"Directorio actual: {os.getcwd()}")
            print(f"Archivos en directorio: {os.listdir()}")
            # Si no hay imagen, usar color sólido
            master.configure(fg_color=self.COLOR_BG_PRIMARY)

        # Configuración de fuentes (estilo interfaz2.py)
        self.f_title = ("Times New Roman", 32, "bold")
        self.f_section_title = ("Times New Roman", 24, "bold")
        self.f_card_title = ("Arial", 18, "bold")
        self.f_body = ("Arial", 14)
        self.f_small = ("Arial", 12)
        self.f_button = ("Arial", 12, "bold")
        self.f_big_button = ("Arial", 14, "bold")
        
        self._create_widgets()
        self.master.after(100, self._process_ui_queue)

    def _create_widgets(self):
        """Crea y distribuye los widgets con diseño estilo interfaz2.py."""
        
        # --- SIDEBAR IZQUIERDA ---
        # Usar fondo semitransparente para que se vea la imagen
        sidebar = ctk.CTkFrame(self.master, width=300, 
                              fg_color="#FFF8E7",  # Color sólido
                              corner_radius=0, border_width=1, border_color=self.COLOR_BORDER)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Logo y Título
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(pady=(30, 40), padx=20, fill="x")
        
        ctk.CTkLabel(logo_frame, text="🎵", font=("Arial", 40)).pack(pady=(0, 10))
        ctk.CTkLabel(logo_frame, text="NeuroPianist", 
                    text_color=self.COLOR_TEXT_PRIMARY, 
                    font=self.f_title).pack()
        
        # Modo Actual
        mode_frame = ctk.CTkFrame(sidebar, fg_color="#FFFFFF",  # Blanco semitransparente
                                 corner_radius=10, border_width=1, border_color=self.COLOR_BORDER)
        mode_frame.pack(pady=(0, 20), padx=15, fill="x")
        
        ctk.CTkLabel(mode_frame, text="MODO ACTUAL", 
                    text_color=self.COLOR_TEXT_SECONDARY,
                    font=self.f_small).pack(pady=(10, 5))
        self.lbl_mode = ctk.CTkLabel(mode_frame, text="MENU", 
                                     text_color=self.COLOR_TEXT_PRIMARY, 
                                     font=("Times New Roman", 20, "bold"))
        self.lbl_mode.pack(pady=(0, 10))
        
        # Último Comando BCI
        ctk.CTkLabel(sidebar, text="ÚLTIMO COMANDO BCI", 
                    text_color=self.COLOR_TEXT_SECONDARY,
                    font=self.f_small).pack(pady=(10, 5), anchor="w", padx=20)
        
        self.lbl_selection = ctk.CTkLabel(sidebar, text="N/A", 
                                         text_color="white", 
                                         fg_color=self.COLOR_ACCENT_2, 
                                         corner_radius=20,
                                         font=self.f_card_title, height=40)
        self.lbl_selection.pack(pady=(0, 30), padx=20, fill="x")
        
        # Estado del Sistema
        status_frame = ctk.CTkFrame(sidebar, fg_color="#FFFFFF", 
                                   corner_radius=10, border_width=1, border_color=self.COLOR_BORDER)
        status_frame.pack(pady=(0, 20), padx=15, fill="x")
        
        ctk.CTkLabel(status_frame, text="ESTADO DEL SISTEMA", 
                    text_color=self.COLOR_TEXT_SECONDARY,
                    font=self.f_small).pack(pady=(10, 5))
        
        self.lbl_message = ctk.CTkLabel(status_frame, text=self.data_state["message"], 
                                       text_color=self.COLOR_TEXT_SECONDARY, 
                                       font=self.f_body, 
                                       wraplength=250, justify="center")
        self.lbl_message.pack(pady=(0, 10), padx=10)
        
        # Footer
        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(side="bottom", pady=(20, 20), padx=20, fill="x")
        ctk.CTkLabel(footer, text="Brain-Computer Interface", 
                    text_color=self.COLOR_TEXT_SECONDARY,
                    font=self.f_small).pack()

        # --- CONTENIDO PRINCIPAL ---
        # Usar fondo transparente para que se vea la imagen
        main_content = ctk.CTkFrame(self.master, fg_color="transparent")
        main_content.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        
        # Header con fondo semitransparente
        header = ctk.CTkFrame(main_content, fg_color="transparent", height=80)
        header.pack(fill="x", padx=40, pady=(30, 20))
        header.pack_propagate(False)
        
        self.lbl_content_title = ctk.CTkLabel(header, text="Menú Principal", 
                                             text_color=self.COLOR_TEXT_PRIMARY, 
                                             font=("Times New Roman", 36, "bold"))
        self.lbl_content_title.pack(side="left", fill="x", expand=True)
        
        # Contenedor de contenido dinámico - transparente
        self.content_frame = ctk.CTkFrame(main_content, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        
        self._update_interface()

    def _clear_content(self):
        """Limpia el contenedor de contenido."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _create_menu_view(self):
        """Crea vista de menú con estilo de interfaz2.py."""
        self._clear_content()
        
        # Contenedor principal - transparente
        main_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main_frame.pack(expand=True, fill="both")
        
        # Título de bienvenida
        ctk.CTkLabel(main_frame, text="¡Bienvenido a NeuroPianist!", 
                    text_color=self.COLOR_TEXT_PRIMARY,
                    font=("Times New Roman", 32, "bold")).pack(pady=20)
        
        # Frame para botones - transparente
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(expand=True)
        
        # Botones del menú principal con números como en interfaz2.py
        menu_items = [
            ("1. Modo Normal", self.COLOR_ACCENT_1, lambda: self._change_mode("NORMAL")),
            ("2. Modo Composición", self.COLOR_ACCENT_2, lambda: self._change_mode("COMPOSICION")),
            ("3. Modo Neurify", self.COLOR_ACCENT_3, lambda: self._change_mode("NEURIFY")),
            ("4. Salir", self.COLOR_ACCENT_4, self.master.quit)
        ]
        
        for text, color, command in menu_items:
            btn = ctk.CTkButton(button_frame, text=text, command=command,
                               font=self.f_big_button, fg_color=color,
                               text_color="white", height=50, width=300,
                               corner_radius=8)
            btn.pack(pady=10)

    def _create_normal_view(self):
        """Vista del modo normal."""
        self._clear_content()
        
        # Frame principal con scroll - transparente
        container = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True)
        
        # Información del modo - fondo semitransparente
        info_frame = ctk.CTkFrame(container, fg_color="#FFFFFF", 
                                 corner_radius=10, border_width=1, border_color=self.COLOR_BORDER)
        info_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(info_frame, text="🎹 Modo Normal", 
                    text_color=self.COLOR_TEXT_PRIMARY,
                    font=self.f_section_title).pack(pady=20, padx=30, anchor="w")
        
        ctk.CTkLabel(info_frame, text="Toca notas individuales en tiempo real",
                    text_color=self.COLOR_TEXT_SECONDARY,
                    font=self.f_body).pack(pady=(0, 20), padx=30, anchor="w")
        
        # Teclado de notas - fondo semitransparente
        notes_frame = ctk.CTkFrame(container, fg_color="#FFFFFF",
                                  corner_radius=10, border_width=1, border_color=self.COLOR_BORDER)
        notes_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(notes_frame, text="Notas Disponibles", 
                    text_color=self.COLOR_TEXT_PRIMARY,
                    font=self.f_section_title).pack(pady=(20, 10), padx=30, anchor="w")
        
        # Grid de notas con números - transparente
        notes_grid = ctk.CTkFrame(notes_frame, fg_color="transparent")
        notes_grid.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        notes = [
            ("D", "Do"), ("R", "Re"), ("M", "Mi"), ("F", "Fa"),
            ("S", "Sol"), ("L", "La"), ("I", "Si"), ("D", "Do⁺")
        ]
        
        # Configurar columnas proporcionalmente
        for col in range(4):
            notes_grid.columnconfigure(col, weight=1)
            
        for i, (key, note) in enumerate(notes):
            row = i // 4
            col = i % 4
            
            note_card = ctk.CTkFrame(notes_grid, fg_color="#FFFFFF", corner_radius=8,
                                    border_width=1, border_color=self.COLOR_BORDER)
            note_card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # Hacer que la tarjeta se expanda
            note_card.grid_rowconfigure(0, weight=1)
            note_card.grid_columnconfigure(0, weight=1)
            
            # Frame para centrar contenido
            center_frame = ctk.CTkFrame(note_card, fg_color="transparent")
            center_frame.grid(row=0, column=0, sticky="nsew")
            center_frame.grid_rowconfigure(0, weight=1)
            center_frame.grid_columnconfigure(0, weight=1)
            
            # Contenido centrado vertical y horizontalmente
            content_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
            content_frame.grid(row=0, column=0)
            
            ctk.CTkLabel(content_frame, text=key, text_color=self.COLOR_ACCENT_2,
                        font=("Arial", 24, "bold")).pack()
            ctk.CTkLabel(content_frame, text=note, text_color=self.COLOR_TEXT_PRIMARY,
                        font=self.f_card_title).pack()
        
        # Comandos de modo
        self._add_mode_commands(container)

    def _create_composition_view(self):
        """Vista del modo composición."""
        self._clear_content()
        
        container = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True)
        
        # Secuencia actual - fondo semitransparente
        sequence_frame = ctk.CTkFrame(container, fg_color="#FFFFFF",
                                     corner_radius=10, border_width=1, border_color=self.COLOR_BORDER)
        sequence_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(sequence_frame, text="✏️ Modo Composición", 
                    text_color=self.COLOR_TEXT_PRIMARY,
                    font=self.f_section_title).pack(pady=(20, 10), padx=30, anchor="w")
        
        if self.data_state['composed_notes']:
            notes_display = ' → '.join([NOTA_MAP.get(n, n) for n in self.data_state['composed_notes']])
            sequence_text = f"{notes_display}\n\n{len(self.data_state['composed_notes'])} notas añadidas"
        else:
            sequence_text = "Aún no has añadido notas. Comienza tu composición..."
        
        ctk.CTkLabel(sequence_frame, text=sequence_text, 
                    text_color=self.COLOR_TEXT_SECONDARY,
                    font=self.f_body, justify="left").pack(pady=(0, 20), padx=30, anchor="w")
        
        # Instrucciones con números
        instructions_frame = ctk.CTkFrame(sequence_frame, fg_color="transparent")
        instructions_frame.pack(pady=(0, 20), padx=30, fill="x")
        
        instructions = [
            ("1. Añadir Notas", "D:DO, R:RE, M:MI, F:FA , S:SOL, L:LA, I:SI, O:DO⁺"),
            ("2. Finalizar", "Presiona [0] para terminar"),
            ("3. Guardar", "Escribe nombre y presiona [N]")
        ]
        
        for num, (title, desc) in enumerate(instructions, 1):
            inst_card = ctk.CTkFrame(instructions_frame, fg_color="#FFFFFF", 
                                    corner_radius=8, border_width=1, border_color=self.COLOR_BORDER)
            inst_card.pack(fill="x", pady=5)
            
            ctk.CTkLabel(inst_card, text=title, 
                        text_color=self.COLOR_TEXT_PRIMARY,
                        font=self.f_body, anchor="w").pack(padx=15, pady=10, anchor="w")
            ctk.CTkLabel(inst_card, text=desc, 
                        text_color=self.COLOR_TEXT_SECONDARY,
                        font=self.f_small, anchor="w").pack(padx=15, pady=(0, 10), anchor="w")
        
        # Botones con números
        btn_frame = ctk.CTkFrame(sequence_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 20), padx=30)
        
        btn_add = ctk.CTkButton(btn_frame, text="1. Añadir Nota (Simulado)",
                               font=self.f_button, fg_color=self.COLOR_ACCENT_2,
                               text_color="white", command=self._simulate_add_note)
        btn_add.pack(side="left", padx=5)
        
        btn_finish = ctk.CTkButton(btn_frame, text="2. Terminar y Guardar",
                                  font=self.f_button, fg_color=self.COLOR_ACCENT_3,
                                  text_color="white", command=self._finish_composition)
        btn_finish.pack(side="left", padx=5)
        
        self._add_mode_commands(container)

    def _create_neurify_view(self):
        """Vista del modo Neurify."""
        self._clear_content()
        
        container = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True)
        
        # Now Playing (si hay algo reproduciéndose)
        if self.data_state.get("current_song_id"):
            self._create_now_playing_card(container)
        
        # Canciones Predefinidas con números
        ctk.CTkLabel(container, text="Canciones Predefinidas", 
                    text_color=self.COLOR_TEXT_PRIMARY,
                    font=self.f_section_title).pack(pady=(0, 15), anchor="w")
        
        predefined_frame = ctk.CTkFrame(container, fg_color="transparent")
        predefined_frame.pack(fill="x", pady=(0, 30))
        
        predefined_songs = self.data_state.get("predefined_songs", {})
        for i, (song_id, song) in enumerate(predefined_songs.items()):
            self._create_song_card(predefined_frame, song_id, song, i)
        
        # Tus Composiciones
        if self.data_state["songs"]:
            ctk.CTkLabel(container, text="Tus Composiciones", 
                        text_color=self.COLOR_TEXT_PRIMARY,
                        font=self.f_section_title).pack(pady=(20, 15), anchor="w")
            
            compositions_frame = ctk.CTkFrame(container, fg_color="transparent")
            compositions_frame.pack(fill="x", pady=(0, 30))
            
            for i, (song_id, song) in enumerate(self.data_state["songs"].items()):
                self._create_song_card(compositions_frame, song_id, song, i)
        
        self._add_mode_commands(container)

    def _create_now_playing_card(self, parent):
        """Crea la tarjeta 'Now Playing'."""
        current_id = self.data_state.get("current_song_id")
        
        # Buscar la canción
        song = None
        if current_id in self.data_state.get("predefined_songs", {}):
            song = self.data_state["predefined_songs"][current_id]
        elif current_id in self.data_state["songs"]:
            song = self.data_state["songs"][current_id]
        
        if not song:
            return
        
        now_playing = ctk.CTkFrame(parent, fg_color="#FFFFFF", 
                                  corner_radius=10, border_width=2, border_color=self.COLOR_ACCENT_2)
        now_playing.pack(fill="x", pady=(0, 30))
        
        content = ctk.CTkFrame(now_playing, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=15)
        
        # Indicador de reproducción
        ctk.CTkLabel(content, text="▶", text_color=self.COLOR_ACCENT_2,
                    font=("Arial", 24)).pack(side="left", padx=(0, 20))
        
        # Info de la canción
        info = ctk.CTkFrame(content, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(info, text="REPRODUCIENDO AHORA", text_color=self.COLOR_ACCENT_2,
                    font=self.f_small).pack(anchor="w")
        ctk.CTkLabel(info, text=song["title"], text_color=self.COLOR_TEXT_PRIMARY,
                    font=self.f_card_title).pack(anchor="w", pady=(5, 0))
        ctk.CTkLabel(info, text=song["artist"], text_color=self.COLOR_TEXT_SECONDARY,
                    font=self.f_body).pack(anchor="w")

    def _create_song_card(self, parent, song_id, song, index):
        """Crea una tarjeta de canción con números."""
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", 
                           corner_radius=8, border_width=1, border_color=self.COLOR_BORDER)
        card.pack(fill="x", pady=8)
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=15)
        
        # Número/ID con formato [X] como en interfaz2.py
        ctk.CTkLabel(content, text=f"[{song_id}]", text_color=self.COLOR_TEXT_SECONDARY,
                   font=self.f_body, width=40).pack(side="left", padx=(0, 15))
        
        # Info de la canción
        info = ctk.CTkFrame(content, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(info, text=song["title"], text_color=self.COLOR_TEXT_PRIMARY,
                    font=self.f_card_title, anchor="w").pack(fill="x")
        ctk.CTkLabel(info, text=song["artist"], text_color=self.COLOR_TEXT_SECONDARY,
                    font=self.f_small, anchor="w").pack(fill="x")
        
        # Botón de play
        btn_play = ctk.CTkButton(content, text="▶ Reproducir", 
                                font=self.f_small, fg_color=self.COLOR_ACCENT_2,
                                text_color="white", width=100, height=30,
                                command=lambda sid=song_id: self._play_song(sid))
        btn_play.pack(side="right")

    def _add_mode_commands(self, parent):
        """Añade los comandos de cambio de modo con números."""
        commands_frame = ctk.CTkFrame(parent, fg_color="#FFFFFF",
                                     corner_radius=10, border_width=1, border_color=self.COLOR_BORDER)
        commands_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkLabel(commands_frame, text="Cambiar de Modo", 
                    text_color=self.COLOR_TEXT_PRIMARY,
                    font=self.f_section_title).pack(pady=(20, 10), padx=30, anchor="w")
        
        commands = ctk.CTkFrame(commands_frame, fg_color="transparent")
        commands.pack(fill="x", padx=30, pady=(0, 20))
        
        # Botones en horizontal con números
        btn_frame = ctk.CTkFrame(commands, fg_color="transparent")
        btn_frame.pack()
        
        mode_buttons = [
            ("1. Normal", self.COLOR_ACCENT_1, lambda: self._change_mode("NORMAL")),
            ("2. Compositor", self.COLOR_ACCENT_2, lambda: self._change_mode("COMPOSICION")),
            ("3. Neurify", self.COLOR_ACCENT_3, lambda: self._change_mode("NEURIFY")),
            ("4. Menú", self.COLOR_ACCENT_4, lambda: self._change_mode("MENU"))
        ]
        
        for text, color, command in mode_buttons:
            btn = ctk.CTkButton(btn_frame, text=text, command=command,
                               font=self.f_button, fg_color=color,
                               text_color="white", width=140, height=40)
            btn.pack(side="left", padx=10)

    def _update_interface(self):
        """Actualiza la interfaz según el modo actual."""
        mode = self.data_state["mode"]
        
        # Actualizar título
        titles = {
            "MENU": "Menú Principal",
            "NORMAL": "🎹 Modo Normal",
            "COMPOSICION": "✏️ Modo Composición",
            "NEURIFY": "🎧 Modo Neurify"
        }
        self.lbl_content_title.configure(text=titles.get(mode, "NeuroPianist"))
        
        # Actualizar sidebar
        self.lbl_mode.configure(text=mode)
        self.lbl_selection.configure(text=self.data_state["last_selection"])
        self.lbl_message.configure(text=self.data_state["message"])
        
        # Renderizar vista correspondiente
        if mode == "MENU":
            self._create_menu_view()
        elif mode == "NORMAL":
            self._create_normal_view()
        elif mode == "COMPOSICION":
            self._create_composition_view()
        elif mode == "NEURIFY":
            self._create_neurify_view()

    def _process_ui_queue(self):
        """Procesa mensajes de la cola de comandos."""
        while not UI_QUEUE.empty():
            try:
                message = UI_QUEUE.get_nowait()
                command = message.get("command")
                value = message.get("value")

                if command == "UPDATE_MODE":
                    self.data_state["mode"] = value

                elif command == "UPDATE_SELECTION":
                    self.data_state["last_selection"] = value

                elif command == "PLAY_SONG":
                    self.data_state["current_song_id"] = value

                elif command == "UPDATE_DATA":
                    for key, val in value.items():
                        self.data_state[key] = val

                self._update_interface()

            except Exception as e:
                print(f"Error procesando comando de UI: {e}")

        self.master.after(100, self._process_ui_queue)

    def _change_mode(self, new_mode):
        """Cambia el modo de la aplicación."""
        UI_QUEUE.put({"command": "UPDATE_MODE", "value": new_mode})
        UI_QUEUE.put({"command": "UPDATE_SELECTION", "value": new_mode})
        UI_QUEUE.put({"command": "UPDATE_DATA", "value": {"message": f"Modo {new_mode} activado"}})
        
        if new_mode == "COMPOSICION":
            # Reiniciar notas al entrar en modo composición
            self.data_state["composed_notes"] = []

    def _simulate_add_note(self):
        """Simula añadir una nota (para demostración)."""
        import random
     
        notes_map = {1: "D", 2: "R", 3: "M", 4: "F", 5: "S", 6: "L", 7: "I", 8: "O"}
        note_num = random.choice(list(notes_map.keys()))
        note = notes_map[note_num]
        
        self.data_state["composed_notes"].append(note)
        UI_QUEUE.put({"command": "UPDATE_SELECTION", "value": str(note_num)})
        UI_QUEUE.put({"command": "UPDATE_DATA", "value": {
            "composed_notes": self.data_state["composed_notes"],
            "message": f"Nota {note_num} ({NOTA_MAP[note]}) añadida"
        }})

    def _finish_composition(self):
        """Termina y guarda la composición actual."""
        if not self.data_state['composed_notes']:
            messagebox.showinfo("Composición", 
                              "No has añadido ninguna nota. No se guardará la canción.")
            return
        
        # Mostrar diálogo para guardar
        dialog = GuardarCancionDialog(self.master, "¿Cómo quieres guardar esta canción?")
        nombre = dialog.result
        
        if nombre:
            # Convertir notas a nombres completos
            notas_completas = [NOTA_MAP.get(n, n) for n in self.data_state['composed_notes']]
            guardar_cancion(nombre, notas_completas, titulo=nombre)
            
            # Actualizar datos
            self.data_state["songs"] = cargar_canciones()
            UI_QUEUE.put({"command": "UPDATE_DATA", "value": {
                "message": f"Canción '{nombre}' guardada con {len(notas_completas)} notas.",
                "songs": self.data_state["songs"]
            }})
            
            messagebox.showinfo("Guardado", 
                              f"Canción '{nombre}' guardada con {len(notas_completas)} notas.")
        else:
            messagebox.showinfo("Guardado", 
                              "No se ha guardado la canción (nombre no proporcionado).")

    def _play_song(self, song_id):
        """Simula la reproducción de una canción."""
        # Buscar la canción
        song = None
        song_type = None
        
        if song_id in self.data_state.get("predefined_songs", {}):
            song = self.data_state["predefined_songs"][song_id]
            song_type = "predefined"
        elif song_id in self.data_state["songs"]:
            song = self.data_state["songs"][song_id]
            song_type = "user"
        
        if song:
            UI_QUEUE.put({"command": "PLAY_SONG", "value": song_id})
            UI_QUEUE.put({"command": "UPDATE_DATA", "value": {
                "current_song_id": song_id,
                "current_song_type": song_type,
                "message": f"Reproduciendo: {song['title']}"
            }})


if __name__ == "__main__":
    root = ctk.CTk()
    app = NeuroPianistApp(root)
    root.mainloop()