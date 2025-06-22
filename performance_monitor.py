'''
Ağ Performansı Optimizasyonu Ölçüm Modülü
Bu modül chat uygulamasının ağ performansını izler ve optimize eder
'''
import time
import threading
import statistics
from collections import deque, defaultdict
import json
import os
from datetime import datetime, timedelta

class PerformanceMonitor:
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.lock = threading.Lock()
        
        # Performans metrikleri
        self.latencies = deque(maxlen=window_size)  # RTT süreleri
        self.message_timestamps = deque(maxlen=window_size)  # Mesaj gönderim zamanları
        self.packet_sizes = deque(maxlen=window_size)  # Paket boyutları
        self.retransmissions = deque(maxlen=window_size)  # Yeniden gönderim sayıları
        
        # Gerçek zamanlı sayaçlar
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
        self.total_retransmissions = 0
        self.session_start_time = time.time()
        
        # Latency ölçümleri için
        self.pending_messages = {}  # seq_num -> timestamp
        
        # Throughput hesaplama için
        self.throughput_window = deque(maxlen=10)  # Son 10 saniyenin verileri
        self.last_throughput_check = time.time()
        
        # Performans logları
        self.performance_log = []
        self.log_file = f"performance_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Performans istatistikleri thread'i
        self.monitoring_active = True
        self.stats_thread = threading.Thread(target=self._periodic_stats_collection, daemon=True)
        self.stats_thread.start()

    def record_message_sent(self, seq_num, message_size, timestamp=None):
        """Gönderilen mesaj bilgilerini kaydet"""
        if timestamp is None:
            timestamp = time.time()
        with self.lock:
            self.total_messages_sent += 1
            self.total_bytes_sent += message_size
            self.message_timestamps.append(timestamp)
            self.packet_sizes.append(message_size)
            self.pending_messages[seq_num] = timestamp
            print(f"[PERF-LOG] SENT: seq_num={seq_num}, size={message_size}, total_sent={self.total_messages_sent}")

    def record_message_received(self, seq_num, message_size, timestamp=None):
        """Alınan mesaj bilgilerini kaydet ve latency hesapla"""
        if timestamp is None:
            timestamp = time.time()
        with self.lock:
            self.total_messages_received += 1
            self.total_bytes_received += message_size
            print(f"[PERF-LOG] RECEIVED: seq_num={seq_num}, size={message_size}, total_received={self.total_messages_received}")
            # Latency hesapla
            if seq_num in self.pending_messages:
                sent_time = self.pending_messages[seq_num]
                latency = (timestamp - sent_time) * 1000  # milisaniye
                self.latencies.append(latency)
                del self.pending_messages[seq_num]

    def record_retransmission(self, seq_num):
        """Yeniden gönderim kaydı"""
        with self.lock:
            self.total_retransmissions += 1
            self.retransmissions.append(time.time())

    def get_current_stats(self):
        """Anlık performans istatistikleri"""
        with self.lock:
            current_time = time.time()
            session_duration = current_time - self.session_start_time
            print(f"[PERF-LOG] get_current_stats: sent={self.total_messages_sent}, received={self.total_messages_received}, retransmissions={self.total_retransmissions}")
            # Temel istatistikler
            stats = {
                'session_duration': session_duration,
                'total_messages_sent': self.total_messages_sent,
                'total_messages_received': self.total_messages_received,
                'total_bytes_sent': self.total_bytes_sent,
                'total_bytes_received': self.total_bytes_received,
                'total_retransmissions': self.total_retransmissions,
            }
            
            # Latency istatistikleri
            if self.latencies:
                stats.update({
                    'avg_latency_ms': statistics.mean(self.latencies),
                    'min_latency_ms': min(self.latencies),
                    'max_latency_ms': max(self.latencies),
                    'latency_stddev_ms': statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0,
                    'jitter_ms': self._calculate_jitter()
                })
            
            # Throughput hesaplama
            stats.update({
                'messages_per_second': self._calculate_message_throughput(),
                'bytes_per_second': self._calculate_byte_throughput(),
                'packet_loss_rate': self._calculate_packet_loss_rate(),
                'retransmission_rate': self._calculate_retransmission_rate()
            })
            
            # Ortalama paket boyutu
            if self.packet_sizes:
                stats['avg_packet_size'] = statistics.mean(self.packet_sizes)
            
            return stats

    def _calculate_jitter(self):
        """Jitter hesaplama (latency değişimi)"""
        if len(self.latencies) < 2:
            return 0
        
        # Ardışık latency'lerin farkları
        diffs = []
        for i in range(1, len(self.latencies)):
            diffs.append(abs(self.latencies[i] - self.latencies[i-1]))
        
        return statistics.mean(diffs) if diffs else 0

    def _calculate_message_throughput(self):
        """Mesaj/saniye hesaplama"""
        current_time = time.time()
        one_second_ago = current_time - 1.0
        
        # Son 1 saniyedeki mesajları say
        recent_messages = sum(1 for ts in self.message_timestamps if ts > one_second_ago)
        return recent_messages

    def _calculate_byte_throughput(self):
        """Byte/saniye hesaplama"""
        current_time = time.time()
        session_duration = current_time - self.session_start_time
        
        if session_duration > 0:
            return self.total_bytes_sent / session_duration
        return 0

    def _calculate_packet_loss_rate(self):
        """Gönderilen ve alınan paket farkına göre kayıp oranı"""
        if self.total_messages_sent == 0:
            return 0
        lost_packets = max(self.total_messages_sent - self.total_messages_received, 0)
        return (lost_packets / self.total_messages_sent) * 100

    def _calculate_retransmission_rate(self):
        """Yeniden gönderim oranı (her gönderilen mesaja oranla toplam retransmission sayısı)"""
        if self.total_messages_sent == 0:
            return 0
        return (self.total_retransmissions / self.total_messages_sent) * 100

    def _periodic_stats_collection(self):
        """Periyodik istatistik toplama"""
        while self.monitoring_active:
            try:
                stats = self.get_current_stats()
                stats['timestamp'] = datetime.now().isoformat()
                self.performance_log.append(stats)
                
                # Log dosyasına yaz
                self._save_to_file(stats)
                
                # Bellek kullanımını kontrol et
                if len(self.performance_log) > 1000:
                    self.performance_log = self.performance_log[-500:]  # Son 500 kaydı tut
                
                time.sleep(5)  # 5 saniyede bir istatistik topla
                
            except Exception as e:
                print(f"Performans monitoring hatası: {e}")
                time.sleep(5)

    def _save_to_file(self, stats):
        """İstatistikleri dosyaya kaydet"""
        try:
            # Dosya mevcutsa append, yoksa create
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
            else:
                data = []
            
            data.append(stats)
            
            # Son 1000 kaydı tut
            if len(data) > 1000:
                data = data[-1000:]
            
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Performans log yazma hatası: {e}")

    def get_performance_report(self):
        """Detaylı performans raporu"""
        stats = self.get_current_stats()
        
        report = f"""
=== PERFORMANS RAPORU ===
Oturum Süresi: {stats['session_duration']:.2f} saniye

MESAJ İSTATİSTİKLERİ:
- Gönderilen: {stats['total_messages_sent']}
- Alınan: {stats['total_messages_received']}
- Yeniden gönderim: {stats['total_retransmissions']}
- Yeniden gönderim oranı: {stats['retransmission_rate']:.2f}%

LATENCY (GECİKME):
- Ortalama: {stats.get('avg_latency_ms', 0):.2f} ms
- Minimum: {stats.get('min_latency_ms', 0):.2f} ms
- Maximum: {stats.get('max_latency_ms', 0):.2f} ms
- Jitter: {stats.get('jitter_ms', 0):.2f} ms

THROUGHPUT (AKIŞ HIZI):
- Mesaj/saniye: {stats['messages_per_second']:.2f}
- Byte/saniye: {stats['bytes_per_second']:.2f}
- Ortalama paket boyutu: {stats.get('avg_packet_size', 0):.2f} byte

PAKET KAYBI:
- Kayıp oranı: {stats['packet_loss_rate']:.2f}%

TOPLAM VERİ:
- Gönderilen: {stats['total_bytes_sent']} byte
- Alınan: {stats['total_bytes_received']} byte
"""
        return report

    def get_optimization_suggestions(self):
        """Performans optimizasyon önerileri"""
        stats = self.get_current_stats()
        suggestions = []
        
        # Latency kontrolü
        avg_latency = stats.get('avg_latency_ms', 0)
        if avg_latency > 100:
            suggestions.append("⚠️ Yüksek latency tespit edildi. Ağ bağlantınızı kontrol edin.")
        
        # Jitter kontrolü
        jitter = stats.get('jitter_ms', 0)
        if jitter > 50:
            suggestions.append("⚠️ Yüksek jitter tespit edildi. Ağ kararlılığınızı artırın.")
        
        # Packet loss kontrolü
        packet_loss = stats['packet_loss_rate']
        if packet_loss > 5:
            suggestions.append("⚠️ Yüksek paket kaybı tespit edildi. Ağ kalitesini artırın.")
        elif packet_loss > 2:
            suggestions.append("ℹ️ Orta seviye paket kaybı tespit edildi.")
        
        # Throughput kontrolü
        throughput = stats['bytes_per_second']
        if throughput < 1000:  # 1KB/s'den az
            suggestions.append("ℹ️ Düşük throughput. Daha büyük paketler kullanmayı düşünün.")
        
        if not suggestions:
            suggestions.append("✅ Ağ performansı optimal görünüyor!")
        
        return suggestions

    def stop_monitoring(self):
        """Monitoring'i durdur"""
        self.monitoring_active = False
        if self.stats_thread.is_alive():
            self.stats_thread.join(timeout=1)

    def reset_stats(self):
        """İstatistikleri sıfırla"""
        with self.lock:
            self.latencies.clear()
            self.message_timestamps.clear()
            self.packet_sizes.clear()
            self.retransmissions.clear()
            self.pending_messages.clear()
            
            self.total_messages_sent = 0
            self.total_messages_received = 0
            self.total_bytes_sent = 0
            self.total_bytes_received = 0
            self.total_retransmissions = 0
            self.session_start_time = time.time()

# Global performans monitor instance
performance_monitor = PerformanceMonitor()