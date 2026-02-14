### 13 Şubat

Bugün projenin mimari olarak önemli bir aşamasını tamamladım. Django servisinin sadece internal network üzerinden erişilebilir olmasını sağlayarak Nginx’i tek giriş noktası haline getirdim. Böylece sistem artık production benzeri bir trafik akışına sahip oldu: dış istekler önce Nginx’e geliyor, oradan Django’ya yönleniyor. Django public port expose etmiyor.

Bu kararın temel nedeni güvenlik ve kontrol. Rate limit, timeout ve ileride eklenecek ek gateway kontrollerinin tek noktadan yönetilebilmesi için API doğrudan dış dünyaya açık olmamalı.

Ardından Celery entegrasyonunu gerçekleştirdim. Django projesi içerisine worker eklendi ve RabbitMQ broker üzerinden görev alacak şekilde yapılandırıldı. Bu aşamada amaç business logic’i request-response döngüsünden ayırmak ve event processing’i asenkron hale getirmekti.

İlk task olarak `process_events_batch` fonksiyonunu ekledim. Bu task şu an basit bir ORM sorgusu ile event’leri alıp durum güncellemesi yapıyor. Gerçek processing logic daha sonra eklenecek. Şu an amaç altyapının doğru çalıştığını teyit etmekti.

Docker Compose tarafında:

* Worker servisi eklendi.
* Django ve worker için network düzenlemeleri yapıldı.
* PostgreSQL’e pg_stat_statements eklendi, böylece ileride query performans analizi yapılabilecek.
* Requirements dosyasına celery ve redis eklendi.

Tek image yaklaşımı tercih edildi. API ve worker aynı image üzerinden farklı command ile çalışıyor. Bunun nedeni dependency drift riskini azaltmak ve CI/CD sürecini sade tutmak. Django ORM kullanan worker için ayrı image üretmek şu aşamada yorucu olurdu.

Sistem şu an şu şekilde çalışıyor:

Client → Nginx → Django API → Event oluşturma → Celery task dispatch → Worker → DB update

Bu haliyle proje artık sadece CRUD uygulaması değil, asenkron işlem yapabilen, gateway arkasında çalışan gözlemlenebilir bir servis yapısına evrildi.