### 10 Şubat

Bugün projeyi sıfırdan ayağa kaldırdım. Amacım sadece uygulama yazmak değil, üretim ortamına yakın bir altyapı kurmaktı.

Docker Compose ile servisleri tanımladım:

* PostgreSQL
* Redis
* RabbitMQ
* Nginx gateway
* Django (event_ingestor)
* FastAPI servisleri
* WebSocket gateway

Network katmanını bilinçli tasarladım:

* public_net
* internal_net
* data_net

Veritabanı ve broker servislerini dış dünyaya açmadım. Trafik yalnızca Nginx üzerinden akacak şekilde konumlandırdım. Bu ayrımı güvenlik ve izolasyon için yaptım.

Healthcheck’ler ekledim. Container restart davranışlarını gözlemledim. Resource limitlerini belirledim. Image versiyonlarını sabitlemenin neden önemli olduğunu değerlendirdim.

Bu günün ana çıktısı:

Proje sadece bir Django app değil, containerized bir sistem olarak çalışıyor. Servis izolasyonu, network segmentasyonu ve gateway mimarisi kuruldu.
