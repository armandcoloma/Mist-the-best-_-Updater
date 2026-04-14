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
from tkinter import messagebox, ttk
from urllib.parse import quote

# --- Configuración de Repositorios ---
CONFIG = {
    "firmware": {"owner": "mist-devel", "repo": "mist-binaries", "sha": "875d39549d2e24edf289cdee026a8e0079e999b7", "path": "firmware"},
    "micros": {"owner": "Gehstock", "repo": "Mist_FPGA_Cores", "sha": "b704582b24527f68532cd6fa8aa1c65b6ae8a0af", "path": "Computer_MiST", "target": "Gehstock_computer"},
    "consolas": {"owner": "Gehstock", "repo": "Mist_FPGA_Cores", "sha": "b704582b24527f68532cd6fa8aa1c65b6ae8a0af", "path": "Console_MiST", "target": "Gehstock_console"},
    "devel_cores": {"owner": "mist-devel", "repo": "mist-binaries", "sha": "875d39549d2e24edf289cdee026a8e0079e999b7", "path": "cores", "target": "Mist_devel_cores"},
    "devel_arcades": {"owner": "mist-devel", "repo": "mist-binaries", "sha": "875d39549d2e24edf289cdee026a8e0079e999b7", "path": "cores/arcade", "target": "Mist_devel_arcades"}
}

# --- Directorio Base ---
BASE_DIR = "Mist"

HEADERS = {'User-Agent': 'Mozilla/5.0 (MiST-Updater-v33)'}
ssl_context = ssl._create_unverified_context()

# --- Sprites (Marcianos) ---
SPRITES = [
    [[0,0,1,0,0,0,0,0,1,0,0],[0,0,0,1,0,0,0,1,0,0,0],[0,0,1,1,1,1,1,1,1,0,0],[0,1,1,0,1,1,1,0,1,1,0],[1,1,1,1,1,1,1,1,1,1,1],[1,0,1,1,1,1,1,1,1,0,1],[1,0,1,0,0,0,0,0,1,0,1],[0,0,0,1,1,0,1,1,0,0,0]],
    [[0,0,0,1,1,0,0,0],[0,0,1,1,1,1,0,0],[0,1,1,1,1,1,1,0],[1,1,0,1,1,0,1,1],[1,1,1,1,1,1,1,1,1,1],[0,0,1,0,0,1,0,0],[0,1,0,1,1,0,1,0],[1,0,1,0,0,1,0,1]],
    [[0,0,0,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,1,1,0],[1,1,1,1,1,1,1,1,1,1],[1,1,0,0,1,1,0,0,1,1],[1,1,1,1,1,1,1,1,1,1],[0,0,1,1,0,0,1,1,0,0],[0,1,1,0,1,1,0,1,1,0],[1,1,0,0,0,0,0,0,1,1]],
    [[0,0,1,0,0,0,0,0,1,0,0],[1,0,0,1,0,0,0,1,0,0,1],[1,0,1,1,1,1,1,1,1,0,1],[1,1,1,0,1,1,1,0,1,1,1],[1,1,1,1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,1,1,1,0],[0,0,1,0,0,0,0,0,1,0,0],[0,1,0,0,0,0,0,0,0,1,0]]
]

# --- Lógica de Archivos y Red ---
def safe_clear_dir(directory):
    full_path = os.path.join(BASE_DIR, directory)
    if not os.path.exists(BASE_DIR): 
        os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(full_path): 
        os.makedirs(full_path, exist_ok=True)
        return
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
                if 'old' in path.lower().split('/'): continue
                folder = os.path.dirname(path)
                if folder not in groups: groups[folder] = []
                groups[folder].append(i)
        lst = [sorted(groups[g], key=lambda x: x['path'])[-1] for g in groups]
        if not lst: return
        safe_clear_dir(t)
        for i, item in enumerate(lst):
            fname = os.path.basename(item['path'])
            url = f"https://raw.githubusercontent.com/{c['owner']}/{c['repo']}/{c['sha']}/{quote(item['path'])}"
            status_label.config(text=f"Bajando: {fname}", fg="#00ff00")
            save_path = os.path.join(BASE_DIR, t, fname)
            with urllib.request.urlopen(url, context=ssl_context) as r, open(save_path, 'wb') as f:
                shutil.copyfileobj(r, f)
            progress_var.set((i+1)/len(lst)*100); root.update_idletasks()
        status_label.config(text="Actualización completa", fg="#00ff00")
    except Exception as e: messagebox.showerror("Error", str(e))

def update_firmware():
    try:
        status_label.config(text="Buscando Firmware...", fg="#ffff00")
        c = CONFIG['firmware']
        data = api_request(f"https://api.github.com/repos/{c['owner']}/{c['repo']}/contents/{quote(c['path'])}?ref={c['sha']}")
        upg_files = [item for item in data if item['name'].endswith('.upg')]
        def extract_date(name):
            match = re.search(r'firmware_(\d{6})', name)
            return datetime.strptime(match.group(1), '%y%m%d') if match else datetime.min
        latest = max(upg_files, key=lambda f: extract_date(f['name']))
        target_sub = 'firmware_Mist' # También con M mayúscula por consistencia
        safe_clear_dir(target_sub)
        save_path = os.path.join(BASE_DIR, target_sub, latest['name'])
        with urllib.request.urlopen(latest['download_url'], context=ssl_context) as r, open(save_path, 'wb') as f:
            shutil.copyfileobj(r, f)
        progress_var.set(100); status_label.config(text="Firmware OK", fg="#00ff00")
    except Exception as e: messagebox.showerror("Error", str(e))

def thread_wrapper(f, *a):
    progress_var.set(0)
    threading.Thread(target=f, args=a, daemon=True).start()

# --- GUI ---
root = tk.Tk(); root.title("Mist_the_Best"); root.geometry("500x680"); root.configure(bg='#0a0a0a')
canvas = tk.Canvas(root, width=500, height=680, bg='#0a0a0a', highlightthickness=0); canvas.place(x=0, y=0)

class MovingInvader:
    def __init__(self, sprite):
        self.pixels = []; self.x, self.y = random.randint(50, 400), random.randint(100, 400)
        self.dx, self.dy = random.choice([-2, 2]), random.choice([-2, 2])
        for r, row in enumerate(sprite):
            for c, val in enumerate(row):
                if val: p = canvas.create_rectangle(0,0,0,0, fill='#002800', outline=""); self.pixels.append((p, c, r))
    def update(self):
        self.x += self.dx; self.y += self.dy
        if self.x <= 0 or self.x >= 460: self.dx *= -1
        if self.y <= 0 or self.y >= 640: self.dy *= -1
        for p, cx, ry in self.pixels: canvas.coords(p, self.x+cx*3, self.y+ry*3, self.x+cx*3+3, self.y+ry*3+3)

invaders = [MovingInvader(s) for s in SPRITES]
def animate():
    for inv in invaders: inv.update()
    root.after(35, animate)

# --- Reloj y Cabecera ---
clock_f = tk.Frame(root, bg='#00ff00', padx=1, pady=1); clock_f.pack(side=tk.TOP, anchor="e", padx=20, pady=10)
clock_lbl = tk.Label(clock_f, text="", bg='black', fg='#00ff00', font=("Courier", 10, "bold"), padx=10, pady=4, justify="center"); clock_lbl.pack()
def update_clock(): clock_lbl.config(text=datetime.now().strftime("%Y-%m-%d\n%H:%M:%S")); root.after(1000, update_clock)

tk.Label(root, text="Mist_the_Best", font=("Courier", 24, "bold"), bg='#0a0a0a', fg='#00ff00').pack(pady=(5, 0))
tk.Label(root, text="downloader", font=("Courier", 14), bg='#0a0a0a', fg='#00ff00').pack(pady=(0, 5))

# --- Botones ---
def btn(txt, cmd):
    f = tk.Frame(root, bg='#00ff00', padx=1, pady=1); f.pack(pady=4) 
    tk.Button(f, text=txt, command=cmd, bg='black', fg='#00ff00', width=30, relief='flat', font=("Courier", 10)).pack()

btn("[ ACTUALIZAR FIRMWARE ]", lambda: thread_wrapper(update_firmware))
btn("[ Gehstock_computer ]", lambda: thread_wrapper(download_cores_logic, "micros"))
btn("[ Gehstock_console ]", lambda: thread_wrapper(download_cores_logic, "consolas"))
btn("[ Mist_devel_cores ]", lambda: thread_wrapper(download_cores_logic, "devel_cores"))
btn("[ Mist_devel_arcades ]", lambda: thread_wrapper(download_cores_logic, "devel_arcades"))
for _ in range(4): btn("[ añadir repositorio ]", None)

# --- Opción SALIR ---
exit_f = tk.Frame(root, bg='#00ff00', padx=1, pady=1)
exit_f.pack(pady=(35, 10)) 
tk.Button(exit_f, text="[ SALIR ]", command=root.quit, bg='black', fg='#00ff00', width=30, relief='flat', font=("Courier", 10), activebackground='#ff0000').pack()

# --- Barra de Estado Inferior ---
bottom_f = tk.Frame(root, bg='#0a0a0a'); bottom_f.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=10)
status_label = tk.Label(bottom_f, text="Sistema listo", bg='#0a0a0a', fg='#00ff00', font=("Courier", 9)); status_label.pack()
progress_var = tk.DoubleVar(); style = ttk.Style(); style.theme_use('default')
style.configure("green.Horizontal.TProgressbar", background='#00ff00', troughcolor='#111', thickness=10)
ttk.Progressbar(bottom_f, variable=progress_var, maximum=100, style="green.Horizontal.TProgressbar").pack(fill=tk.X, pady=5)

update_clock(); animate(); root.mainloop()