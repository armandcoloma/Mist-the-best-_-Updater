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

# --- Importación de Pillow ---
try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Error", "Instala Pillow: pip install Pillow")
    raise

# --- Configuración de Directorios ---
BASE_DIR = "Mist"
DATA_DIR = "data"  # Directorio para archivos locales (.txt, .jpg)

# Crear carpeta data si no existe
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- Configuración de Repositorios ---
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

def set_window_icon(window):
    """Asigna el icono buscando la imagen en la carpeta /data"""
    try:
        icon_path = os.path.join(DATA_DIR, "Placa_mist.jpg")
        icon_img = Image.open(icon_path)
        photo = ImageTk.PhotoImage(icon_img)
        window.wm_iconphoto(True, photo)
    except:
        pass

def show_txt_content(filename, title):
    """Lee archivos .txt desde la carpeta /data"""
    full_path = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(full_path):
        with open(full_path, "w", encoding="utf-8") as f: 
            f.write(f"--- {title} ---\nArchivo creado en {DATA_DIR}. Edítalo para añadir contenido.")
    
    try:
        with open(full_path, "r", encoding="utf-8") as f: 
            content = f.read()
    except: 
        return
    
    top = tk.Toplevel(root)
    top.title(title)
    top.geometry("800x500")
    top.configure(bg="#0a0a0a")
    set_window_icon(top)
    
    frame = tk.Frame(top, bg="#00ff00", padx=1, pady=1)
    frame.pack(expand=True, fill="both", padx=15, pady=10)
    
    txt_area = scrolledtext.ScrolledText(frame, bg="black", fg="#00ff00", font=("Courier", 10), relief="flat")
    txt_area.pack(expand=True, fill="both")
    txt_area.insert(tk.END, content)
    txt_area.configure(state="disabled")
    
    close_f = tk.Frame(top, bg='#00ff00', padx=1, pady=1)
    close_f.pack(pady=(0, 15))
    tk.Button(close_f, text="[ CERRAR ]", command=top.destroy, bg='black', fg='#00ff00', font=("Courier", 9)).pack()

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
            fname = os.path.basename(item['path']); url = f"https://raw.githubusercontent.com/{c['owner']}/{c['repo']}/{c['sha']}/{quote(item['path'])}"
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

# --- GUI ---
root = tk.Tk()
root.title("Mist_the_Best")
root.geometry("500x680")
root.configure(bg='#0a0a0a')

# Cargar icono desde /data
set_window_icon(root)

canvas = tk.Canvas(root, width=500, height=680, bg='#0a0a0a', highlightthickness=0); canvas.place(x=0, y=0)

# Imagen miniaturizada en la UI desde /data
try:
    img_path = os.path.join(DATA_DIR, "Placa_mist.jpg")
    pil_image = Image.open(img_path)
    pil_small = pil_image.resize((50, 50), Image.Resampling.LANCZOS)
    mist_img = ImageTk.PhotoImage(pil_small)
    img_label = tk.Label(root, image=mist_img, bg='#0a0a0a')
    img_label.image = mist_img
    img_label.place(relx=0.0, x=15, y=15, anchor="nw")
except Exception as e:
    print(f"Error imagen UI (buscando en {DATA_DIR}): {e}")

# Reloj
clock_f = tk.Frame(root, bg='#00ff00', padx=1, pady=1); clock_f.place(relx=1.0, x=-15, y=15, anchor="ne")
clock_lbl = tk.Label(clock_f, text="", bg='black', fg='#00ff00', font=("Courier", 10, "bold"), padx=10, pady=4); clock_lbl.pack()
def update_clock(): clock_lbl.config(text=datetime.now().strftime("%Y-%m-%d\n%H:%M:%S")); root.after(1000, update_clock)

tk.Label(root, text="Mist_the_Best", font=("Courier", 24, "bold"), bg='#0a0a0a', fg='#00ff00').pack(pady=(50, 0))
tk.Label(root, text="downloader", font=("Courier", 14), bg='#0a0a0a', fg='#00ff00').pack(pady=(0, 10))

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
btn("[ Instrucciones de uso ]", lambda: show_txt_content("instrucciones.txt", "Instrucciones"))
btn("[ Sobre la Mist / Mistica ]", lambda: show_txt_content("Mistica.txt", "Sobre la Mist / Mistica"))

exit_f = tk.Frame(root, bg='#00ff00', padx=1, pady=1); exit_f.pack(pady=(25, 5)) 
tk.Button(exit_f, text="[ SALIR ]", command=root.quit, bg='black', fg='#00ff00', width=30, relief='flat', font=("Courier", 10)).pack()

about_f = tk.Frame(root, bg='#00ff00', padx=1, pady=1); about_f.place(relx=0.95, rely=0.88, anchor="se")
tk.Button(about_f, text="Acerca de...", command=lambda: show_txt_content("acercade.txt", "Acerca de"), bg='black', fg='#00ff00', font=("Courier", 8), relief='flat').pack()

bottom_f = tk.Frame(root, bg='#0a0a0a'); bottom_f.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=(0, 10))
status_label = tk.Label(bottom_f, text="Sistema listo", bg='#0a0a0a', fg='#00ff00', font=("Courier", 9)); status_label.pack()
progress_var = tk.DoubleVar(); style = ttk.Style(); style.theme_use('default')
style.configure("green.Horizontal.TProgressbar", background='#00ff00', troughcolor='#111', thickness=10)
ttk.Progressbar(bottom_f, variable=progress_var, maximum=100, style="green.Horizontal.TProgressbar").pack(fill=tk.X, pady=5)

update_clock(); root.mainloop()