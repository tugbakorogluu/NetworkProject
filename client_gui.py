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

        # Ana layout: önce başlık barı, sonra içerik
        main_vlayout = QVBoxLayout(self)
        main_vlayout.setContentsMargins(8, 8, 8, 8)
        main_vlayout.setSpacing(4)

        # Custom title bar (tüm pencere üstünde)
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

        # Alt içerik (eski main_layout)
        content_hlayout = QHBoxLayout()
        content_hlayout.setSpacing(8)  # Yatay boşluk ekle

        # Sol panel
        left_panel = QVBoxLayout()
        left_panel.setSpacing(4)  # Dikey boşluk ekle
        user_label = QLabel("Çevrimiçi Kullanıcılar")
        user_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(user_label)
        self.user_listbox = QListWidget()
        self.user_listbox.setSelectionMode(QListWidget.MultiSelection)
        left_panel.addWidget(self.user_listbox)
        self.refresh_button = QPushButton("Yenile")
        self.refresh_button.clicked.connect(self.refresh_users)
        left_panel.addWidget(self.refresh_button)
        left_panel.addSpacing(20)

        # Performans Monitörü
        perf_group = QGroupBox("Performans Monitörü")
        perf_layout = QFormLayout(perf_group)
        perf_layout.setSpacing(4)  # Form layout boşluğu
        perf_layout.setContentsMargins(8, 8, 8, 8)  # İç kenar boşlukları
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

        # Sağ panel
        right_panel = QVBoxLayout()
        right_panel.setSpacing(4)  # Dikey boşluk ekle
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        right_panel.addWidget(self.text_area, 5)
        entry_layout = QHBoxLayout()
        entry_layout.setSpacing(4)  # Yatay boşluk ekle
        self.entry = QLineEdit()
        self.entry.returnPressed.connect(self.send_message)
        entry_layout.addWidget(self.entry, 5)
        self.send_button = QPushButton("Gönder")
        self.send_button.clicked.connect(self.send_message)
        entry_layout.addWidget(self.send_button)
        right_panel.addLayout(entry_layout)
        content_hlayout.addLayout(right_panel, 3)
        main_vlayout.addLayout(content_hlayout)

    def connect_to_server(self):
        ClientClass = client.Client
        self.client = ClientClass(self.username, self.server_addr, self.port, 3, on_message=self.display_message)
        threading.Thread(target=self.client.start, daemon=True).start()
        self.display_message("Sunucuya bağlanılıyor...", 'system')
        QTimer.singleShot(500, self.refresh_users)

    def send_message(self):
        msg = self.entry.text()
        if msg:
            if not self.client or not hasattr(self.client, 'sock') or self.client.sock is None:
                QMessageBox.warning(self, "Bağlantı Hatası", "Sunucuya bağlı değilsiniz veya bağlantı koptu.")
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

    def _display_message_gui(self, message, tag_override):
        if tag_override == 'system':
            self.text_area.append(f"<i>{message}</i>")
            return
        if tag_override == 'performance':
            self.text_area.append(f"<span style='color:green;'><b>{message}</b></span>")
            return
        if message.startswith("list: "):
            users = message[6:].strip().split()
            self.user_list = sorted([u for u in users if u != self.username])
            self.update_user_listbox()
        elif message.startswith("msg:"):
            try:
                _, sender, content = message.split(':', 2)
                if sender.startswith(self.username):
                    context = ""
                    if "(Herkese)" in sender:
                        context = " (Herkese)"
                    elif "(Özel)" in sender:
                        context = " (Özel)"
                    self.text_area.append(f"<b style='color:#0078D4;'>Siz{context}:</b> {content}")
                else:
                    self.text_area.append(f"<b>{sender}:</b> {content}")
            except ValueError:
                self._display_message_gui(f"Alınan mesaj formatı bozuk: {message}", 'system')
        else:
            self._display_message_gui(message, 'system')

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