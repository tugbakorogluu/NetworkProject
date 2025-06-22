import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, font, ttk
import threading
import client
import queue
import time

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Uygulaması")
        self.root.configure(bg="#F0F0F0")

        # Fonts and Colors
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Helvetica", size=10)
        self.bold_font = font.Font(family="Helvetica", size=10, weight="bold")
        
        BG_COLOR = "#F0F0F0"
        TEXT_COLOR = "#000000"
        ENTRY_BG = "#FFFFFF"
        BUTTON_BG = "#0078D4"
        BUTTON_FG = "#FFFFFF"
        USER_LIST_BG = "#FFFFFF"
        PERF_BG = "#E8F4FD"
        PERF_BORDER = "#0078D4"

        # --- Layout ---
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Left Frame (User List)
        left_frame = tk.Frame(self.root, bg=BG_COLOR, padx=10, pady=10)
        left_frame.grid(row=0, column=0, sticky="ns")

        user_label = tk.Label(left_frame, text="Çevrimiçi Kullanıcılar", font=self.bold_font, bg=BG_COLOR)
        user_label.pack(pady=(0, 5))

        self.user_listbox = tk.Listbox(left_frame, selectmode=tk.MULTIPLE, exportselection=False, bg=USER_LIST_BG, width=30, height=20)
        self.user_listbox.pack(fill=tk.BOTH, expand=True)

        self.refresh_button = tk.Button(left_frame, text="Yenile", command=self.refresh_users, bg=BUTTON_BG, fg=BUTTON_FG, relief=tk.FLAT)
        self.refresh_button.pack(pady=5, fill=tk.X)

        # Performance Monitor Frame
        perf_frame = tk.LabelFrame(left_frame, text="Performans Monitörü", font=self.bold_font, bg=BG_COLOR, fg=TEXT_COLOR)
        perf_frame.pack(pady=10, fill=tk.X)

        # Performance Stats Labels
        self.perf_labels = {}
        perf_stats = [
            ("Mesaj/sn:", "msg_per_sec", "0.0"),
            ("Ortalama Gecikme:", "avg_latency", "0 ms"),
            ("Paket Kaybı:", "packet_loss", "0%"),
            ("Gönderilen:", "sent_count", "0"),
            ("Alınan:", "received_count", "0")
        ]

        for i, (label_text, key, default_value) in enumerate(perf_stats):
            label = tk.Label(perf_frame, text=label_text, bg=BG_COLOR, font=("Helvetica", 8))
            label.grid(row=i, column=0, sticky="w", padx=5, pady=1)
            
            value_label = tk.Label(perf_frame, text=default_value, bg=BG_COLOR, font=("Helvetica", 8, "bold"), fg="#0078D4")
            value_label.grid(row=i, column=1, sticky="e", padx=5, pady=1)
            
            self.perf_labels[key] = value_label

        # Performance Buttons
        perf_buttons_frame = tk.Frame(perf_frame, bg=BG_COLOR)
        perf_buttons_frame.grid(row=len(perf_stats), column=0, columnspan=2, pady=5, sticky="ew")

        self.perf_report_button = tk.Button(perf_buttons_frame, text="Detaylı Rapor", 
                                          command=self.show_performance_report, 
                                          bg="#28A745", fg="white", relief=tk.FLAT, font=("Helvetica", 8))
        self.perf_report_button.pack(fill=tk.X, pady=1)

        self.perf_reset_button = tk.Button(perf_buttons_frame, text="İstatistikleri Sıfırla", 
                                         command=self.reset_performance_stats, 
                                         bg="#DC3545", fg="white", relief=tk.FLAT, font=("Helvetica", 8))
        self.perf_reset_button.pack(fill=tk.X, pady=1)

        # Right Frame (Chat Area)
        right_frame = tk.Frame(self.root, bg=BG_COLOR)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        self.text_area = scrolledtext.ScrolledText(right_frame, state='disabled', wrap=tk.WORD, bg=ENTRY_BG, font=("Helvetica", 10))
        self.text_area.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # --- Message Entry ---
        entry_frame = tk.Frame(right_frame, bg=BG_COLOR)
        entry_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        entry_frame.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(entry_frame, bg=ENTRY_BG, font=("Helvetica", 10))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(entry_frame, text="Gönder", command=self.send_message, bg=BUTTON_BG, fg=BUTTON_FG, relief=tk.FLAT)
        self.send_button.grid(row=0, column=1)

        # --- Tag Configurations for Text Area ---
        self.text_area.tag_configure('me', foreground="#0078D4", font=self.bold_font)
        self.text_area.tag_configure('other', foreground="#000000", font=self.bold_font)
        self.text_area.tag_configure('message', foreground="#333333")
        self.text_area.tag_configure('system', foreground="#666666", font=("Helvetica", 9, "italic"))
        self.text_area.tag_configure('performance', foreground="#28A745", font=("Helvetica", 9, "italic"))

        # --- Initialization ---
        self.client = None
        self.username = simpledialog.askstring("Kullanıcı Adı", "Kullanıcı adınızı girin:")
        if not self.username:
            self.root.destroy()
            return

        self.root.title(f"Chat Uygulaması - {self.username}")
            
        self.server_addr = simpledialog.askstring("Sunucu Adresi", "Sunucu adresini girin:", initialvalue="localhost")
        self.port = simpledialog.askinteger("Port", "Sunucu portunu girin:", initialvalue=15000)
        
        self.msg_queue = queue.Queue()
        self.user_list = []
        
        if self.username and self.server_addr and self.port:
            self.connect_to_server()
            self.root.after(100, self.check_messages)
            # Start performance monitoring updates
            self.root.after(1000, self.update_performance_display)
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
        if self.client:
            self.display_message("Kullanıcı listesi yenileniyor...", 'system')
            self.client.list()

    def update_user_listbox(self):
        current_selection = self.user_listbox.curselection()
        self.user_listbox.delete(0, tk.END)
        for user in self.user_list:
            self.user_listbox.insert(tk.END, user)
        # Restore selection
        for i in current_selection:
            if i < len(self.user_list):
                self.user_listbox.select_set(i)

    def update_performance_display(self):
        """Performans istatistiklerini güncelle"""
        if self.client and hasattr(self.client, 'perf_monitor'):
            try:
                stats = self.client.perf_monitor.get_current_stats()
                
                # Update performance labels
                self.perf_labels['msg_per_sec'].config(text=f"{stats['messages_per_second']:.1f}")
                
                avg_latency = stats.get('avg_latency_ms', 0)
                self.perf_labels['avg_latency'].config(text=f"{avg_latency:.1f} ms")
                
                packet_loss = stats['packet_loss_rate']
                self.perf_labels['packet_loss'].config(text=f"{packet_loss:.1f}%")
                
                self.perf_labels['sent_count'].config(text=str(stats['total_messages_sent']))
                self.perf_labels['received_count'].config(text=str(stats['total_messages_received']))
                
                # Color coding for performance indicators
                # Latency color coding
                if avg_latency > 100:
                    self.perf_labels['avg_latency'].config(fg="#DC3545")  # Red
                elif avg_latency > 50:
                    self.perf_labels['avg_latency'].config(fg="#FFC107")  # Yellow
                else:
                    self.perf_labels['avg_latency'].config(fg="#28A745")  # Green
                
                # Packet loss color coding
                if packet_loss > 5:
                    self.perf_labels['packet_loss'].config(fg="#DC3545")  # Red
                elif packet_loss > 2:
                    self.perf_labels['packet_loss'].config(fg="#FFC107")  # Yellow
                else:
                    self.perf_labels['packet_loss'].config(fg="#28A745")  # Green
                    
            except Exception as e:
                # Handle any errors silently to avoid GUI disruption
                pass
        
        # Schedule next update
        self.root.after(2000, self.update_performance_display)  # Update every 2 seconds

    def show_performance_report(self):
        """Detaylı performans raporu göster"""
        if not self.client or not hasattr(self.client, 'perf_monitor'):
            messagebox.showwarning("Uyarı", "Performans monitörü henüz başlatılmamış.")
            return
        
        try:
            report = self.client.perf_monitor.get_performance_report()
            suggestions = self.client.perf_monitor.get_optimization_suggestions()
            
            # Create a new window for the report
            report_window = tk.Toplevel(self.root)
            report_window.title("Performans Raporu")
            report_window.geometry("600x500")
            report_window.configure(bg="#F0F0F0")
            
            # Create notebook for tabs
            notebook = ttk.Notebook(report_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Report tab
            report_frame = ttk.Frame(notebook)
            notebook.add(report_frame, text="Detaylı Rapor")
            
            report_text = scrolledtext.ScrolledText(report_frame, wrap=tk.WORD, font=("Courier", 10))
            report_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            report_text.insert(tk.END, report)
            report_text.config(state='disabled')
            
            # Suggestions tab
            suggestions_frame = ttk.Frame(notebook)
            notebook.add(suggestions_frame, text="Optimizasyon Önerileri")
            
            suggestions_text = scrolledtext.ScrolledText(suggestions_frame, wrap=tk.WORD, font=("Helvetica", 10))
            suggestions_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            suggestions_content = "=== OPTİMİZASYON ÖNERİLERİ ===\n\n"
            for suggestion in suggestions:
                suggestions_content += f"• {suggestion}\n\n"
            
            suggestions_text.insert(tk.END, suggestions_content)
            suggestions_text.config(state='disabled')
            
            # Close button
            close_button = tk.Button(report_window, text="Kapat", 
                                   command=report_window.destroy,
                                   bg="#0078D4", fg="white", relief=tk.FLAT)
            close_button.pack(pady=5)
            
        except Exception as e:
            messagebox.showerror("Hata", f"Performans raporu oluşturulurken hata: {str(e)}")

    def reset_performance_stats(self):
        """Performans istatistiklerini sıfırla"""
        if not self.client or not hasattr(self.client, 'perf_monitor'):
            messagebox.showwarning("Uyarı", "Performans monitörü henüz başlatılmamış.")
            return
        
        result = messagebox.askyesno("Onay", "Performans istatistiklerini sıfırlamak istediğinizden emin misiniz?")
        if result:
            try:
                self.client.perf_monitor.reset_stats()
                self.display_message("Performans istatistikleri sıfırlandı.", 'performance')
                messagebox.showinfo("Başarılı", "Performans istatistikleri başarıyla sıfırlandı.")
            except Exception as e:
                messagebox.showerror("Hata", f"İstatistikler sıfırlanırken hata: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    gui = ChatGUI(root)
    root.mainloop()