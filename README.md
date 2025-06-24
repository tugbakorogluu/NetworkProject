**#Chat Application - Reliable UDP (PyQt5 GUI & Performance Monitoring)**
Bu proje, UDP üzerinden çalışan, güvenilir mesaj iletimi sağlayan bir sohbet uygulamasıdır. Hem komut satırı hem de modern PyQt5 tabanlı bir grafik arayüz (GUI) içerir. Ağ performansı, özel bir modül ile gerçek zamanlı izlenir ve detaylı raporlanır. Proje, üniversite programlama ödevi kapsamında geliştirilmiştir.


**##Özellikler**
- *Sunucu (server.py):*
1) UDP üzerinden çoklu istemci desteği
2) Aktif kullanıcı yönetimi
3) Mesaj yönlendirme (bireysel, herkese, grup)
4) Güvenilir iletim için sıralama, ACK, tekrar gönderim
5) Grup oluşturma ve grup mesajlaşma desteği

- *İstemci (client.py):*
1) Komut satırı arayüzü
2) Mesaj gönderme, kullanıcı listeleme, gruplar, performans komutları
3) Performans istatistikleri ve öneriler

- *Grafik Arayüz (client_gui.py):*
1) PyQt5 ile modern, karanlık temalı sohbet arayüzü
2) Kullanıcı ve grup listeleri, sekmeli sohbet, performans monitörü
3) Detaylı performans raporu ve optimizasyon önerileri

- *Ağ Performans Monitörü (performance_monitor.py):*
1) RTT, jitter, throughput, paket kaybı, yeniden gönderim oranı
2) Gerçek zamanlı istatistikler ve JSON loglama
3) Otomatik optimizasyon önerileri

- *Yardımcı Fonksiyonlar (util.py):*
1) Paket oluşturma, çözümleme, checksum, mesaj formatları


**##Kurulum**

*Gereksinimler*
- Python 3.6+
- PyQt5 (pip install pyqt5)
- Linux/MacOS (tavsiye edilir) veya Windows (WSL ile önerilir)

*Proje Dosya Yapısı:*
server.py              # Sunucu kodu (güvenilir UDP)
client.py              # Komut satırı istemci
client_gui.py          # PyQt5 tabanlı grafik istemci
performance_monitor.py # Ağ performans izleme modülü
util.py                # Yardımcı fonksiyonlar ve sabitler
README.md


**##Kullanım**

*Sunucuyu Başlatmak:*
python3 server.py -p <port_num>
NOt: Varsayılan port: 15000

*Komut Satırı İstemcisi:*
python3 client.py -p <server_port_num> -u <username>

*Grafik Arayüz (PyQt5)*
python3 client_gui.py
Not: Kullanıcı adı, sunucu adresi ve portu arayüzden girilir.


**##Temel Komutlar**
- Mesaj Gönder: msg <kullanıcı_sayısı> <kullanıcı1> <kullanıcı2> ... <mesaj>
- Kullanıcıları Listele: list
- Yardım: help
- Çıkış: quit
- Grup Oluştur: create_group <grup_adı> <kullanıcı1> <kullanıcı2> ...
- Grup Mesajı: group_msg <grup_id> <mesaj>
- Grupları Listele: groups
- Performans: perf, perf_report, perf_reset


**#Testler**
Uygulamanın gecikme performansını ölçmek için client.py tarafında bir rtt_test fonksiyonu geliştirilmiştir. Bu test, aşağıdaki adımları izlemiştir:
İstemciden sunucuya 100 adet sıralı test paketi gönderilmiştir.
Her bir paketin gönderildiği an ile sunucudan ilgili yanıtın alındığı an arasındaki süre (RTT) yüksek hassasiyetle ölçülmüştür.
Test, istemci ve sunucunun aynı makine üzerinde (localhost) çalıştığı bir ortamda gerçekleştirilmiştir.


**##Teknolojiler**
- Python 3
- UDP Socket Programlama
- PyQt5 (GUI)
- Threading
- CRC32 Checksum
- JSON ile loglama


Not:
Sunucu ve istemci aynı makinede çalışacaksa, farklı portlar kullanın. Ağ performans monitörü, 
performans_log.json dosyasına kayıt yapar.