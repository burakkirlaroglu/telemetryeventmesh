### 14 Şubat

Bugün event processing pipeline’ını gerçek crash senaryosu ile test ettim. Amaç Celery ACK davranışının ve state machine tasarımının gerçekten ne anlama geldiğini gözlemlemekti.

### 1. Başlangıç Durumu – acks_late=False (default)

Worker crash testi yapıldı:

* 12 event oluşturuldu (QUEUED).
* Worker batch aldı.
* 9 tanesi PROCESSED oldu.
* 3 tanesi PROCESSING durumundayken worker durduruldu.

Gözlem:

* Broker tarafında message kayboldu (ACK erken gönderildiği için).
* 3 kayıt DB’de PROCESSING olarak kaldı.
* Worker restart edildiğinde bu 3 kayıt otomatik olarak tekrar işlenmedi.

Çıkarım:
acks_late=False durumunda worker task’ı alır almaz ACK gönderdiği için crash sonrası message broker’da tutulmaz. Bu, PROCESSING state’lerinin stuck kalmasına neden olabilir.

---

### 2. acks_late=True Deneyi

Celery task’ına `acks_late=True` eklendi ve aynı crash testi tekrarlandı.

Gözlem:

* Worker task’ı alıp PROCESSING durumuna geçti.
* Worker crash edildi.
* Broker tarafında message unacked durumundan ready durumuna geçti.
* Worker tekrar başlatıldığında ready olan task yeniden işlendi.
* DB state’leri sonunda PROCESSED oldu.

Çıkarım:
acks_late=True ile broker “at-least-once delivery” davranışı sergiliyor. Worker crash etse bile message kaybolmuyor ve yeniden işlenebiliyor.

Ancak:
Broker garantisi tek başına yeterli değil. DB state’i de doğru şekilde recovery edilebilir olmalı.

---

### 3. Kritik Farkındalık – Broker Garantisi ≠ İş Garantisi

Bugünkü en önemli öğrenme:

* Queue garantisi ile iş garantisi farklı kavramlar.
* acks_late=True message kaybını önler.
* Ancak DB’de PROCESSING state’leri recovery edilmezse sistem yine takılabilir.
* Distributed sistemlerde hem broker hem state katmanı düşünülmelidir.

---

### 4. DB / Worker Ayrı DB Sorunu

Test sürecinde worker’ın API ile aynı veritabanına bakmadığı fark edildi. Bu nedenle task başta boş dönüyordu. Environment yapılandırması düzeltilerek worker ve API’nin aynı Postgres instance’ına bağlanması sağlandı.

Çıkarım:
Distributed sistemlerde boş sonuçlar çoğu zaman kod hatası değil konfigürasyon problemidir.

---

### 5. Sonraki Adım (Plan)

Retry / Recovery mekanizması eklenecek:

* Dakikada bir çalışan ayrı bir task
* PROCESSING durumunda uzun süre kalmış (locked_at eski) kayıtları tespit edecek
* State’i tekrar QUEUED yapacak
* Böylece stuck işler yeniden işlenebilecek

Bu mekanizma broker garantisini DB state recovery ile tamamlayacak.

---

### Günün Sonuç Özeti

Bugün sistem:

* Gateway arkasında çalışıyor
* Async worker ile event işliyor
* Batch locking pattern’i doğru çalışıyor
* Crash senaryosu test edildi
* ACK davranışı gözlemlendi
* At-least-once delivery doğrulandı
* Recovery ihtiyacı netleşti

Bugün kod yazmaktan çok sistemin gerçek davranışı gözlemlendi ve distributed processing’in temel prensipleri pratik olarak doğrulandı.
