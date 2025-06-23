import sys
import threading
import queue
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QTextEdit, QLineEdit,
    QMessageBox, QInputDialog, QTabWidget, QDialog, QFormLayout, QDialogButtonBox, QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint
import client

class MessageSignals(QObject):
    message_received = pyqtSignal(str, str)

class PerformanceReportDialog(QDialog):
    def __init__(self, report, suggestions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Performans Raporu")
        self.resize(600, 500)
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        # Report tab
        report_widget = QWidget()
        report_layout = QVBoxLayout(report_widget)
        report_text = QTextEdit()
        report_text.setReadOnly(True)
        report_text.setFontFamily("Courier")
        report_text.setText(report)
        report_layout.addWidget(report_text)
        tabs.addTab(report_widget, "Detaylı Rapor")
        # Suggestions tab
        suggestions_widget = QWidget()
        suggestions_layout = QVBoxLayout(suggestions_widget)
        suggestions_text = QTextEdit()
        suggestions_text.setReadOnly(True)
        suggestions_content = "=== OPTİMİZASYON ÖNERİLERİ ===\n\n"
        for suggestion in suggestions:
            suggestions_content += f"• {suggestion}\n\n"
        suggestions_text.setText(suggestions_content)
        suggestions_layout.addWidget(suggestions_text)
        tabs.addTab(suggestions_widget, "Optimizasyon Önerileri")
        layout.addWidget(tabs)
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

class ChatGUI(QWidget):
    def __init__(self):
        super().__init__()
        # Frameless window ve custom title bar için ayarlar
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowTitle("Chat Uygulaması")
        self.resize(900, 600)
        self.msg_queue = queue.Queue()
        self.user_list = []
        self.client = None
        self.signals = MessageSignals()
        self.signals.message_received.connect(self._display_message_gui)
        self.username = self.ask_username()
        if not self.username:
            sys.exit(0)
        self.setWindowTitle(f"Chat Uygulaması - {self.username}")
        self.server_addr = self.ask_server_addr()
        self.port = self.ask_port()
        if not (self.server_addr and self.port):
            sys.exit(0)
        self.groups = {}
        self.selected_group_id = None
        self.active_chat_label = None
        self.chat_widgets = {}  # chat_id: {'widget': QWidget, 'text_area': QTextEdit, 'entry': QLineEdit}
        self.init_ui()
        self.connect_to_server()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_messages)
        self.timer.start(100)
        self.perf_timer = QTimer(self)
        self.perf_timer.timeout.connect(self.update_performance_display)
        self.perf_timer.start(2000)
        self._drag_pos = None
        self._RESIZE_MARGIN = 8
        self._resizing = False
        self._resize_dir = None
        self._resize_start_pos = None
        self._resize_start_geom = None

    def ask_username(self):
        text, ok = QInputDialog.getText(self, "Kullanıcı Adı", "Kullanıcı adınızı girin:")
        return text if ok and text else None

    def ask_server_addr(self):
        text, ok = QInputDialog.getText(self, "Sunucu Adresi", "Sunucu adresini girin:", text="localhost")
        return text if ok and text else None

    def ask_port(self):
        num, ok = QInputDialog.getInt(self, "Port", "Sunucu portunu girin:", value=15000)
        return num if ok else None

    def init_ui(self):
        # Ana pencere için stil tanımlaması
        self.setStyleSheet("""
            QWidget {
                background-color: #2F2F2F;
                color: #FFFFFF;
            }
            QTextEdit, QListWidget, QLineEdit {
                background-color: #3D3D3D;
                border: 1px solid #FF8C00;
                border-radius: 4px;
                padding: 4px;
                color: #FFFFFF;
                margin: 2px;
            }
            QPushButton {
                background-color: #FF8C00;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #FFA500;
            }
            QPushButton:pressed {
                background-color: #FF7000;
            }
            QLabel {
                color: #FFFFFF;
                margin: 2px;
            }
            QGroupBox {
                border: 1px solid #FF8C00;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 14px;
                margin-left: 2px;
                margin-right: 2px;
            }
            QGroupBox::title {
                color: #FF8C00;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
        """)

        main_vlayout = QVBoxLayout(self)
        main_vlayout.setContentsMargins(8, 8, 8, 8)
        main_vlayout.setSpacing(4)

        # Custom title bar
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(36)
        self.title_bar.setStyleSheet("background-color: #2F2F2F; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(8, 0, 8, 0)
        self.title_label = QLabel(f"Chat Uygulaması - {self.username}")
        self.title_label.setStyleSheet("color: #FF8C00; font-weight: bold; font-size: 16px;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background-color: #3D3D3D; color: #FF8C00; border-radius: 14px; font-size: 16px;")
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        main_vlayout.addWidget(self.title_bar)

        # Alt içerik (yeni ana layout)
        content_hlayout = QHBoxLayout()
        content_hlayout.setSpacing(8)

        # Sol panel (chat list + kullanıcılar + gruplar)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(4)
        # Son Konuşmalar
        chatlist_label = QLabel("Son Konuşmalar")
        chatlist_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(chatlist_label)
        self.chat_listbox = QListWidget()
        self.chat_listbox.setSelectionMode(QListWidget.SingleSelection)
        left_panel.addWidget(self.chat_listbox)
        self.new_chat_button = QPushButton("Yeni Mesaj")
        self.new_chat_button.clicked.connect(self.new_chat_dialog)
        left_panel.addWidget(self.new_chat_button)
        # Grup oluşturma butonu
        self.create_group_button = QPushButton("Yeni Grup")
        self.create_group_button.clicked.connect(self.create_group_dialog)
        left_panel.addWidget(self.create_group_button)
        left_panel.addSpacing(10)
        # Kullanıcılar
        user_label = QLabel("Kullanıcılar")
        user_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(user_label)
        self.user_listbox = QListWidget()
        self.user_listbox.setSelectionMode(QListWidget.MultiSelection)
        left_panel.addWidget(self.user_listbox)
        self.refresh_button = QPushButton("Yenile")
        self.refresh_button.clicked.connect(self.refresh_users)
        left_panel.addWidget(self.refresh_button)
        left_panel.addSpacing(10)
        # Gruplar
        group_label = QLabel("Gruplar")
        group_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(group_label)
        self.group_listbox = QListWidget()
        self.group_listbox.setSelectionMode(QListWidget.SingleSelection)
        self.group_listbox.itemClicked.connect(self.on_group_selected)
        left_panel.addWidget(self.group_listbox)
        self.refresh_groups_button = QPushButton("Grupları Yenile")
        self.refresh_groups_button.clicked.connect(self.refresh_groups)
        left_panel.addWidget(self.refresh_groups_button)
        left_panel.addSpacing(20)
        # Performans Monitörü (eski koddan alınacak)
        perf_group = QGroupBox("Performans Monitörü")
        perf_layout = QFormLayout(perf_group)
        perf_layout.setSpacing(4)
        perf_layout.setContentsMargins(8, 8, 8, 8)
        self.perf_labels = {}
        perf_stats = [
            ("Mesaj/sn:", "msg_per_sec", "0.0"),
            ("Ortalama Gecikme:", "avg_latency", "0 ms"),
            ("Paket Kaybı:", "packet_loss", "0%"),
            ("Gönderilen:", "sent_count", "0"),
            ("Alınan:", "received_count", "0")
        ]
        for label_text, key, default_value in perf_stats:
            value_label = QLabel(default_value)
            perf_layout.addRow(QLabel(label_text), value_label)
            self.perf_labels[key] = value_label
        self.perf_report_button = QPushButton("Detaylı Rapor")
        self.perf_report_button.clicked.connect(self.show_performance_report)
        self.perf_reset_button = QPushButton("İstatistikleri Sıfırla")
        self.perf_reset_button.clicked.connect(self.reset_performance_stats)
        perf_layout.addRow(self.perf_report_button, self.perf_reset_button)
        left_panel.addWidget(perf_group)
        left_panel.addStretch(1)
        content_hlayout.addLayout(left_panel, 1)

        # Orta panel: Sekmeli sohbet alanı
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_chat_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        content_hlayout.addWidget(self.tab_widget, 3)

        main_vlayout.addLayout(content_hlayout)
        self.setLayout(main_vlayout)

        self.user_listbox.itemSelectionChanged.connect(self.user_listbox_selection_changed)

    def connect_to_server(self):
        ClientClass = client.Client
        self.client = ClientClass(self.username, self.server_addr, self.port, 3, on_message=self.display_message)
        threading.Thread(target=self.client.start, daemon=True).start()
        self.display_message("Sunucuya bağlanılıyor...", 'system')
        QTimer.singleShot(500, self.refresh_users)
        QTimer.singleShot(1000, self.refresh_groups)

    def send_message(self):
        msg = self.entry.text()
        if msg:
            if not self.client or not hasattr(self.client, 'sock') or self.client.sock is None:
                QMessageBox.warning(self, "Bağlantı Hatası", "Sunucuya bağlı değilsiniz veya bağlantı koptu.")
                return
            if self.selected_group_id:
                # Grup mesajı
                try:
                    self.client.group_msg(f"group_msg {self.selected_group_id} {msg}")
                    # Kendi mesajını arayüzde göster
                    group_name = self.groups[self.selected_group_id]['name'] if self.selected_group_id in self.groups else self.selected_group_id
                    self.text_area.append(f"<b style='color:#28A745;'>[Grup: {group_name}] Siz:</b> {msg}")
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Grup mesajı gönderilemedi: {str(e)}")
                self.entry.clear()
                return
            selected_items = self.user_listbox.selectedItems()
            if not selected_items:
                selected_users = ['all']
                display_text = f"msg:{self.username} (Herkese):{msg}"
            else:
                selected_users = [item.text() for item in selected_items]
                display_text = f"msg:{self.username} (Özel):{msg}"
            self.msg_queue.put(display_text)
            user_count = len(selected_users)
            user_str = ','.join(selected_users)
            full_msg = f"msg {user_count} {user_str} {msg}"
            try:
                self.client.msg(full_msg)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Mesaj gönderilemedi: {str(e)}")
            self.entry.clear()

    def display_message(self, message, tag_override=None):
        self.signals.message_received.emit(message, tag_override if tag_override else "")
        # Grup mesajı veya grup bildirimi ise güncelle
        if message.startswith("Yeni grup oluşturuldu:") or message.startswith("[Grup:"):
            self.refresh_groups()

    def _display_message_gui(self, message, tag_override):
        # Mesajı ilgili sekmeye yönlendir
        # Özel mesaj: msg:username:mesaj
        if message.startswith("msg:"):
            try:
                _, sender, content = message.split(':', 2)
                # Eğer mesajı ben gönderdiysem, chat_id karşı taraf olmalı
                if sender == self.username:
                    # Kendi gönderdiğim mesajı, aktif sekmeye ekle (zaten ekleniyor)
                    return
                chat_id = sender.strip()
                text_area = self._get_or_create_chat_tab(chat_id, is_group=False)
                text_area.append(f"<b>{sender}:</b> {content}")
            except ValueError:
                self._get_or_create_chat_tab("Sistem").append(f"Alınan mesaj formatı bozuk: {message}")
            return
        # Grup mesajı
        if message.startswith("[Grup:"):
            try:
                # [Grup: GrupAdı] Kullanıcı: mesaj
                group_info = message.split(']')[0][7:]  # Grup adı
                group_name = group_info.strip()
                chat_id = group_name
                text_area = self._get_or_create_chat_tab(chat_id, is_group=True, group_name=group_name)
                text_area.append(f"<span style='color:#0078D4;'><b>{message}</b></span>")
            except Exception:
                self._get_or_create_chat_tab("Sistem").append(f"Grup mesajı formatı bozuk: {message}")
            return
        # Sistem ve diğer mesajlar
        if tag_override == 'system':
            text_area = self._get_or_create_chat_tab("Sistem")
            text_area.append(f"<i>{message}</i>")
            return
        if tag_override == 'performance':
            text_area = self._get_or_create_chat_tab("Performans")
            text_area.append(f"<span style='color:green;'><b>{message}</b></span>")
            return
        if message.startswith("list: "):
            users = message[6:].strip().split()
            self.user_list = sorted([u for u in users if u != self.username])
            self.update_user_listbox()
            text_area = self._get_or_create_chat_tab("Sistem")
            text_area.append(f"<i>{message}</i>")
        elif message.startswith("Dahil olduğunuz gruplar:"):
            # Grup listesi güncelle
            group_list = message.split(':', 1)[1].strip().split(',')
            self.groups = {}
            for g in group_list:
                if ':' in g:
                    gid, gname = g.split(':', 1)
                    self.groups[gid] = {'name': gname, 'members': []}
            self.update_group_listbox()
            text_area = self._get_or_create_chat_tab("Sistem")
            text_area.append(f"<i>{message}</i>")
            return
        else:
            text_area = self._get_or_create_chat_tab("Sistem")
            text_area.append(f"<i>{message}</i>")

    def check_messages(self):
        while not self.msg_queue.empty():
            message = self.msg_queue.get()
            self.display_message(message)

    def refresh_users(self):
        if not self.client or not hasattr(self.client, 'sock') or self.client.sock is None:
            QMessageBox.warning(self, "Bağlantı Hatası", "Sunucuya bağlı değilsiniz veya bağlantı koptu.")
            return
        try:
            self.display_message("Kullanıcı listesi yenileniyor...", 'system')
            self.client.list()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kullanıcı listesi alınırken hata oluştu: {str(e)}")

    def update_user_listbox(self):
        selected = [item.text() for item in self.user_listbox.selectedItems()]
        self.user_listbox.clear()
        for user in self.user_list:
            self.user_listbox.addItem(user)
        # Restore selection
        for i in range(self.user_listbox.count()):
            if self.user_listbox.item(i).text() in selected:
                self.user_listbox.item(i).setSelected(True)

    def update_performance_display(self):
        if self.client and hasattr(self.client, 'perf_monitor'):
            try:
                stats = self.client.perf_monitor.get_current_stats()
                self.perf_labels['msg_per_sec'].setText(f"{stats['messages_per_second']:.1f}")
                avg_latency = stats.get('avg_latency_ms', 0)
                self.perf_labels['avg_latency'].setText(f"{avg_latency:.1f} ms")
                packet_loss = stats['packet_loss_rate']
                self.perf_labels['packet_loss'].setText(f"{packet_loss:.1f}%")
                self.perf_labels['sent_count'].setText(str(stats['total_messages_sent']))
                self.perf_labels['received_count'].setText(str(stats['total_messages_received']))
                # Color coding
                if avg_latency > 100:
                    self.perf_labels['avg_latency'].setStyleSheet("color:#DC3545;")
                elif avg_latency > 50:
                    self.perf_labels['avg_latency'].setStyleSheet("color:#FFC107;")
                else:
                    self.perf_labels['avg_latency'].setStyleSheet("color:#28A745;")
                if packet_loss > 5:
                    self.perf_labels['packet_loss'].setStyleSheet("color:#DC3545;")
                elif packet_loss > 2:
                    self.perf_labels['packet_loss'].setStyleSheet("color:#FFC107;")
                else:
                    self.perf_labels['packet_loss'].setStyleSheet("color:#28A745;")
            except Exception:
                pass

    def show_performance_report(self):
        if not self.client or not hasattr(self.client, 'perf_monitor'):
            QMessageBox.warning(self, "Uyarı", "Performans monitörü henüz başlatılmamış.")
            return
        try:
            report = self.client.perf_monitor.get_performance_report()
            suggestions = self.client.perf_monitor.get_optimization_suggestions()
            dlg = PerformanceReportDialog(report, suggestions, self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Performans raporu oluşturulurken hata: {str(e)}")

    def reset_performance_stats(self):
        if not self.client or not hasattr(self.client, 'perf_monitor'):
            QMessageBox.warning(self, "Uyarı", "Performans monitörü henüz başlatılmamış.")
            return
        result = QMessageBox.question(self, "Onay", "Performans istatistiklerini sıfırlamak istediğinizden emin misiniz?", QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            try:
                self.client.perf_monitor.reset_stats()
                self.display_message("Performans istatistikleri sıfırlandı.", 'performance')
                QMessageBox.information(self, "Başarılı", "Performans istatistikleri başarıyla sıfırlandı.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"İstatistikler sıfırlanırken hata: {str(e)}")

    def refresh_groups(self):
        if not self.client:
            return
        try:
            self.client.request_groups_list()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Grup listesi alınırken hata oluştu: {str(e)}")

    def update_group_listbox(self):
        self.group_listbox.clear()
        for gid, ginfo in self.groups.items():
            self.group_listbox.addItem(f"{ginfo['name']} (ID: {gid})")

    def on_group_selected(self, item):
        # Grup seçilince sekme aç
        text = item.text()
        if '(ID:' in text:
            group_name = text.split(' (ID:')[0]
            gid = text.split('(ID:')[1].strip(' )')
            self.open_chat_tab(gid, is_group=True, group_name=group_name)

    def create_group_dialog(self):
        selected_items = self.user_listbox.selectedItems()
        if not selected_items or len(selected_items) < 2:
            QMessageBox.warning(self, "Uyarı", "Grup oluşturmak için en az iki kullanıcı seçmelisiniz.")
            return
        group_name, ok = QInputDialog.getText(self, "Grup Adı", "Grup adını girin:")
        if ok and group_name:
            members = [item.text() for item in selected_items]
            if self.username not in members:
                members.append(self.username)
            try:
                self.client.create_group(f"create_group {group_name} {' '.join(members)}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Grup oluşturulamadı: {str(e)}")

    def user_listbox_selection_changed(self):
        # Kullanıcı seçimi değiştiğinde yapılacak işlemler (gerekirse buraya eklenir)
        pass

    # --- Frameless window için resize desteği ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            margin = self._RESIZE_MARGIN
            rect = self.rect()
            x, y = event.x(), event.y()
            # Kenar ve köşe kontrolleri
            if x <= margin and y <= margin:
                self._resizing = True; self._resize_dir = 'tl'
            elif x >= rect.width() - margin and y <= margin:
                self._resizing = True; self._resize_dir = 'tr'
            elif x <= margin and y >= rect.height() - margin:
                self._resizing = True; self._resize_dir = 'bl'
            elif x >= rect.width() - margin and y >= rect.height() - margin:
                self._resizing = True; self._resize_dir = 'br'
            elif x <= margin:
                self._resizing = True; self._resize_dir = 'l'
            elif x >= rect.width() - margin:
                self._resizing = True; self._resize_dir = 'r'
            elif y <= margin:
                self._resizing = True; self._resize_dir = 't'
            elif y >= rect.height() - margin:
                self._resizing = True; self._resize_dir = 'b'
            elif self.childAt(event.pos()) == self.title_bar:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            if self._resizing:
                self._resize_start_pos = event.globalPos()
                self._resize_start_geom = self.geometry()
                event.accept()
            elif self._drag_pos:
                event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        elif self._resizing and self._resize_start_pos:
            diff = event.globalPos() - self._resize_start_pos
            geom = self._resize_start_geom
            min_w, min_h = 100, 100  # Minimum boyutu düşürdük
            x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()
            dir = self._resize_dir
            if dir == 'br':
                new_w = max(min_w, w + diff.x())
                new_h = max(min_h, h + diff.y())
                self.setGeometry(x, y, new_w, new_h)
            elif dir == 'bl':
                new_w = max(min_w, w - diff.x())
                new_h = max(min_h, h + diff.y())
                if new_w >= min_w:
                    x = x + diff.x()
                self.setGeometry(x, y, new_w, new_h)
            elif dir == 'tr':
                new_w = max(min_w, w + diff.x())
                new_h = max(min_h, h - diff.y())
                if new_h >= min_h:
                    y = y + diff.y()
                self.setGeometry(x, y, new_w, new_h)
            elif dir == 'tl':
                new_w = max(min_w, w - diff.x())
                new_h = max(min_h, h - diff.y())
                if new_w >= min_w:
                    x = x + diff.x()
                if new_h >= min_h:
                    y = y + diff.y()
                self.setGeometry(x, y, new_w, new_h)
            elif dir == 'l':
                new_w = max(min_w, w - diff.x())
                if new_w >= min_w:
                    x = x + diff.x()
                self.setGeometry(x, y, new_w, h)
            elif dir == 'r':
                new_w = max(min_w, w + diff.x())
                self.setGeometry(x, y, new_w, h)
            elif dir == 't':
                new_h = max(min_h, h - diff.y())
                if new_h >= min_h:
                    y = y + diff.y()
                self.setGeometry(x, y, w, new_h)
            elif dir == 'b':
                new_h = max(min_h, h + diff.y())
                self.setGeometry(x, y, w, new_h)
            event.accept()
        else:
            margin = self._RESIZE_MARGIN
            rect = self.rect()
            x, y = event.x(), event.y()
            if x <= margin and y <= margin:
                self.setCursor(Qt.SizeFDiagCursor)
            elif x >= rect.width() - margin and y <= margin:
                self.setCursor(Qt.SizeBDiagCursor)
            elif x <= margin and y >= rect.height() - margin:
                self.setCursor(Qt.SizeBDiagCursor)
            elif x >= rect.width() - margin and y >= rect.height() - margin:
                self.setCursor(Qt.SizeFDiagCursor)
            elif x <= margin:
                self.setCursor(Qt.SizeHorCursor)
            elif x >= rect.width() - margin:
                self.setCursor(Qt.SizeHorCursor)
            elif y <= margin:
                self.setCursor(Qt.SizeVerCursor)
            elif y >= rect.height() - margin:
                self.setCursor(Qt.SizeVerCursor)
            elif self.childAt(event.pos()) == self.title_bar:
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resizing = False
        self._resize_dir = None
        self._resize_start_pos = None
        self._resize_start_geom = None

    # Yeni Mesaj başlatma dialogu (kullanıcı seçimi)
    def new_chat_dialog(self):
        selected_items = self.user_listbox.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen mesaj göndermek için bir kullanıcı seçin.")
            return
        user = selected_items[0].text()
        self.open_chat_tab(user, is_group=False)

    # Sekme açma fonksiyonu (kullanıcı veya grup için)
    def open_chat_tab(self, chat_id, is_group=False, group_name=None):
        # chat_id: kullanıcı adı veya grup id
        # Eğer sekme zaten açıksa ona geç
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i).objectName() == chat_id:
                self.tab_widget.setCurrentIndex(i)
                return
        # Yeni sekme oluştur
        chat_widget = QWidget()
        chat_widget.setObjectName(chat_id)
        vlayout = QVBoxLayout(chat_widget)
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        vlayout.addWidget(text_area)
        entry_layout = QHBoxLayout()
        entry = QLineEdit()
        send_btn = QPushButton("Gönder")
        entry_layout.addWidget(entry)
        entry_layout.addWidget(send_btn)
        vlayout.addLayout(entry_layout)
        tab_title = group_name if is_group and group_name else chat_id
        self.tab_widget.addTab(chat_widget, tab_title)
        self.tab_widget.setCurrentWidget(chat_widget)
        # Chat widget referanslarını kaydet
        self.chat_widgets[chat_id] = {'widget': chat_widget, 'text_area': text_area, 'entry': entry, 'is_group': is_group}
        # Gönder butonunu ve entry'yi bağla
        def send_message_from_tab():
            msg = entry.text().strip()
            if not msg:
                return
            if is_group:
                # Grup mesajı gönder
                try:
                    self.client.group_msg(f"group_msg {chat_id} {msg}")
                    text_area.append(f"<b style='color:#28A745;'>Siz:</b> {msg}")
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Grup mesajı gönderilemedi: {str(e)}")
            else:
                # Birebir mesaj gönder
                try:
                    user_count = 1
                    user_str = chat_id
                    full_msg = f"msg {user_count} {user_str} {msg}"
                    self.client.msg(full_msg)
                    text_area.append(f"<b style='color:#28A745;'>Siz:</b> {msg}")
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Mesaj gönderilemedi: {str(e)}")
            entry.clear()
        send_btn.clicked.connect(send_message_from_tab)
        entry.returnPressed.connect(send_message_from_tab)

    def _get_or_create_chat_tab(self, chat_id, is_group=False, group_name=None):
        if chat_id not in self.chat_widgets:
            self.open_chat_tab(chat_id, is_group, group_name)
        return self.chat_widgets[chat_id]['text_area']

    def close_chat_tab(self, index):
        self.tab_widget.removeTab(index)

    def on_tab_changed(self, index):
        # Sekme değiştiğinde okunmamış uyarılarını kaldır vs.
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dark_style = """
        QDialog, QInputDialog, QLineEdit, QSpinBox, QComboBox, QListView, QAbstractItemView {
            background-color: #2F2F2F;
            color: #FFFFFF;
            border: 1px solid #FF8C00;
            selection-background-color: #FF8C00;
            selection-color: #2F2F2F;
        }
        QLabel { color: #FFFFFF; }
        QPushButton { background-color: #FF8C00; color: #FFF; border: none; border-radius: 4px; }
        QPushButton:hover { background-color: #FFA500; }
        QPushButton:pressed { background-color: #FF7000; }
    """
    app.setStyleSheet(dark_style)
    gui = ChatGUI()
    gui.show()
    sys.exit(app.exec_())