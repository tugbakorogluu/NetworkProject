import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import threading
import client_1
import client_2
import queue

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("UDP Chat Client")

        self.text_area = scrolledtext.ScrolledText(root, state='disabled', width=50, height=20)
        self.text_area.pack(padx=10, pady=10)

        # Kullanıcı listesi
        self.user_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, exportselection=False, width=30, height=8)
        self.user_listbox.pack(padx=10, pady=(0,10))

        self.refresh_button = tk.Button(root, text="Kullanıcıları Yenile", command=self.refresh_users)
        self.refresh_button.pack(pady=(0,10))

        self.entry = tk.Entry(root, width=40)
        self.entry.pack(side=tk.LEFT, padx=(10,0), pady=(0,10))
        self.entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(root, text="Gönder", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(5,10), pady=(0,10))

        self.client = None
        self.username = simpledialog.askstring("Kullanıcı Adı", "Kullanıcı adınızı girin:")
        self.port = simpledialog.askinteger("Port", "Sunucu portunu girin:", initialvalue=5000)
        self.server_choice = simpledialog.askinteger("Sunucu Seçimi", "Lütfen sunucu seçin (1 veya 2):", minvalue=1, maxvalue=2)
        
        self.msg_queue = queue.Queue()
        self.user_list = []
        if self.username and self.port and self.server_choice:
            self.connect_to_server()
            self.root.after(100, self.check_messages)
        else:
            self.root.destroy()

    def connect_to_server(self):
        if self.server_choice == 1:
            self.client = client_1.Client(self.username, "localhost", self.port, 3, on_message=self.display_message)
        elif self.server_choice == 2:
            self.client = client_2.Client(self.username, "localhost", self.port, 3, on_message=self.display_message)
        
        if self.client:
            threading.Thread(target=self.client.start, daemon=True).start()
            self.root.after(500, self.refresh_users)  # Otomatik ilk kullanıcı listesini al
        else:
            messagebox.showerror("Hata", "Geçersiz sunucu seçimi.")
            self.root.destroy()

    def send_message(self, event=None):
        msg = self.entry.get()
        if msg:
            selected_indices = self.user_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("Uyarı", "Lütfen en az bir kullanıcı seçin!")
                return

            # Display the sent message in the user's own chat window
            display_text = f"msg: {self.username}: {msg}"
            self.msg_queue.put(display_text)
            
            selected_users = [self.user_listbox.get(i) for i in selected_indices]
            user_count = len(selected_users)
            user_str = ','.join(selected_users)
            full_msg = f"msg {user_count} {user_str} {msg}"
            self.client.msg(full_msg)
            self.entry.delete(0, tk.END)

    def display_message(self, message):
        # Kullanıcı listesini güncelle
        if message.startswith("list: "):
            users = message[6:].strip().split()
            self.user_list = [u for u in users if u != self.username]  # Kendini listeden çıkar
            self.update_user_listbox()
        # Mesajı ekrana yaz
        self.msg_queue.put(message)

    def check_messages(self):
        while not self.msg_queue.empty():
            message = self.msg_queue.get()
            self.text_area.config(state='normal')
            self.text_area.insert(tk.END, message + "\n")
            self.text_area.config(state='disabled')
            self.text_area.see(tk.END)
        self.root.after(100, self.check_messages)

    def refresh_users(self):
        self.client.list()

    def update_user_listbox(self):
        self.user_listbox.delete(0, tk.END)
        for user in self.user_list:
            self.user_listbox.insert(tk.END, user)

if __name__ == "__main__":
    root = tk.Tk()
    gui = ChatGUI(root)
    root.mainloop() 