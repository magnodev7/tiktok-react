try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog, ttk
    GUI_AVAILABLE = True
except Exception:
    GUI_AVAILABLE = False

import os, re
from datetime import datetime
from .paths import load_accounts, save_accounts, account_dirs
from .scheduler import TikTokScheduler
from .config import SCHEDULES, BASE_USER_DATA_DIR, BASE_VIDEO_DIR, BASE_POSTED_DIR

# GUI Tkinter (opcional)

def run_gui():
    if not GUI_AVAILABLE:
        print("GUI indisponível (tkinter não instalado).")
        return

    root = tk.Tk()
    root.title('Agendador TikTok')

    accounts = load_accounts()
    current_account = tk.StringVar(value=accounts[0])

    frame_conf = tk.LabelFrame(root, text="Configurações")
    frame_conf.grid(row=1, column=0, padx=10, pady=5, sticky="n")

    tk.Label(frame_conf, text="Conta TikTok:").grid(row=0, column=0, sticky="w")
    combo_accounts = ttk.Combobox(frame_conf, values=accounts, textvariable=current_account, state="readonly", width=18)
    combo_accounts.grid(row=0, column=1, sticky="ew")

    frame_videos = tk.LabelFrame(root, text="Vídeos para Postar")
    frame_videos.grid(row=1, column=1, padx=10, pady=5, sticky="n")
    video_list_var = tk.Variable(value=[])
    listbox_videos = tk.Listbox(frame_videos, listvariable=video_list_var, height=10, width=40)
    listbox_videos.grid(row=0, column=0)
    tk.Label(frame_videos, text="Vídeos na fila:").grid(row=1, column=0, sticky="w")
    label_video_count = tk.Label(frame_videos, text="0")
    label_video_count.grid(row=1, column=0, sticky="e")

    frame_logs = tk.LabelFrame(root, text="Logs")
    frame_logs.grid(row=2, column=1, padx=10, pady=5, sticky="n")
    text_logs = tk.Text(frame_logs, height=15, width=55, state=tk.DISABLED)
    text_logs.grid(row=0, column=0)

    frame_acao = tk.LabelFrame(root, text="Ações")
    frame_acao.grid(row=2, column=0, padx=10, pady=5, sticky="n")

    def log_to_text(msg):
        text_logs.config(state=tk.NORMAL)
        text_logs.insert(tk.END, msg + "\n")
        text_logs.see(tk.END)
        text_logs.config(state=tk.DISABLED)

    class TkSchedulerAdapter(TikTokScheduler):
        def __init__(self, account_name):
            super().__init__(account_name, logger=lambda m: log_to_text(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
            self.running = True
            self.scheduler_active = False

    scheduler = TkSchedulerAdapter(current_account.get())
    scheduler.initial_setup()

    def update_video_list_tk():
        _, vdir, _ = account_dirs(current_account.get())
        vids = [f for f in os.listdir(vdir) if f.lower().endswith((".mp4", ".mov", ".avi"))]
        video_list_var.set(vids)
        label_video_count.config(text=str(len(vids)))

    update_video_list_tk()

    def on_account_change(_=None):
        scheduler.stop()
        scheduler.__init__(current_account.get(), logger=scheduler._logger)  # rebind simples
        scheduler.initial_setup()
        update_video_list_tk()
        scheduler.log(f"🔄 Conta ativa: {current_account.get()}")

    combo_accounts.bind('<<ComboboxSelected>>', on_account_change)

    def on_start():
        btn_start.config(state=tk.DISABLED)
        btn_stop.config(state=tk.NORMAL)
        scheduler.start()

    def on_stop():
        btn_start.config(state=tk.NORMAL)
        btn_stop.config(state=tk.DISABLED)
        scheduler.stop()

    btn_start = tk.Button(frame_acao, text="Iniciar", bg="green", fg="white", command=on_start); btn_start.grid(row=0, column=0, sticky="ew")
    btn_stop  = tk.Button(frame_acao, text="Parar",  bg="red",   fg="white", state=tk.DISABLED, command=on_stop); btn_stop.grid(row=0, column=1, sticky="ew")

    status_var = tk.StringVar(value="Pronto")
    status_bar = tk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor="w", width=70)
    status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")

    def periodic_update():
        update_video_list_tk()
        status_var.set(datetime.now().strftime("Pronto - %H:%M:%S"))
        root.after(5000, periodic_update)
    periodic_update()

    root.mainloop()
