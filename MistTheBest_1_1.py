import urllib.request
import json
import os
import re
import shutil
import threading
import random
import ssl
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
from urllib.parse import quote

# directorio inicial de descarga
BASE_DIR = "Mist"


# Repositorios 
CONFIG = {
    "firmware": {"owner": "mist-devel", "repo": "mist-binaries", "sha": "875d39549d2e24edf289cdee026a8e0079e999b7", "path": "firmware"},
    "micros": {"owner": "Gehstock", "repo": "Mist_FPGA_Cores", "sha": "b704582b24527f68532cd6fa8aa1c65b6ae8a0af", "path": "Computer_MiST", "target": "Gehstock_computer"},
    "consolas": {"owner": "Gehstock", "repo": "Mist_FPGA_Cores", "sha": "b704582b24527f68532cd6fa8aa1c65b6ae8a0af", "path": "Console_MiST", "target": "Gehstock_console"},
    "devel_cores": {"owner": "mist-devel", "repo": "mist-binaries", "sha": "875d39549d2e24edf289cdee026a8e0079e999b7", "path": "cores", "target": "Mist_devel_cores"},
    "devel_arcades": {"owner": "mist-devel", "repo": "mist-binaries", "sha": "875d39549d2e24edf289cdee026a8e0079e999b7", "path": "cores/arcade", "target": "Mist_devel_arcades"},
    "tdelage": {"owner": "tdelage26", "repo": "mist-binaries", "sha": "4d483e910fc5c11c8e1b49b94aca3f3564b554ee", "path": "cores", "target": "tdelague_cores"}
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (MiST-Updater-v33)'}
ssl_context = ssl._create_unverified_context()

# Sprites de Invaders --- La tonteria mas grande del programa
SPRITES = [
    [[0,0,1,0,0,0,0,0,1,0,0],[0,0,0,1,0,0,0,1,0,0,0],[0,0,1,1,1,1,1,1,1,0,0],[0,1,1,0,1,1,1,0,1,1,0],[1,1,1,1,1,1,1,1,1,1,1],[1,0,1,1,1,1,1,1,1,0,1],[1,0,1,0,0,0,0,0,1,0,1],[0,0,0,1,1,0,1,1,0,0,0]],
    [[0,0,0,1,1,0,0,0],[0,0,1,1,1,1,0,0],[0,1,1,1,1,1,1,0],[1,1,0,1,1,0,1,1],[1,1,1,1,1,1,1,1,1,1],[0,0,1,0,0,1,0,0],[0,1,0,1,1,0,1,0],[1,0,1,0,0,1,0,1]],
    [[0,0,0,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,1,1,0],[1,1,1,1,1,1,1,1,1,1],[1,1,0,0,1,1,0,0,1,1],[1,1,1,1,1,1,1,1,1,1],[0,0,1,1,0,0,1,1,0,0],[0,1,1,0,1,1,0,1,1,0],[1,1,0,0,0,0,0,0,1,1]],
    [[0,0,1,0,0,0,0,0,1,0,0],[1,0,0,1,0,0,0,1,0,0,1],[1,0,1,1,1,1,1,1,1,0,1],[1,1,1,0,1,1,1,0,1,1,1],[1,1,1,1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,1,1,1,0],[0,0,1,0,0,0,0,0,1,0,0],[0,1,0,0,0,0,0,0,0,1,0]]
]

class MovingInvader:
    def __init__(self, sprite, canvas):
        self.canvas = canvas
        self.pixels = []
        self.x, self.y = random.randint(50, 400), random.randint(100, 400)
        self.dx, self.dy = random.choice([-2, 2]), random.choice([-2, 2])
        for r, row in enumerate(sprite):
            for c, val in enumerate(row):
                if val:
                    p = self.canvas.create_rectangle(0,0,0,0, fill='#00ff00', outline="")
                    self.pixels.append((p, c, r))
    def update(self):
        self.x += self.dx
        self.y += self.dy
        if self.x <= 0 or self.x >= 460: self.dx *= -1
        if self.y <= 0 or self.y >= 640: self.dy *= -1
        for p, cx, ry in self.pixels:
            self.canvas.coords(p, self.x+cx*3, self.y+ry*3, self.x+cx*3+3, self.y+ry*3+3)

# --- Funciones de Ventana ---
def show_text_window(content, title):
    top = tk.Toplevel(root); top.title(title); top.geometry("850x650"); top.configure(bg="#0a0a0a")
    frame = tk.Frame(top, bg="#00ff00", padx=1, pady=1); frame.pack(expand=True, fill="both", padx=15, pady=10)
    txt_area = scrolledtext.ScrolledText(frame, bg="black", fg="#00ff00", font=("Courier", 10), relief="flat")
    txt_area.pack(expand=True, fill="both")
    txt_area.insert(tk.END, content)
    txt_area.configure(state="disabled")
    tk.Button(top, text="[ CERRAR ]", command=top.destroy, bg='black', fg='#00ff00', font=("Courier", 9)).pack(pady=10)

# --- Lógica de Red ---
def safe_clear_dir(directory):
    full_path = os.path.join(BASE_DIR, directory)
    if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(full_path): os.makedirs(full_path, exist_ok=True); return
    for f in os.listdir(full_path):
        p = os.path.join(full_path, f)
        try:
            if os.path.isfile(p) or os.path.islink(p): os.unlink(p)
            elif os.path.isdir(p): shutil.rmtree(p)
        except: continue

def api_request(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
        return json.loads(response.read().decode())

def download_cores_logic(key):
    c = CONFIG[key]; t = c["target"]
    try:
        status_label.config(text=f"Analizando {t}...", fg="#ffff00")
        data = api_request(f"https://api.github.com/repos/{c['owner']}/{c['repo']}/git/trees/{c['sha']}?recursive=1")
        groups = {}
        for i in data.get('tree', []):
            path = i['path']
            if path.lower().endswith('.rbf') and path.startswith(c['path']):
                folder = os.path.dirname(path)
                if folder not in groups: groups[folder] = []
                groups[folder].append(i)
        lst = [sorted(groups[g], key=lambda x: x['path'])[-1] for g in groups]
        safe_clear_dir(t)
        for i, item in enumerate(lst):
            fname = os.path.basename(item['path'])
            url = f"https://raw.githubusercontent.com/{c['owner']}/{c['repo']}/{c['sha']}/{quote(item['path'])}"
            status_label.config(text=f"Bajando: {fname}", fg="#00ff00")
            with urllib.request.urlopen(url, context=ssl_context) as r, open(os.path.join(BASE_DIR, t, fname), 'wb') as f: shutil.copyfileobj(r, f)
            progress_var.set((i+1)/len(lst)*100); root.update_idletasks()
        status_label.config(text="Actualización completa", fg="#00ff00")
    except Exception as e: messagebox.showerror("Error", str(e))

def update_firmware():
    try:
        status_label.config(text="Buscando Firmware...", fg="#ffff00")
        c = CONFIG['firmware']
        data = api_request(f"https://api.github.com/repos/{c['owner']}/{c['repo']}/contents/{quote(c['path'])}?ref={c['sha']}")
        upg_files = [item for item in data if item['name'].endswith('.upg')]
        latest = max(upg_files, key=lambda f: f['name'])
        safe_clear_dir('firmware_Mist')
        with urllib.request.urlopen(latest['download_url'], context=ssl_context) as r, open(os.path.join(BASE_DIR, 'firmware_Mist', latest['name']), 'wb') as f: shutil.copyfileobj(r, f)
        progress_var.set(100); status_label.config(text="Firmware OK", fg="#00ff00")
    except Exception as e: messagebox.showerror("Error", str(e))

def thread_wrapper(f, *a): progress_var.set(0); threading.Thread(target=f, args=a, daemon=True).start()

# --- Interfaz Principal ---
root = tk.Tk()
root.title("Mist_the_Best")
root.geometry("500x680")
root.configure(bg='#0a0a0a')

canvas = tk.Canvas(root, width=500, height=680, bg='#0a0a0a', highlightthickness=0); canvas.place(x=0, y=0)
invaders = [MovingInvader(s, canvas) for s in SPRITES]

def animate():
    for inv in invaders: inv.update()
    root.after(35, animate)

clock_f = tk.Frame(root, bg='#00ff00', padx=1, pady=1); clock_f.place(relx=1.0, x=-15, y=15, anchor="ne")
clock_lbl = tk.Label(clock_f, text="", bg='black', fg='#00ff00', font=("Courier", 10, "bold"), padx=10, pady=4); clock_lbl.pack()
def update_clock(): clock_lbl.config(text=datetime.now().strftime("%Y-%m-%d\n%H:%M:%S")); root.after(1000, update_clock)

tk.Label(root, text="Mist_the_Best", font=("Courier", 24, "bold"), bg='#0a0a0a', fg='#00ff00').pack(pady=(40, 0))
tk.Label(root, text="downloader v1.1", font=("Courier", 14), bg='#0a0a0a', fg='#00ff00').pack(pady=(0, 10))

def btn(txt, cmd):
    if not txt: tk.Label(root, text="", bg='#0a0a0a').pack(pady=4); return
    f = tk.Frame(root, bg='#00ff00', padx=1, pady=1); f.pack(pady=4) 
    tk.Button(f, text=txt, command=cmd, bg='black', fg='#00ff00', width=30, relief='flat', font=("Courier", 10)).pack()

btn("[ ACTUALIZAR FIRMWARE ]", lambda: thread_wrapper(update_firmware))
btn("[ Mist_devel_cores ]", lambda: thread_wrapper(download_cores_logic, "devel_cores"))
btn("[ Mist_devel_arcades ]", lambda: thread_wrapper(download_cores_logic, "devel_arcades"))
btn("[ Gehstock_computer ]", lambda: thread_wrapper(download_cores_logic, "micros"))
btn("[ Gehstock_console ]", lambda: thread_wrapper(download_cores_logic, "consolas"))
btn("[ tdelage26_cores ]", lambda: thread_wrapper(download_cores_logic, "tdelage"))
btn("", None) 

btn("[ Instrucciones de uso ]", lambda: show_text_window(INSTRUCCIONES_HARDCODED, "Instrucciones"))
btn("[ Sobre la Mist / Mistica ]", lambda: show_text_window(MISTICA_INFO_HARDCODED, "Sobre la Mist / Mistica"))

# Botón Acerca de...
about_f = tk.Frame(root, bg='#00ff00', padx=1, pady=1); about_f.place(relx=0.95, rely=0.88, anchor="se")
tk.Button(about_f, text="Acerca de...", command=lambda: show_text_window(ACERCA_DE_HARDCODED, "Acerca de"), bg='black', fg='#00ff00', font=("Courier", 8), relief='flat').pack()

btn("[ SALIR ]", root.quit)

bottom_f = tk.Frame(root, bg='#0a0a0a'); bottom_f.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=(0, 10))
status_label = tk.Label(bottom_f, text="Sistema listo", bg='#0a0a0a', fg='#00ff00', font=("Courier", 9)); status_label.pack()
progress_var = tk.DoubleVar()
ttk.Progressbar(bottom_f, variable=progress_var, maximum=100).pack(fill=tk.X, pady=5)

update_clock(); animate()

# AQUI PONGO LOS TEXTOS EN VARIABLES, PARA IR MODIFICANDO.
# Sobre la Mistica

MISTICA_INFO_HARDCODED = """FPGA - Altera Cyclone III EP3C25:
---------------------------------

Elementos Lógicos (LEs): Cuenta con 24,624 elementos lógicos
Arquitectura basada en LUT + flip-flop (estilo clásico de Altera)
Memoria Embebida: Dispone de 594,432 bits de memoria interna (M9K blocks)
Multiplicadores Embebidos: Incluye 66 multiplicadores (18x18)
Gestión de Reloj: Posee 4 bucles de fijación de fase (PLLs)
Velocidades: Hasta 875 Mbps en interfaces diferenciales
Interfaces de memoria externa: DDR / DDR2 / SDR SDRAM / QDRII SRAM
Máx. I/O: hasta 215 
Bancos de I/O: 8
Voltaje de Operación: Funciona con un núcleo de baja potencia de 1.2V


Placa Mist:
-----------
SDRAM externa: 32 / 64 MB segun version (16-bit, 133 MHz)
Controlador auxiliar: MCU ARM: Atmel AT91SAM7S56 / S256:
            Gestión de I/O (USB, SD)
            Configuración del FPGA (bitstream loading)
            Menú OSD
            Carga de cores
Almacenamiento: Slot SD Card:
            Carga de Bitstreams (.rbf)
            Imágenes de disco (ADF, HDF, etc.)
Interfaces de entrada/salida
    Vídeo:VGA analógica 3×6 bits RGB → 18 bits color (~262k colores)
    Audio: Salida estéreo analógica (jack 3.5 mm)
    DAC tipo delta-sigma
    USB: 4× USB Host
    DB9: 2× puertos DB9 Estándar Atari / Commodore"""

# Acerca de.....

ACERCA_DE_HARDCODED = """Programa dedicado única y exclusivamente a la FPGA Mist (y Mistica).

Este programilla está hecho con fines lúdicos y con la intención de quien escribe
de ordenar y tener a mano la inforación disponible sobre la Mist (/Mistica).

No se tiene ninguna intención de ampliar a otras fpga's, solo nos gusta esta, la abuela!

**************************************************
Los repositorios utilizados hasta el momento son:
**************************************************

https://github.com/mist-devel/mist-binaries   
        (Firmware, Cores)

https://github.com/Gehstock/Mist_FPGA
        (Arcades, Computer, Console)

https://github.com/tdelage26/Mist_FPGA
        (Arcade, Computer, Console)
        
        
****************************************************
Los datos estan sacados de diferentes fuentes, entre otras:

 - la documentación contenida en imagenes i documentos del gran DrWho 
         ( https://github.com/Dalekamistoso/fpga-toolset )

 - foro retrowiki.es

 - canales de telegram de los que si que saben:  - SOC-ARM-EMULACION-FPGA
                                                 - MiST / Mistica / SiDi
                                                 - Comunidad POSEIDÓN


*****************************************************
si conoces repositorios donde haya algun core de Mist, o ves mejoras en la documentación, 
ruego colaboración para ir mejorando la aplicación!!!
 
https://github.com/armandcoloma/Mist-the-best-_-Updater

________________________
Actualizaciones:
    programa            ---> 14/04/2026
    base repositiorios  ---> 14/04/2026"""


# instrucciones carga de cores

INSTRUCCIONES_HARDCODED = """###################                    14/04/2026
## MIST/MISTICA ###                    ----------
###################

Esta información es actualizable a modo de resumen para mi.
Los datos estan sacados de diferentes fuentes, entre otras:

 - la documentación contenida en imagenes i documentos elaborados por DrWho
 - foro retrowiki.es
 - canales de telegram de los que si que saben: - SOC-ARM-EMULACION-FPGA
                                                 - MiST / Mistica / SiDi
                                                 - Comunidad POSEIDÓN

 -se agradecen colaboraciones!!!

###################
##    MICROS    ###
###################

###########################################################################################
Acorn Atom: 
###########################################################################################

VHD files:
1) mount VHD in OSD
2) hit SHIFT + F10 to mount VHD

###########################################################################################
Amiga CD32:
###########################################################################################

En OSD drives: 
* Pri.master: Fixed/HDD --> MEgaAGS.hdf i pri.slave: Fixed/HDD --> MegaAGS-Saves.hdf
* Sec. Master: Removable/CD : posar aquí l'arxiu *.chd

###########################################################################################
Amstrad CPC:files DSK, TAPE
###########################################################################################

DSK file-
1) load DSK through OSD
2) type CAT
3) type RUN"GAMENAME

TAPE file-
1) load CDT through OSD
2) type |TAPE
3) type RUN"
4) press any key to start the tape loading

Notes: When loading TAPE games, hitting CTRL+END will automatically type RUN" and press ENTER

###########################################################################################
Amstrad PCW: files DSK
###########################################################################################

DSK file-
1) load DSK through OSD
2) reset core

Notes: Some games require a boot disk, and then you load the next DSK when prompted to. Some 
games require a password. Set core to PAL, and for best compatibility set clockspeed to 4.00(1x) 
when loading.

###########################################################################################
Apple One
###########################################################################################

Para programas BASIC:

1.- Arrancar "BASIC_BIN_E000.prg" en el OSD
2.- Ejecutarlo con RUN y obtener E000R
3.- Resetear el Apple 
4.- Cargar el prg desde el OSD
5.- Teclear E2B3R 
6.- Teclear RUN

Para Applesoft (Microsoft):

1.- Arrancar "applesoft-sd_BIN_6000.prg" en el OSD
2.- Ejecutarlo con RUN y obtener 6000R
3.- Resetear el Apple 
4.- Cargar el prg desde el OSD
5.- Teclear 6003R
6.- Teclear RUN

###########################################################################################
Atari ST: files ST (disks), VHD
###########################################################################################

ST files config:
Memory:    1MB
TOS:    TOS v1.02 (1987)
Chipset:ST
Blitter:Off
Viking:    Off
Screen: Color
Border: Visible

STE files config: 
Memory: 4MB
TOS:    TOS v1.62 (1990)
Chipset:STE
Blitter:On
Viking:    Off
Screen:    Color
Border:    Visibile

ST (disks)
1) load ST through OSD
2) load ST disk 1 in A, disk 2 in B 
3) double click floppy disk drive and launch PRG or TOS
4) sometimes a soft reset is in order

VHD file config:
HDD0:    ST.dbug.Klaz.vhd 
Memory: 4MB
TOS:    TOS v1.62 (1989)
Chipset:STE
Blitter:On
Viking:    Off
Screen:    Color
Border:    Visibile

VHD
- Launch games on drive D: and E: root, and under D:\\KLAZ directory.  Double click to navigate 
directories as needed.  Atari ST executables have .PRG and .TOS extensions, those are what you
 want to run.
- For STE games change chipset to STE.

Notes: Rename IMG files to VHD. Sometimes a cold reboot is needed for this core currently. For 
some later VHD files, use TOS v2.06, and Chipset STE.

###########################################################################################
Aquarius: files BIN, and CAQ *
###########################################################################################

BIN file-
1) load BIN from OSD

CAQ file-
1) hit ENTER to get into basic
2) type CLOAD
3) hit ENTER to "Press <Play>"
4) load tape 1 of 2 CAQ from OSD
5) type RUN
6) hit ENTER to "Press <Play>"
7) load tape 2 of 2 CAQ from OSD
8) wait

Notes: Ctrl + Z = CLOAD shortcut

###########################################################################################
Archie: files DSK
###########################################################################################

DSK file-
1) load DSK from OSD
2) click on disk drive in bottom left corner
3) double click icon to start game

###########################################################################################
Atari 800: files ATR, ATX, and CAR
###########################################################################################

ATR file- 
1) load ATR from OSD
2) hit F10 to reset and load game

ATR file- (HDimages.zip collection)
1) load ATR from OSD
2) hit F10 to load MyPicoDos menu
3) Select game from menu and hit ENTER
Notes: Hit F10 to bring up MyPicoDos for HDimages.zip ATR files.

ATX file- 
1) load ATX from OSD
2) hit F10 to reset and load game

CAR file-
1) load CAR from OSD

Notes: Some games will require holding down F8 for a short while when pressing F10. It disables 
Atari BASIC, and some games need that.

###########################################################################################
BBC Micro
###########################################################################################

BBC Membrane Keyboard Mapping
Mapping the 58-key Spectrum Next keyboard to 74-key BBC Micro keyboard was somewhat of a challenge.

The mapping is as follows:

Spec Next Key  Beeb Key
BREAK  BREAK
EDIT  ESCAPE
TRUE VIDEO  TAB
INV VIDEO  COPY
CAPS LOCK  CAPS LOCK
GRAPH  CTRL
CAPS SHIFT  SHIFT
EXTEND  See below
SYMBOL SHIFT  See below
DELETE  DELETE
ENTER  RETURN
Up/Down/Left/Right  Up/Down/Left/Right
A-Z  A-Z
0-9  0-9
;  ; and +
"  : and *
,  , and <
.  . and >
This misses out the following Beeb keys:

@
? and =
^ and ~
/ and |
[ and {
] and }
_ and £
/ and ?
To access these, it's necessary to use the Spec Next SYMBOL SHIFT as a modifier, which operates 
exactly as it does in the Spec Next core. For example, SYMBOL SHIFT + L should give you =. i.e. 
just look for the key cap with the symbol character you need.

The EXTEND key is also used as a modifier to access the 10 red BBC function keys. For example, 
F1 is Extend + 1.

Finally, on the Membrane keyboard, the yellow NMI button in conjunction with a number key (0-9) 
selects a particular config key. For example, Config-1 is bound to Yellow NMI + 1.

###########################################################################################
BK0011M: files DSK
###########################################################################################

Para ejecutar un disco teclear: 000B  y luego seleccionar el ejecutable

###########################################################################################
Camputers Lynx: files TAP
###########################################################################################

TAP file-
1) load TAP from OSD
2) Some games autostart
3) type RUN and hit ENTER

Notes: F11 = Reset. If a game doesn't load in 48k mode, try 96k mode

###########################################################################################
Coleco ADAM: files DSK, DDP, COL, BIN, ROM, SG
###########################################################################################

DSK, DDP files-
1) load DSK or DDP from OSD
2) reset via OSD or button

COL, SG files-
1) load COL, BIN, ROM, SG from OSD
2) program auto starts

BIN, ROM files-
1) open OSD set MODE to Console
2) load BIN, ROM from OSD
3) reset via OSD or button

###########################################################################################
C16: files D64, BIN, PRG, and TAP
###########################################################################################

D64 file-
1) load D64 from OSD
2) type LOAD"*",8,1
3) type RUN

BIN file-
1) load BIN from OSD
2) press F2

PRG file-
1) load PRG from OSD
2) type RUN

TAP file-
1) type LOAD
2) load TAP from OSD
3) type RUN

###########################################################################################
C64: files D64, PRG, CRT, and TAP
###########################################################################################

D64 file-
Quick loading=
1) load D64 from OSD
2) press SHIFT+ESC to run the disk with JIFFY DOS
Manual Loading=
1) load D64 from OSD
2) type LOAD"*",8,1 
3) type RUN
Swap disk=
1) load disk 2 D64 from OSD

PRG file-
1) load PRG from OSD
2) hit the SPACE BAR to progress through l333t warez group

CRT file- 
1) load CRT from OSD

TAP file- 
1) Disable Jiffy DOS by setting Kernal to "Standard C64" in OSD
2) hit ALT+ESC or type LOAD and press Enter
3) load TAP from OSD

Notes: Set most games to PAL for improved compatibility. You may disable Jiffy DOS with @Q. 
RUN/STOP = ESC, Change Input = Scroll Lock. Tape sounds may be enabled from OSD.

###########################################################################################
CoCo3: files DSK, and CAS and CCC
###########################################################################################

DSK file- BAS is the executable
1) load DSK from OSD
2) type DIR
3) locate BAS file
4) type RUN"FILENAME

CAS file- BIN is the executable
1) load DSK from OSD
2) type DIR1
3) locate BIN file
4) type LOADM"FILENAME
5) type EXEC

CCC files
1) load CCC from OSD

Notes: BAS files are executables. Follow the first set of instructions for them. Other games 
only have a BIN file. Follow the second set of instructions for them. F10 resets the core. To 
load NitroOS-9 load DSK in OSD and then type DOS. Info on NitrOS-9 can be found at 
http://www.nitros9.org/battle.html

###########################################################################################
Dragon 32 / 64. 
###########################################################################################

Cargando desde disco y cassette 

DIR ----> lista el directorio, con la tecla BREAK interrumpes donde quieres parar.
BOOT ----> para hacer boot del OS9 , DragonDOS o de discos autoarrancables
(Cuidado porque hay variantes, como son : Dragon DOS, CumanaDOS, DeltaDOS, EurohardDOS, 
SuperDOS y DosPlus.)

y lo típico , LOAD "programa" y RUN. Si vais desde disco, si se carga BASIC desde cinta idem. 

Para cargar un programa en BASIC desde DISCO se hace:
LOAD "PROGRAMA.BAS"
RUN

Para cargar ficheros Binarios :
LOAD "PROGRAMA.BIN"
EXEC

o también:

LOADM "PROGRAMA.BIN"
EXEC

Aunque resulta que haciendo:
RUN "PROGRAMA.BAS"
Carga y ejecuta a la vez. Para ficheros binarios se hace igual.

Desde Cinta de Cassette.
CLOADM ""-----> carga código máquina 6809 desde cintas. Con el comando EXEC o RUN, ejecutas.
CLOAD "" ----> carga programas basic desde cintas

-Convertir arxius vdk a dsk Dragon
-------------------------------------------
# Iterar sobre todos los archivos .VDK en el directorio
 for archivo_vdk in *.VDK; do 

# Comprobar si hay archivos .VDK 
if [[ -f "$archivo_vdk" ]]; then 

# Crear el nombre del archivo .DSK 

archivo_dsk="${archivo_vdk%.VDK}.DSK" 

# Usar dd para convertir el archivo dd 

if="$archivo_vdk" of="$archivo_dsk" bs=1 skip=12 
echo "Convertido: $archivo_vdk a $archivo_dsk" 
ys else echo "No se encontraron archivos .VDK en el directorio."

###########################################################################################
Enterprise
###########################################################################################

Los comandos van con ":" al principio.

Ejemplos:
:g:               (equivalente a "g:")
: cd directorio (equivalente a "cd directorio")

Para ejecutar el soft incluido:

1.- Pulsar C+F9
2.- Pulsar F1 (o teclear START)

###########################################################################################
Interact Home Computer: files K7 , and CIN 
###########################################################################################

K7 file-
1) 
2) 
3) 

CIN file-
1) load CIN file through OSD
2) select PLAY in the OSD
3) type L if program does not automatically load 

Notes: Up on the mapped joystick often progresses the program

###########################################################################################
MSX: files ROM, DSK, and HDD load through boot.vhd. Hit F2 to start SofaRun
###########################################################################################

MSX Core Settings:
CPU speed:    Turbo(+F11)
CPU type:             R800
Slot1:        MegaSCC+ 1MB
Slot2:        MegaSCC2

ROM file- load from menu *
1) select rom from menu
2) hit ENTER to load ROM
3) hit ENTER to START ROM
Notes: If ROM does not load change change ROM settings under just that ROM from ESE SCC to 
OCM and relaunch

DSK file- 
1) select DSK from sofarrun menu
2) hit ENTER to load DSK
3) hit ENTER again to START DSK
Notes: To change disks hold down the number of the disk and hit the space bar.

HDD file-
1) select HDD folder from sofarun menu
2) locate BAT or COM file
3) hit ENTER to launch game

###########################################################################################
MulitComp: <no info>
###########################################################################################

###########################################################################################
Orao: files WAV, and TAP
###########################################################################################

TAP/WAV file-
1) type BC to load Basic
2) hit ENTER to bypass MEM SIZE
3) type LMEM "" to load program
4) open TAP/WAV from OSD

###########################################################################################
Oric: files DSK, and TAP
###########################################################################################

DSK files-
1) load DSK through OSD
2) hit F10
3) hit F11

TAP files-
1) load TAP through OSD
2) type CLOAD"
3) type RUN (if needed)

Notes: DSK files need to be formatted/converted. TOSEC currently is hit or miss on which files work.

###########################################################################################
PC8801mk2SR: files D88
###########################################################################################

PC8801mk2SR Core Settings:
Aspect ratio:    4:3
Mode:            N88V2
Speed:           4MHz
Basic Mode:      Terminal
Cols:            80
Lines:           25
Disk boot:       Enable
Disk motor save: Disable

###########################################################################################
D88 files-
###########################################################################################

1) hit F11 to pull up the SD Card Disk Emulation Utility
2) load F88 files by navigating to FDD 0: and hitting ENTER, then scroll over to FILE, select
D88 file, then hit ENTER
3) load additional disks in sequential FDD drives, IE disk 1 in FDD 0, disk 2 in FDD 1, etc.
4) select SAVE at the bottom of the screen
5) reset by selecting RESET in OSD or reloading the core

Notes:  This is a very early experimental core. Trust me and just wait for this to be tied 
into the main framework. 

PDP1: files PDP, RIM, and BIN
RIM file-
1) open OSD and enable RIM mode
2) load RIM file from OSD

###########################################################################################
PET2001: files PRG
###########################################################################################

PRG files-
1) load PRG through OSD
2) type RUN

###########################################################################################
Sinclair QL: per n-go
###########################################################################################
Copiar de la SD al disc dur virtual i arrencar amb el core de QL
- ew scopy;”nomarxiu.mdv nomarxiu.mdv”   (si es vol copiar del .WIN a la sd es 
    qcopy encomptes de scopy)
- lrun mountmdv
- dira File (_mdv):  -> escrivim el nom de l’arxiu, sin mdv
- dir mdv1_
- lrun mdv1_boot

Si los juegos te van demasiado rápido, ejecuta el comando “SLOW 5” antes de “LRUN win1_boot_juegos”

directoris:
     DDOWN name                      move to a sub-directory
     DUP                               move up through the tree
     DNEXT name                      move to another directory
                                                  at the same level

     MERGE name                      merge a SuperBASIC program
     MRUN name                       merge and run a SuperBASIC program

editor:
VIEW #chanel, nomarxiu

Commands:

     DIR #channel, name                drive statistics and list of files
     WDIR #channel, name              list of files

     STAT #channel, name                drive statistics
     WSTAT #channel, name              list of files and their statistics

     DELETE name                            delete a file
    *WDEL #channel, name                delete files

     COPY name TO name                         copy a file
     COPY_O name TO name                     copy a file (overwriting)
     COPY_N name TO name                    copy a file (without header)
     COPY_H name TO name                     copy a file (with header)
    *WCOPY #channel, name TO name           copy files
     SPL name TO name                            spool a file
     SPLF name TO name                       spool a file, <FF> at end

     RENAME name TO name                     rename a file
    *WREN #channel, name TO name            rename files

###########################################################################################
SharpMZ: files ROM
###########################################################################################

ROM file-
1) From the MiSTer GUI, set your Machine Model. The majority of games are MZ-700 as you can 
tell from the subfolder's name
2) Go to Tape Storage and select "Load direct to RAM" and select a game from the list. Note 
the "Exec Addr" number in "Tape Details"
3) Exit the GUI to the SharpMZ Monitor. Type J followed by the Exec Addr of the game you loaded. 
For example, Bomberman's Exec Addr is 1200, so to load it you type J1200

Notes: Not all tapes are valid. These will fail with a tape error

###########################################################################################
Sharp X68000: files D88, HDF, VHD
###########################################################################################

D88 files-
1) hit F11 to pull up the SD Card Disk Emulation Utility
2) load F88 files by navigating to FDD 0: and hitting ENTER, then scroll over to FILE, select 
D88 file, then hit ENTER
3) load additional disks in sequential FDD drives, IE disk 1 in FDD 0, disk 2 in FDD 1, etc.
4) set SRAM to 1MB or 2MB SRAM.dat file
5) select SAVE at the bottom of the screen
6) reset by selecting RESET in OSD or reloading the core

HDF files-
1) load HDF file in OSD
2) core should reset and self boot
3) if the core does not autoload, reset by selecting RESET in OSD or hitting the reset button

VHD files-
1) hit F11 to pull up the SD Card Disk Emulation Utility
2) load VHD files by navigating to HDD 0: and hitting ENTER, then scroll over to FILE, select 
VHD file, then hit ENTER
3) set SRAM to 1MB or 2MB SRAM.dat file
4) select SAVE at the bottom of the screen
5) reset by selecting RESET in OSD or reloading the core

###########################################################################################
TRS-80: files CAS
###########################################################################################

CAS file-
1) hit ENTER 
2) type SYSTEM
3) load CAS from OSD
4) type the first letter of the file you want to load
5) type /

Notes: hit ENTER after every step.
GH: https://github.com/MiSTer-devel/TRS-80_MiSTer

###########################################################################################
TSConf: files SCL, and TAP *
###########################################################################################

SCL file-
1) load game through wild commander interface
2) choose Drive A
3) choose reset to Basic 128
4) hit ENTER twice on the glitched screen to load game
5) to exit game and return to menu hit F11

TAP file- (takes a while)
1) load game through commander interface
2) hit ENTER to start TAP Mounter
3) choose Tape Loader
4) to exit game and return to menu hit F11

*Notes: ZX Spectrum clone with menu

###########################################################################################
Tatung Einstein: files DSK, and XBS
###########################################################################################

DSK file-
1) load DSK from OSD
2) hit CTRL+TAB to load DSK
3) type DIR
4) locate COM file
5) type COM file name without extension (IE ALICE for ALICE.COM)
6) press ENTER

XBS
1) load XBASIC DSK from OSD
2) hit CTRL+TAB to load DSK
3) type XBAS then hit ENTER
3) type LOAD"filename"
4) type RUN then hit ENTER

###########################################################################################
UK101: *
###########################################################################################

1) ALT + C for a Cold Start
2) Hit ENTER for both MEMORY SIZE and TERMINAL WIDTH

Notes: No UART support yet. Bootup choices below.
ALT + C = Cold Start
ALT + W = Warm Start
ALT + M = Monitor
ALT + D = Debug
Manual: http://uk101.sourceforge.net/docs/pdf/manual.pdf
UK101 FPGA Homepage: http://searle.x10host.com/uk101FPGA/index.html

###########################################################################################
Vic 20: files CRT, TAP, D64, G64, PRG, ROM
###########################################################################################

CRT file-
1) load CRT through OSD 
2) type LOAD"$",8
3) reset via OSD or button

TAP file-
1) type LOAD
2) load TAP through OSD
3) type RUN

D64 file-
1) load D64 through OSD 
2) type LOAD"$",8
3) type LIST
4) type LOAD"game name",8
5) type RUN

o també

1) load D64 through OSD 
2) type LOAD"*",8
3) type LIST
4) type RUN

Notes: Mega-Cart support added. "`" will go back to the main menu. Most games on MC. Load 
through OSD. lctrl + lalt + ralt will reset the system and keep the cartridge attached. You 
can truncate game names with *. Some games require unique expansion ram settings. Start 
unexpanded with all memory off.

###########################################################################################
ZX Spectrum: files TAP, TRD, and Z80
###########################################################################################

TAP file-
1) load TAP through OSD
2) select Tape Loader
3) wait...

TRD file-
1) enter TR-DOS from the menu
2) load TRD from OSD
3) hit R to autotype RUN
4) hit ENTER

Z80 Snapshot-
1) load Z80 through OSD
2) hit ENTER

###########################################################################################
ZX81:
###########################################################################################

1) load a .P file from OSD
2) press J, then Shift + P twice to make two " marks
3) hit ENTER

###########################################################################################
Computer cores with no prompt: (games load instantly from OSD or integrated menu)
###########################################################################################

-Apogee
-Apple II
-Jupiter
-MacPlus
-SamCoupe
-Specialist
-TI-99/4A
-Vector06"""

# A RODAR!! COJONES!

if __name__ == "__main__":
    root.mainloop()