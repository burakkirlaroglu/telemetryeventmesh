### 12 Şubat

Bugün event modeli üzerinden status alanının performans ve mimari etkisini analiz ettim. Amacım write-heavy bir tabloda index eklemenin gerçek maliyetini ölçmekti, teorik değil deneysel ilerlemek istedim.

İlk olarak Event modeline `status` alanını ekledim. Hiç index eklemeden k6 ile stres testine soktum. Veri yokken sistem oldukça rahattı. CPU değerleri normal aralıktaydı, p95 değerlerinde anormal bir artış yoktu. Write tarafı stabil görünüyordu.

İkinci adımda `status` alanına index ekleyerek aynı testi tekrar çalıştırdım. Veri hacmi düşük olduğu için ciddi bir fark gözle görülmedi. Hafif bir artış vardı ancak sistem bunu rahatlıkla taşıyabiliyordu. Bu aşamada index maliyeti çok belirgin değildi.

Üçüncü aşamada tabloya yaklaşık 500 bin kayıt bastım ve aynı testi yeniden çalıştırdım. Bu noktada fark net şekilde ortaya çıktı. CPU kullanımı 20-30 bandından 50 seviyelerine çıktı. p95 değerlerinde belirgin artış oldu. Sistem süreci yine handle etti ancak maliyet bariz şekilde yükseldi. Write path üzerindeki baskı hissedilir düzeydeydi.

Buradan şu çıkarıma ulaştım:

Status alanı sürekli güncellenen bir kolon. Bu kolon indexli olduğunda her update işlemi yalnızca satır değişimi değil, aynı zamanda index entry invalidate + yeniden yazma anlamına geliyor. PostgreSQL tarafında update’in aslında yeni tuple üretmesi ve eskiyi invalid etmesi, indexli kolon değiştiğinde HOT update mekanizmasının devre dışı kalmasına neden oluyor. Bu da write amplification oluşturuyor.

Yani status gibi sık değişen bir alanı büyük ve write-heavy bir tabloda indexlemek uzun vadede performans maliyetini ciddi şekilde artırabilir.

Bu nedenle status bilgisini Event tablosundan ayırıp ayrı bir ProcessingState tablosunda tutma kararı aldım. Böylece:

* Event immutable kalacak.
* Write path sadeleşecek.
* Status update maliyeti daha küçük ve yönetilebilir bir tabloda gerçekleşecek.
* Index stratejisi daha kontrollü tasarlanabilecek.

---

### Test Özeti

Aşağıdaki sonuçlar bu çıkarımın temelini oluşturuyor:

Durum 1 – Index yok, düşük veri
CPU stabil, latency düşük, p95 normal aralıkta.

Durum 2 – Index var, düşük veri
Hafif artış var ancak gözle görülür değil. Sistem rahat.

Durum 3 – Index var, ~500k veri
CPU 20-30 seviyesinden 50 civarına çıktı.
p95 değerlerinde belirgin artış oldu.
Write maliyeti ciddi şekilde yükseldi ancak sistem tamamen çökmedi.

Sonuç olarak write-heavy ve mutable bir kolon üzerinde index kullanımı veri büyüdükçe maliyetli hale geliyor. Bu deneyimle birlikte ingestion tasarımını immutable event + ayrı state tablosu şeklinde ilerletmeye karar verdim.

Yarın hedef: ProcessingState modelini oluşturmak ve composition yaklaşımını uygulamaya geçirmek.
