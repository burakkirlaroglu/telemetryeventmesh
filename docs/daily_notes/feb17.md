### 17 Şubat

## 1. Idempotency Katmanı Eklendi

Bugün en kritik adım: side-effect idempotency.

Problem:
Celery `acks_late=True` ile broker seviyesinde mesaj kaybını engelliyoruz.
Ancak worker crash + retry durumunda aynı event iki kere işlenebilir.

Çözüm:
`ProcessedEventLog` modeli eklendi.

```python
class ProcessedEventLog(models.Model):
    event = models.OneToOneField(Event, ...)
```

OneToOne constraint sayesinde:

* Aynı event için ikinci side-effect insert edilemez.
* Duplicate execution durumunda `IntegrityError` oluşur.
* Task bunu yakalayıp state’i PROCESSED yapar.

Sonuç:
At-least-once delivery
Exactly-once effect

Bu idempotency DB unique constraint ile sağlandı.
Application-level kontrol yerine database-level garanti tercih edildi.

Bu bilinçli bir tasarım kararıdır.

---

## 2. acks_late Davranışı Test Edildi

`process_events_batch` için:

```
acks_late=True
```

Test senaryosu:

* Worker PROCESSING durumundayken kill edildi.
* RabbitMQ mesajı unacked → ready durumuna döndü.
* Worker yeniden başlatıldığında mesaj tekrar işlendi.

Sonuç:

Broker mesaj kaybetmiyor.
Crash sonrası mesaj yeniden teslim ediliyor.

Recovery mekanizması olmadan bile broker tarafı garantiyi sağlıyor.

---

## 3. Recovery Task Gerçekten Çalışıyor mu Test Edildi

Recovery task:

* PROCESSING durumunda uzun kalan kayıtları
* QUEUED’a geri çeviriyor.

Test:

* Worker kill edildi.
* PROCESSING kalan kayıtlar gözlemlendi.
* Worker restart sonrası:

    * Broker re-delivery yaptı.
    * Recovery task da devreye girdi.

Önemli öğrenim:

Recovery task Celery üzerinden çalıştığı için worker yokken çalışmaz.
Worker ayağa kalkınca sistem toparlanır.

Bu eventual consistency modelidir.

---

## 4. Queue Separation Yapıldı

Tek worker yerine iki ayrı worker’a geçildi:

* processing_queue → ağır batch task
* maintenance_queue → recovery task

Celery routing:

```python
@shared_task(queue="processing_queue", acks_late=True)
@shared_task(queue="maintenance_queue")
```

Docker Compose:

* celery_worker_processing
* celery_worker_maintenance

Sonuç:

Failure domain isolation sağlandı.
Heavy load recovery’yi bloklamıyor.

Bu separation özellikle gerçek sistemlerde kritik.

---

## 5. Prefetch Davranışı Konuşuldu

`--prefetch-multiplier=1` konusu değerlendirildi.

Şu an eklenmedi çünkü:

* Erken optimizasyon gereksiz.
* Önce gözlemleme yapılmalı.

İleride throughput testlerinde değerlendirilecek.

---

## 6. Sistem Son Durumu

Şu anda sistem özellikleri:

* Ingest API
* ProcessingState state machine
* Using `select_for_update` provides DB row-level locking
* At-least-once delivery
* Idempotent side-effect
* Recovery loop
* Multi-queue worker separation
* Broker re-delivery test edildi

---

## 7. Öğrenilen Kritik Kavramlar

* Broker guarantee ≠ exactly-once
* acks_late mesaj kaybını engeller, duplicate’i engellemez
* Idempotency application değil, DB constraint ile daha güçlüdür
* Recovery eventual consistency sağlar
* Worker separation production stabilitesi artırır
