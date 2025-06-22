import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, font
import threading
import client
import queue

# Özelleştirilmiş giriş penceresi
class ThemedInputDialog:
    def __init__(self, parent, title, prompt, initialvalue=None, is_int=False):
        self.value = None
        self.is_int = is_int
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.configure(bg="#2e2c2c")
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.geometry("300x120")
        self.result = None

        label = tk.Label(self.top, text=prompt, bg="#2e2c2c", fg="#FFFFFF", font=("Helvetica", 10))
        label.pack(pady=(15, 5))

        self.entry = tk.Entry(self.top, bg="#2e2c2c", fg="#FFFFFF", insertbackground="#FFFFFF", font=("Helvetica", 10))
        self.entry.pack(pady=5, padx=20, fill=tk.X)
        if initialvalue is not None:
            self.entry.insert(0, str(initialvalue))
        self.entry.focus_set()

        button = tk.Button(self.top, text="Tamam", command=self.on_ok, bg="#FFB347", fg="#FFFFFF", activebackground="#FFB347", activeforeground="#FFFFFF", font=("Helvetica", 10, "bold"), relief=tk.FLAT)
        button.pack(pady=(10, 10))

        self.top.bind("<Return>", lambda event: self.on_ok())
        self.top.protocol("WM_DELETE_WINDOW", self.on_close)
        parent.wait_window(self.top)

    def on_ok(self):
        val = self.entry.get()
        if self.is_int:
            try:
                val = int(val)
            except ValueError:
                val = None
        self.result = val
        self.top.destroy()

    def on_close(self):
        self.result = None
        self.top.destroy()

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Uygulaması")
        self.root.configure(bg="#808080")

        # Fonts and Colors
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Helvetica", size=10)
        self.bold_font = font.Font(family="Helvetica", size=10, weight="bold")
        
        BG_COLOR = "#2e2c2c"  # Daha koyu gri arka plan
        TEXT_COLOR = "#FFFFFF"  # Beyaz yazı
        ENTRY_BG = "#2e2c2c"  # Daha koyu gri giriş alanı
        BUTTON_BG = "#FFB347"  # Soft turuncu buton
        BUTTON_FG = "#FFFFFF"  # Beyaz buton yazısı
        USER_LIST_BG = "#2e2c2c"  # Daha koyu gri kullanıcı listesi

        # --- Layout ---
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Left Frame (User List)
        left_frame = tk.Frame(self.root, bg=BG_COLOR, padx=10, pady=10)
        left_frame.grid(row=0, column=0, sticky="ns")

        user_label = tk.Label(left_frame, text="Çevrimiçi Kullanıcılar", font=self.bold_font, bg=BG_COLOR, fg=TEXT_COLOR)
        user_label.pack(pady=(0, 5))

        self.user_listbox = tk.Listbox(left_frame, selectmode=tk.MULTIPLE, exportselection=False, bg=USER_LIST_BG, fg=TEXT_COLOR, width=30, height=20, highlightbackground=BG_COLOR, selectbackground=BUTTON_BG, selectforeground=BUTTON_FG)
        self.user_listbox.pack(fill=tk.BOTH, expand=True)

        self.refresh_button = tk.Button(left_frame, text="Yenile", command=self.refresh_users, bg=BUTTON_BG, fg=BUTTON_FG, relief=tk.FLAT, activebackground=BUTTON_BG, activeforeground=BUTTON_FG)
        self.refresh_button.pack(pady=5, fill=tk.X)

        # Right Frame (Chat Area)
        right_frame = tk.Frame(self.root, bg=BG_COLOR)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        self.text_area = scrolledtext.ScrolledText(
            right_frame,
            state='disabled',
            wrap=tk.WORD,
            bg=ENTRY_BG,
            fg=TEXT_COLOR,
            font=("Helvetica", 10),
            insertbackground=TEXT_COLOR,
            highlightbackground=BG_COLOR,
            highlightcolor=BG_COLOR,
            borderwidth=2
        )
        self.text_area.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # Scrollbar'ı koyu gri yap
        for child in self.text_area.winfo_children():
            if isinstance(child, tk.Scrollbar):
                child.config(bg=BG_COLOR, troughcolor=BG_COLOR, activebackground=BG_COLOR, highlightbackground=BG_COLOR)

        # --- Message Entry ---
        entry_frame = tk.Frame(right_frame, bg=BG_COLOR)
        entry_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 0))
        entry_frame.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(entry_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=("Helvetica", 10), insertbackground=TEXT_COLOR)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(entry_frame, text="Gönder", command=self.send_message, bg=BUTTON_BG, fg=BUTTON_FG, relief=tk.FLAT, activebackground=BUTTON_BG, activeforeground=BUTTON_FG)
        self.send_button.grid(row=0, column=1)

        # --- Tag Configurations for Text Area ---
        self.text_area.tag_configure('me', foreground=BUTTON_BG, font=self.bold_font)
        self.text_area.tag_configure('other', foreground=TEXT_COLOR, font=self.bold_font)
        self.text_area.tag_configure('message', foreground=TEXT_COLOR)
        self.text_area.tag_configure('system', foreground=TEXT_COLOR, font=("Helvetica", 9, "italic"))

        # --- Initialization ---
        self.client = None
        self.username = ThemedInputDialog(self.root, "Kullanıcı Adı", "Kullanıcı adınızı girin:").result
        if not self.username:
            self.root.destroy()
            return

        self.root.title(f"Chat Uygulaması - {self.username}")
            
        self.server_addr = ThemedInputDialog(self.root, "Sunucu Adresi", "Sunucu adresini girin:", initialvalue="localhost").result
        self.port = ThemedInputDialog(self.root, "Port", "Sunucu portunu girin:", initialvalue=15000, is_int=True).result
        
        self.msg_queue = queue.Queue()
        self.user_list = []
        if self.username and self.server_addr and self.port:
            self.connect_to_server()
            self.root.after(100, self.check_messages)
        else:
            self.root.destroy()

    def connect_to_server(self):
        ClientClass = client.Client
        self.client = ClientClass(self.username, self.server_addr, self.port, 3, on_message=self.display_message)
        
        threading.Thread(target=self.client.start, daemon=True).start()
        self.display_message("Sunucuya bağlanılıyor...", 'system')
        self.root.after(500, self.refresh_users)

    def send_message(self, event=None):
        msg = self.entry.get()
        if msg:
            selected_indices = self.user_listbox.curselection()
            
            if not selected_indices:
                selected_users = ['all']
                display_text = f"msg:{self.username} (Herkese):{msg}"
            else:
                selected_users = [self.user_listbox.get(i) for i in selected_indices]
                display_text = f"msg:{self.username} (Özel):{msg}"

            self.msg_queue.put(display_text)
            
            user_count = len(selected_users)
            user_str = ','.join(selected_users)
            full_msg = f"msg {user_count} {user_str} {msg}"
            self.client.msg(full_msg)
            self.entry.delete(0, tk.END)

    def display_message(self, message, tag_override=None):
        if tag_override:
            self.text_area.config(state='normal')
            self.text_area.insert(tk.END, message + "\n", tag_override)
            self.text_area.config(state='disabled')
            self.text_area.see(tk.END)
            return

        if message.startswith("list: "):
            users = message[6:].strip().split()
            self.user_list = sorted([u for u in users if u != self.username])
            self.update_user_listbox()
        elif message.startswith("msg:"):
            try:
                _, sender, content = message.split(':', 2)
                self.text_area.config(state='normal')
                if sender.startswith(self.username): # Handles "(Herkese)" or "(Özel)"
                    context = ""
                    if "(Herkese)" in sender:
                        context = " (Herkese)"
                    elif "(Özel)" in sender:
                        context = " (Özel)"
                    self.text_area.insert(tk.END, f"Siz{context}: ", 'me')
                else:
                    self.text_area.insert(tk.END, f"{sender}: ", 'other')
                self.text_area.insert(tk.END, f"{content}\n", 'message')
                self.text_area.config(state='disabled')
                self.text_area.see(tk.END)
            except ValueError:
                 self.display_message(f"Alınan mesaj formatı bozuk: {message}", 'system')
        else:
            self.display_message(message, 'system')

    def check_messages(self):
        while not self.msg_queue.empty():
            message = self.msg_queue.get()
            self.display_message(message)
        self.root.after(100, self.check_messages)

    def refresh_users(self):
        self.display_message("Kullanıcı listesi yenileniyor...", 'system')
        self.client.list()

    def update_user_listbox(self):
        current_selection = self.user_listbox.curselection()
        self.user_listbox.delete(0, tk.END)
        for user in self.user_list:
            self.user_listbox.insert(tk.END, user)
        # Restore selection
        for i in current_selection:
            if self.user_listbox.get(i) in self.user_list:
                self.user_listbox.select_set(i)

if __name__ == "__main__":
    root = tk.Tk()
    gui = ChatGUI(root)
    root.mainloop() 