# TelemetryEventMesh

---

## Nedir?

TelemetryEventMesh, mikroservislerin ürettiği iş olaylarını (event’leri) güvenli ve yetkilendirilmiş şekilde merkezi olarak kabul eden bir ingestion altyapısıdır.

Bu sistem:

* Servis kimlik doğrulaması yapar (API Key)
* Rol ve HTTP method bazlı yetkilendirme uygular
* Policy-driven permission modeli kullanır
* Event’leri PostgreSQL üzerinde saklar
* Container tabanlı dağıtık mimariye uygundur

Bu proje bir CRUD uygulaması değil, bir **event ingestion boundary** örneğidir.

---

## Ne İşe Yarar?

Dağıtık sistemlerde farklı servisler olay üretir:

* payment.success
* user.created
* order.cancelled

TelemetryEventMesh:

* Bu olayların kim tarafından gönderildiğini doğrular
* Yetkili olup olmadığını kontrol eder
* Olayı merkezi olarak kaydeder
* İleride başka sistemlere aktarılabilecek güvenli bir veri noktası oluşturur

Bu yapı özellikle:

* Event-driven sistemler
* Observability altyapıları
* Audit ve güvenlik sistemleri
* Gerçek zamanlı analiz pipeline’ları

için temel oluşturur.

---

## Stack

### Backend

* Python 3.12
* Django 5
* Django Rest Framework
* FastAPI (WebSocket ve async boundary için)
* Celery (asenkron task işleme)

### Asynchronous & Messaging

* RabbitMQ (message broker)
* Celery worker (prefork concurrency modeli)
* Redis (result backend ve cache)

### Database

* PostgreSQL 16
* UUID primary key
* JSONField (event payload saklama)
* pg_stat_statements (query gözlemlenebilirliği)

### Web & Gateway

* Nginx (reverse proxy + rate limiting)
* WebSocket gateway (FastAPI tabanlı)
* IP hash / least_conn load balancing stratejileri

### Infrastructure

* Docker
* Docker Compose
* Multi-network segmentation (public / internal / data)
* Healthchecks
* Resource limits (memory isolation)

### Observability & Testing

* pg_stat_statements (query analizi)
* k6 (yük testi)
* Structured logging
* Container-level monitoring (docker stats)

### CI/CD

* GitHub Actions (lint + test pipeline)
* Environment-based configuration (.env separation)

---

## Kısa Mimari Özeti

Bu proje:

* Sync (HTTP API) + Async (Celery) + Realtime (WebSocket) boundary içerir
* Event-driven sistem davranışını simüle eder
* Role-based ve policy-driven yetkilendirme uygular
* Çoklu container ve network segmentasyonu kullanır

---

## Permission Modeli

Permission formatı:

```
<app>.<http_method>.<view_name>
```

Örnek:

```
events.post.event_ingest
common.get.healthz
```

Yetki çözümleme:

1. Role (JSON policy)
2. Extra permissions (DB override)
3. Revoked permissions (DB override)

---

## Örnek Akış

Bir servis ödeme başarılı olduğunda şu isteği gönderir:

```
POST /api/events/
X-API-Key: <service_key>
```

Sistem:

* Servisi doğrular
* Yetkiyi kontrol eder
* Event’i kaydeder
* 202 Accepted döner

---

## Dokümantasyon

Proje mimari kararları ve teknik detaylar `docs/` klasörü altında bulunmaktadır:

* `docs/architecture.md` → Sistem mimarisi
* `docs/decisions/` → Mimari kararlar ve gerekçeleri
* `docs/runbooks/` → Operasyonel kullanım rehberi
* `docs/daily_notes/` → Günlük özetler

---

## Projenin Amacı

Bu proje:

* Policy-driven yetkilendirme modeli kurmak
* Event ingestion boundary tasarlamak
* Dağıtık sistem davranışını gözlemlemek
* Performans ve ölçeklenebilirlik testleri yapmak

amacıyla geliştirilmiştir.

---

## Kısa Tanım

> TelemetryEventMesh, mikroservislerin ürettiği iş olaylarını güvenli, yetkili ve gözlemlenebilir şekilde merkezi olarak kabul eden, container tabanlı dağıtık bir ingestion altyapısıdır.

