
# TelemetryEventMesh (TEM) – Architecture

Bu doküman iki katmanda sistemi açıklar:

1. Servis katmanı: `event_ingestor` (Django/DRF) servisinin rolü ve iç akışı
2. Platform katmanı: TEM’in tamamı (gateway, broker, DB, worker’lar ve diğer servisler)

TEM şu anda **operationally distributed, architecturally monolithic** bir yapıdır:
- Operasyonel olarak distributed: broker, worker, gateway, DB ayrı süreç/servisler olarak çalışır.
- Mimari olarak monolith: tek repo/tek compose ile birlikte deploy edilir, paylaşılan tek DB ile sıkı bağlıdır.

---

## 1) Servis Katmanı: event_ingestor

`event_ingestor`, TEM’in ingest ve workflow orchestration giriş noktasıdır.

### 1.1 Sorumluluklar

- HTTP (REST) üzerinden event kabul eder.
- API key / permission ile erişimi kontrol eder.
- Event’i veritabanına yazar.
- Event’e bağlı `ProcessingState` üretir ve state machine’i başlatır.
- Broker’a (RabbitMQ/Celery) dispatch ederek asenkron processing akışını tetikler.

### 1.2 Bileşen Diyagramı (event_ingestor perspektifi)
```
Client
   |
   v
Nginx (Gateway)
   |
   v
event_ingestor (Django + DRF)
   |                |
   |                v
   |            RabbitMQ (Broker)
   v
PostgreSQL (Event + ProcessingState + Idempotency)

```

### 1.3 Veri Modelleri (Core)

**Event**
- immutable kabul edilir (yüksek write throughput için).
- minimal index yaklaşımı: ingest öncelikli, read optimizasyonu daha sonra.

**ProcessingState (infrastructure/workflow state)**
- Event’in “işlenme” durumunu takip eder (domain state değildir).
- worker crash / retry / recovery senaryolarında state tutarlılığı sağlar.

**ProcessedEventLog (idempotency/effect state)**
- Event’e uygulanan side-effect’in “tek sefer” olmasını sağlar.
- DB unique constraint ile atomik idempotency sağlar.

### 1.4 State Machine (Workflow)

TEM, ingest + processing akışını bir finite state machine olarak ele alır:

```

ACCEPTED  ->  QUEUED  ->  PROCESSING  ->  PROCESSED 
                                      ->  FAILED

```

Ek recovery geçişi:

```

PROCESSING --(timeout / stuck)--> QUEUED

```

Durumların anlamı (özet):
- ACCEPTED: API event’i kabul etti, DB’ye yazıldı.
- QUEUED: broker’a dispatch edildi, worker tarafından alınmayı bekliyor.
- PROCESSING: worker lock aldı ve işlem yapıyor.
- PROCESSED: iş başarıyla tamamlandı.
- FAILED: işlem hata ile sonuçlandı (yeniden deneme veya manuel aksiyon gerektirebilir).

### 1.5 Delivery Guarantee (Broker Katmanı)

`process_events_batch` gibi “gerçek iş yapan” task’lar için:

- `acks_late=True` kullanılır.
- worker task’ı alır almaz ack atmaz; iş tamamlanınca ack atar.
- worker crash olursa broker mesajı yeniden teslim edebilir.

Bu katmanın sağladığı garanti:
- **At-least-once delivery** (duplicate mümkündür, mesaj kaybı riski azalır)

### 1.6 State Consistency (DB Workflow Katmanı)

Broker mesajı tekrar teslim etse bile DB’de “PROCESSING’de takılı kalmış” state oluşabilir.
Bu nedenle recovery task’ı:

- belirli bir süre (locked_at eski) PROCESSING kalan kayıtları tespit eder
- tekrar QUEUED’a çeker

Bu katmanın modeli:
- **Eventually consistent workflow** (self-healing)

### 1.7 Effect Guarantee (Idempotency Katmanı)

At-least-once delivery nedeniyle duplicate execution mümkündür.
Side-effect’in duplicate olmasını engellemek için:

- `ProcessedEventLog` OneToOne/unique constraint kullanılır
- duplicate attempt -> `IntegrityError` -> side-effect skip edilir

Bu katmanın modeli:
- **Exactly-once effect** (delivery değil, “etki” tek sefer)

---

## 2) Platform Katmanı: TEM (Sistem Genel)

TEM, gateway + ingest + realtime + processing + observability hedefi olan bir platformdur.

### 2.1 Üst Seviye Topoloji

```
                    Clients
                       |
                       v
                  Nginx Gateway
                       |
        +------------+-------------------+
        |            |                   |
        v            v                   v


event_ingestor   realtime_gateway   api_services
(Django/DRF)     (WebSocket)        (FastAPI)
    |
    v
PostgreSQL  <->  RabbitMQ (Broker)
    |
    v
+----------------------------+
| Celery Worker Layer        |
| - processing_queue         |
| - maintenance_queue        |
+----------------------------+

```

Not:
- `event_ingestor`: ingest + workflow state üretimi
- `realtime_gateway` (WebSocket): client’lara realtime bildirim/stream
- `api_services` (FastAPI): async/performant API uçları veya özel işlevler (ihtiyaca göre)
- Gateway: rate limit, timeouts, tek giriş kapısı

### 2.2 Worker Ayrımı (Queue Separation)

Worker’lar iki queue ile ayrılır:

- `processing_queue`: ağır iş / batch processing
- `maintenance_queue`: recovery gibi bakım işleri

Neden?
- heavy load recovery’yi bloklamasın
- failure domain ayrışsın
- kaynaklar ayrı ayarlanabilsin (concurrency, prefetch, vs.)

Bu mimari, production’da daha stabil bir akış sağlar.

---

## 3) Failure Model (Örnek Senaryolar)

### 3.1 Worker crash (acks_late etkisi)

- Task iş bitmeden ack atmaz.
- worker crash -> broker mesajı yeniden “ready” yapabilir.
- worker geri gelince message re-deliver olur.

Beklenen sonuç:
- mesaj kaybı azalır, duplicate execution ihtimali vardır.

### 3.2 PROCESSING’de takılma (recovery etkisi)

- worker crash veya network issue sonrası DB state PROCESSING’de kalabilir.
- recovery task locked_at eski kayıtları QUEUED yapar.
- yeniden processing radarına girer.

Beklenen sonuç:
- workflow eventually consistent hale gelir.

### 3.3 Duplicate execution (idempotency etkisi)

- broker re-delivery veya recovery ile aynı event yeniden işlenebilir.
- side-effect (ör. log/outbox/webhook) duplicate olmasın diye DB unique constraint kullanılır.
- duplicate attempt -> IntegrityError -> safe skip + state PROCESSED.

Beklenen sonuç:
- exactly-once effect.

---

## 4) Trade-offs

neden böyle ilerlendi? 

Kararlar ve Gerekçeleri

### 4.1 Neden Kafka değil ?

- TEM’in hedefi önce **failure semantics + workflow + idempotency** öğretmek ve göstermek.
- Celery/RabbitMQ ile state machine + retry/recovery + acks_late kavramları daha hızlı deneyimleniyor.
- Kafka eklemek; operasyonel complexity, farklı consumer semantics ve ek altyapı yükü getirir.
- İleride “event bus” ihtiyacı netleşirse Kafka değerlendirilebilir.

### 4.2 Neden ProcessingState (DB) var? Sadece broker + idempotency yetmez mi?

- Sadece broker + idempotency ile “delivery ve effect” çözülür; fakat **workflow görünürlüğü** ve **stuck job recovery** zayıflar.
- ProcessingState, sistemin “şu an nerede kaldık?” sorusuna cevap vermesini sağlar.
- Recovery ile state machine self-healing hale gelir.
- Sonuç: daha az kırılgan, daha gözlemlenebilir bir workflow.

### 4.3 Neden cache yerine DB state?

- Cache, TTL ve restart/failover senaryolarında workflow state için daha kırılgan olabilir.
- DB, “source of truth” olarak audit/debug/forensics için daha güçlüdür.
- Workflow state’in kalıcılığı ve incelenebilirliği önemlidir.

### 4.4 Neden tek DB?

- Tek DB, transaction + locking (select_for_update) ile güçlü ve basit consistency sağlar.
- Öğrenme ve vitrin amacı için state + event aynı yerde izlenebilir.
- Microservice veri ayrımı (her servis kendi DB’si) daha ileri bir fazdır; daha fazla operational ve data consistency maliyeti getirir.

### 4.5 Neden distributed monolith?

- Tek repo/tek compose ile hızlı iterasyon ve net öğrenme.
- Failure semantics ve production pratiği gösterilirken, “tam microservice” karmaşıklığı erkenden eklenmez.
- Platform olgunlaştıkça servis sınırları (repo/deploy/db) daha bilinçli kırılabilir.

