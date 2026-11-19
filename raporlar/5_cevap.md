# 5. Aşama: Cevap doğruluğu (API'siz)

Cevap = en uygun 3 parçadan seçilen 1-2 fıkra/cümle + belge, madde, sayfa, yürürlük tarihi.
Metin üretilmiyor, gösterilen her şey resmi metnin aynısı.

- Cevaplı soru doğru: asistan "bulamadım" demedi ve beklenen ifade gösterilen alıntıda geçiyor.
- Cevapsız soru doğru: asistan cevabı bulduğunu iddia etmedi ("bulamadım" ya da "kesin cevap bulamadım, ilgili olabilecek maddeler").

Eşikler: e5 benzerliği >= 0.85 ise "bulundu", < 0.825 ise "bulamadım", arası "belirsiz".

| Set | Cevaplı doğru | Cevapsız doğru | Cevapsızda doğrudan "bulamadım" |
|---|---|---|---|
| Ana set (eşik ayarında kullanıldı) | 26/27 | 3/3 | 1/3 |
| Kalibrasyon, cevapsız (eşik ayarında kullanıldı) | - | 15/15 | 8/15 |
| Ayrık set | 10/10 | 2/2 | 1/2 |
| Doğrulama seti (eşikten sonra yazıldı) | 7/8 | 6/8 | 2/8 |

## Hatalı sonuçlar

- [Ana set (eşik ayarında kullanıldı)] Kaydımı en fazla kaç dönem dondurabilirim? -> bulundu (benzerlik 0.864)
- [Doğrulama seti (eşikten sonra yazıldı)] Stajımı yaptığım kurumu değiştirebilir miyim? -> bulundu (benzerlik 0.862)
- [Doğrulama seti (eşikten sonra yazıldı)] Mezunlar derneğine nasıl üye olurum? -> bulundu (benzerlik 0.851)
- [Doğrulama seti (eşikten sonra yazıldı)] Akademik takvime göre güz dönemi ne zaman bitiyor? -> bulundu (benzerlik 0.867)

## Notlar

- Eşikler ana set + kalibrasyon sorularına bakılarak seçildi, doğrulama seti ondan sonra yazıldı. Doğrulama sonucuna göre eşik değiştirilmedi, yoksa o set de bağımsız olmazdı.
- Cevapsız bir soruya "bulundu" denmesi en riskli hata. Bu durumda bile asistan metin uydurmuyor, sadece alakasız bir maddeyi gösteriyor; kaynak ve sayfa her zaman yazılı.
- Benzerlik eşiği tek başına sınırlı: "Mezunlar derneği" gibi yönetmelikteki kelimelere yakın sorular eşiği geçebiliyor. Kelime kapsamı gibi ek sinyaller denendi, net ayırmadı.
