# 5. Aşama: Cevap doğruluğu (API'siz)

Cevap = kısa cevap (ozetler.yaml'daki elle yazılmış sade cümlelerden seçilir) + en uygun 3 parçadan seçilen 1-2 fıkra/cümle + belge, madde, sayfa, yürürlük tarihi.
Çalışırken metin üretilmiyor; kaynak alıntıları resmi metnin aynısı.

- Cevaplı soru doğru: asistan "bulamadım" demedi ve beklenen ifade gösterilen alıntıda geçiyor.
- Cevapsız soru doğru: asistan cevabı bulduğunu iddia etmedi ("bulamadım" ya da "kesin cevap bulamadım, ilgili olabilecek maddeler").

Eşikler: e5 benzerliği >= 0.85 ise "bulundu", < 0.825 ise "bulamadım", arası "belirsiz".

- Kısa cevap doğru: kısa cevabın dayandığı maddelerden biri sorunun doğru kaynağı ("ilk cümle" sütununda en üstteki cümlenin maddesi).

| Set | Cevaplı doğru | Cevapsız doğru | Cevapsızda doğrudan "bulamadım" | Kısa cevap doğru maddeye dayanıyor | İlk cümle doğru maddeden |
|---|---|---|---|---|---|
| Ana set (eşik ayarında kullanıldı) | 26/27 | 3/3 | 1/3 | 24/27 | 22/27 |
| Kalibrasyon, cevapsız (eşik ayarında kullanıldı) | - | 15/15 | 8/15 | - | - |
| Ayrık set | 10/10 | 2/2 | 1/2 | 10/10 | 9/10 |
| Doğrulama seti (eşikten sonra yazıldı) | 7/8 | 6/8 | 2/8 | 7/8 | 7/8 |

## Hatalı sonuçlar

- [Ana set (eşik ayarında kullanıldı)] Kaydımı en fazla kaç dönem dondurabilirim? -> bulundu (benzerlik 0.864)
- [Doğrulama seti (eşikten sonra yazıldı)] Stajımı yaptığım kurumu değiştirebilir miyim? -> bulundu (benzerlik 0.862)
- [Doğrulama seti (eşikten sonra yazıldı)] Mezunlar derneğine nasıl üye olurum? -> bulundu (benzerlik 0.851)
- [Doğrulama seti (eşikten sonra yazıldı)] Akademik takvime göre güz dönemi ne zaman bitiyor? -> bulundu (benzerlik 0.867)

## Notlar

- Eşikler ana set + kalibrasyon sorularına bakılarak seçildi, doğrulama seti ondan sonra yazıldı. Doğrulama sonucuna göre eşik değiştirilmedi, yoksa o set de bağımsız olmazdı.
- Cevapsız bir soruya "bulundu" denmesi en riskli hata. Bu durumda bile asistan metin uydurmuyor, sadece alakasız bir maddeyi gösteriyor; kaynak ve sayfa her zaman yazılı.
- Benzerlik eşiği tek başına sınırlı: "Mezunlar derneği" gibi yönetmelikteki kelimelere yakın sorular eşiği geçebiliyor. Kelime kapsamı gibi ek sinyaller denendi, net ayırmadı.

## Kısa cevap

- Her parça için 1-13 sade özet cümlesi elle yazıldı (ozetler.yaml, 181 parça, ~400 cümle). Cümleler madde metninin dışına çıkmıyor ve tek başına okunduğunda anlaşılacak şekilde yazıldı.
- Seçim: en iyi 5 parçanın cümleleri; puan = e5(soru, cümle) + 0,10 x kelime örtüşmesi (idf ağırlıklı) + 1,0 x e5(soru, madde) + ilk cümleye 0,02. En iyi puana 0,015'ten yakın olan en fazla 3 cümle, aynı kuralı tekrar edenler elenerek gösteriliyor.
- Ağırlıklar 19 soruluk ayrı bir listede (arayüzdeki 6 örnek soru dahil) doğru cümlenin ilk sırada gelmesine bakılarak seçildi: 17/19. Hiç kullanılmamış 11 yeni soruda doğru cümle 8/11 ilk sırada, 9/11 cevabın içinde.
- Yalnızca e5 benzerliği kısa cümlelerde gürültülü çıktı ("Kaç iş günü staj yapmalıyım?" sorusuna proje temelli staj cümlesi geliyordu); maddenin bütününün benzerliği eklenince düzeldi.
- Kısa cevap "bulamadım" durumunda gösterilmiyor. "Belirsiz" durumda uyarıyla gösteriliyor.
- Sınır: özet cümleleri elle yazıldığı için belge güncellenince ilgili cümlelerin de güncellenmesi gerekiyor (test, her parçanın özeti olduğunu kontrol ediyor).
