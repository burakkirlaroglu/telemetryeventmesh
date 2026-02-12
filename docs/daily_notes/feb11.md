### 11 Şubat

Bugün sistemi test etmeye başladım. k6 ile ilk load testleri yaptım. Basit bir control-api endpoint üzerinden trafiğin davranışını ölçtüm.

50 VU ve 100 VU senaryolarında:

* p95 değerlerini
* CPU kullanımını
* Container dağılımını

gözlemledim.

Ardından Nginx üzerinden birden fazla backend instance’a load balancing yapılandırdım. 3 adet control_api container ile round-robin davranışını test ettim.

WebSocket servislerini gateway arkasına koydum. Sticky session davranışını gözlemledim. Container kill ettiğimde bağlantı kopma ve yeniden bağlanma davranışını analiz ettim.

Redis üzerinde session state tuttum:

* TTL mekanizması
* reconnect sonrası resume
* sequence artışı

Container restart senaryosunda verinin Redis’te kaldığını ve session’ın kaldığı yerden devam edebildiğini doğruladım.

Bu günün ana çıktısı:

Sistem load altında çalışabiliyor.
Gateway → backend → redis akışı stabil.
WebSocket state yönetimi ve reconnect senaryosu test edildi.


