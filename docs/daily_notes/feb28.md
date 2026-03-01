### 28 Şubat

## Günün Ana Amacı

Event processing pipeline’ı **failure tolerant**, **retry-aware** ve **production davranışı simüle eden** hale getirmek.

Hedef artık sadece:

> event işlensin

değil,

> event fail olursa sistem nasıl hayatta kalır?

sorusuydu.

---

# 1. Mevcut Sistem Durumu (Başlangıç Noktası)

Pipeline zaten şu akışta çalışıyordu:

```
Event API
   ↓
Event
   ↓
ProcessingState
   ↓
Celery Worker
   ↓
Redis Publish
   ↓
WebSocket Gateway
   ↓
User Notification
```

State Machine:

```
QUEUED → PROCESSING → PROCESSED
```

Ama eksik olan kritik gerçek:

* Distributed sistemlerde **başarı normal durum değildir**
* Failure normaldir.

Bugün bu boşluk kapatıldı.

---

# 2. Retry Architecture Tasarımı

Bugün alınan en önemli karar:

## Retry = Celery retry değil

## Retry = Domain State Machine

Yani:

Celery’ye güvenmedik.

Çünkü:

* worker ölür
* broker restart olur
* task kaybolabilir
* retry state observable olmaz

Bunun yerine:

```
Retry state → DATABASE
```

taşındı.

Bu çok kritik bir mimari karar.

### Sonuç

System artık:

* restart safe
* worker independent
* observable retry lifecycle
* deterministic recovery

---

# 3. Eklenen Yeni Alanlar

ProcessingState modeli genişletildi:

```
retry_count
last_error
next_retry_at
```

Amaç:

| Alan          | Sebep              |
| ------------- | ------------------ |
| retry_count   | kaç kez denendi    |
| last_error    | debugging          |
| next_retry_at | scheduler kontrolü |

Bu noktadan sonra sistem:

> zamanı gelince retry eden

bir yapıya dönüştü.

---

# 4. Exponential Backoff + Jitter

Retry storm riskine karşı:

```
delay = base * 2^retry
+ random jitter
```

eklendi.

Sebep:

Eğer 10.000 event aynı anda fail olursa:

 * hepsi aynı saniye retry etmez x
 * zamana yayılır |

Bu gerçek production incident önlemidir.

AWS SQS, Kafka consumers, Google PubSub benzer bir mantığı kullanıyor olabilir.

---

# 5. Dead Letter Mantığı (Critical Decision)

Yeni state:

```
EXTINCT
```

eklendi.

Anlamı:

> Sistem artık otomatik retry etmeyecek.

Bu şu problemi çözer:

Infinite retry loop x
Queue starvation x
CPU burn x

Artık lifecycle:

```
QUEUED
 → PROCESSING
   → FAILED
     → RETRY
       → FAILED
         → EXTINCT
```

Bu noktada TEM:

gerçek message system davranışı kazandı.

---

# 6. Retry Scheduler Mantığı

Yeni maintenance task:

```
retry_failed_events
```

Görevi:

```
FAILED
AND next_retry_at <= now
        ↓
QUEUED
        ↓
worker wakeup
```

Önemli teknik detay:

```python
process_events_batch.apply_async(queue="processing_queue")
```

eklendi.

Sebep:

Worker idle kalmasın.

Yani sistem artık:

* self-healing
* self-triggering

---

# 7. Yapılan Testler

## Test 1 — Simulated Failure

Worker içine bilinçli exception eklendi.

Beklenen:

```
retry_count ↑
status = FAILED
next_retry_at set
```

doğrulandı.

---

## Test 2 — Retry Progression

Beklenen sıra:

```
retry 1 → ~10s
retry 2 → ~20s
retry 3 → ~40s
```

exponential davranış doğrulandı.

---

## Test 3 — Max Retry

MAX_RETRY_COUNT aşıldığında:

```
status → EXTINCT
retry durur
```

doğrulandı.

---

## Test 4 — Recovery Flow

FAILED → scheduler → QUEUED → PROCESSING → PROCESSED

tam lifecycle çalıştı.

---

# 8. Kritik Bug (Bugünün En Değerli Öğrenmesi)

Problem:

```
retry_count artmıyor
```

Sebep:

Worker memory'deki state stale idi.

Row başka transaction’da değişmişti.

Çözüm:

```python
state.refresh_from_db()
```

Bu küçük satır:

* distributed consistency problemi çözümü.

Bugünün en değerli kazanımlarından biri.

---

# 9. Sistem Artık Ne Kazandı?

TEM şu özellikleri aldı:

✅ DB-backed idempotency
✅ Retry orchestration
✅ Failure isolation
✅ Dead letter handling
✅ Exponential retry
✅ Self recovery
✅ Observable lifecycle
