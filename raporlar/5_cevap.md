# 5. Aşama: Cevap doğruluğu (API'siz)

Cevap = kısa cevap (ozetler.yaml'daki elle yazılmış sade cümlelerden seçilir) + en uygun 3 parçadan seçilen 1-2 fıkra/cümle + belge, madde, sayfa, yürürlük tarihi.
Çalışırken metin üretilmiyor; kaynak alıntıları resmi metnin aynısı.

- Cevaplı soru doğru: asistan "bulamadım" demedi ve beklenen ifade gösterilen alıntıda geçiyor.
- Cevapsız soru doğru: asistan cevabı bulduğunu iddia etmedi ("bulamadım" ya da "kesin cevap bulamadım, ilgili olabilecek maddeler").

Eşikler: e5 benzerliği >= 0.85 ise "bulundu", < 0.825 ise "bulamadım", arası "belirsiz".

- Kısa cevap doğru: kısa cevabın dayandığı maddelerden biri sorunun doğru kaynağı ("ilk cümle" sütununda en üstteki cümlenin maddesi).

| Set | Cevaplı doğru | Cevapsız doğru | Cevapsızda doğrudan "bulamadım" | Kısa cevap doğru maddeye dayanıyor | İlk cümle doğru maddeden |
|---|---|---|---|---|---|
| Ana set (eşik ayarında kullanıldı) | 26/27 | 3/3 | 1/3 | 24/27 | 23/27 |
| Kalibrasyon, cevapsız (eşik ayarında kullanıldı) | - | 14/15 | 8/15 | - | - |
| Ayrık set | 10/10 | 2/2 | 1/2 | 10/10 | 10/10 |
| Doğrulama seti (eşikten sonra yazıldı) | 8/8 | 6/8 | 2/8 | 8/8 | 7/8 |
| Fen Fakültesi diğer bölümler | 13/16 | 1/2 | 0/2 | 14/16 | 14/16 |
| Mühendislik Fakültesi | 14/18 | 1/2 | 0/2 | 17/18 | 16/18 |
| Bilgisayar ve Bilişim Bilimleri Fakültesi | 13/15 | 0/2 | 0/2 | 15/15 | 15/15 |
| Havacılık ve Uzay Bilimleri Fakültesi | 13/18 | 0/2 | 0/2 | 15/16 | 15/16 |

## Hatalı sonuçlar

- [Ana set (eşik ayarında kullanıldı)] Kaydımı en fazla kaç dönem dondurabilirim? -> bulundu (benzerlik 0.857)
- [Kalibrasyon, cevapsız (eşik ayarında kullanıldı)] Erasmus için kaç dil puanı gerekiyor? -> bulundu (benzerlik 0.869)
- [Doğrulama seti (eşikten sonra yazıldı)] Mezunlar derneğine nasıl üye olurum? -> bulundu (benzerlik 0.851)
- [Doğrulama seti (eşikten sonra yazıldı)] Akademik takvime göre güz dönemi ne zaman bitiyor? -> bulundu (benzerlik 0.867)
- [Fen Fakültesi diğer bölümler] Biyoloji bölümünde hazırlık okumak zorunlu mu? -> bulundu (benzerlik 0.876)
- [Fen Fakültesi diğer bölümler] Fizik bölümünden mezun olmak için proje şartı var mı? -> bulundu (benzerlik 0.878)
- [Fen Fakültesi diğer bölümler] Matematik bölümünde kaç AKTS ile mezun olunur? -> bulundu (benzerlik 0.865)
- [Fen Fakültesi diğer bölümler] Kimya bölümünün laboratuvar önlüğü nereden alınır? -> bulundu (benzerlik 0.857)
- [Mühendislik Fakültesi] Dönem içinde staj yapabilir miyim? -> bulundu (benzerlik 0.885)
- [Mühendislik Fakültesi] Elektrik elektronik bölümünde hazırlık var mı? -> belirsiz (benzerlik 0.849)
- [Mühendislik Fakültesi] İnşaat mühendisleri nerede çalışabilir? -> bulundu (benzerlik 0.874)
- [Mühendislik Fakültesi] Uçak mühendisliğinde kaç AKTS ile mezun olunur? -> bulundu (benzerlik 0.872)
- [Mühendislik Fakültesi] Makine mühendisliği bölümünün kantini nerede? -> bulundu (benzerlik 0.852)
- [Bilgisayar ve Bilişim Bilimleri Fakültesi] Birinci yarıyılda hangi dersleri alacağım? -> bulundu (benzerlik 0.86)
- [Bilgisayar ve Bilişim Bilimleri Fakültesi] Bilişim sistemlerinde eğitim dili nedir? -> bulundu (benzerlik 0.858)
- [Bilgisayar ve Bilişim Bilimleri Fakültesi] Yapay zeka bölümünün hackathon takımı var mı? -> bulundu (benzerlik 0.853)
- [Bilgisayar ve Bilişim Bilimleri Fakültesi] Bilişim sistemleri bölümünün laboratuvar saatleri nedir? -> bulundu (benzerlik 0.856)
- [Havacılık ve Uzay Bilimleri Fakültesi] Kaç gün staj yapmam gerekiyor? -> bulundu (benzerlik 0.881)
- [Havacılık ve Uzay Bilimleri Fakültesi] Staja ne zaman başlayabilirim? -> bulundu (benzerlik 0.877)
- [Havacılık ve Uzay Bilimleri Fakültesi] Yatay geçişle geldim, eski stajım sayılır mı? -> belirsiz (benzerlik 0.849)
- [Havacılık ve Uzay Bilimleri Fakültesi] Eğitim dili nedir? -> bulunamadi (benzerlik 0.823)
- [Havacılık ve Uzay Bilimleri Fakültesi] Güvenlik soruşturması yapılıyor mu? -> bulunamadi (benzerlik 0.82)
- [Havacılık ve Uzay Bilimleri Fakültesi] Hava trafik bölümünün simülatör saatleri nedir? -> bulundu (benzerlik 0.865)
- [Havacılık ve Uzay Bilimleri Fakültesi] Havacılık yönetimi öğrencilerine uçuş eğitimi veriliyor mu? -> bulundu (benzerlik 0.859)

## Notlar

- Eşikler ana set + kalibrasyon sorularına bakılarak seçildi, doğrulama seti ondan sonra yazıldı. Doğrulama sonucuna göre eşik değiştirilmedi, yoksa o set de bağımsız olmazdı.
- Cevapsız bir soruya "bulundu" denmesi en riskli hata. Bu durumda bile asistan metin uydurmuyor, sadece alakasız bir maddeyi gösteriyor; kaynak ve sayfa her zaman yazılı.
- Özet sıralaması eklenince kalibrasyonda bir soru ("Erasmus için kaç dil puanı gerekiyor?") "bulundu"ya geçti (15/15 -> 14/15): yönetmelik 6. madde özetinde "Erasmus" kelimesi geçiyor ve dil sınavı eşdeğerlikleri maddesi de soruya yakın. Diğer setlerdeki kazanç daha büyük olduğu için tutuldu.
- Benzerlik eşiği tek başına sınırlı: "Mezunlar derneği" gibi yönetmelikteki kelimelere yakın sorular eşiği geçebiliyor. Kelime kapsamı gibi ek sinyaller denendi, net ayırmadı.

## Kısa cevap

- Her parça için 1-13 sade özet cümlesi elle yazıldı (ozetler.yaml, 181 parça, ~400 cümle). Cümleler madde metninin dışına çıkmıyor ve tek başına okunduğunda anlaşılacak şekilde yazıldı.
- Seçim: en iyi 5 parçanın cümleleri; puan = e5(soru, cümle) + 0,10 x kelime örtüşmesi (idf ağırlıklı) + 1,0 x e5(soru, madde) + ilk cümleye 0,02. En iyi puana 0,015'ten yakın olan en fazla 3 cümle, aynı kuralı tekrar edenler elenerek gösteriliyor.
- Ağırlıklar 19 soruluk ayrı bir listede (arayüzdeki 6 örnek soru dahil) doğru cümlenin ilk sırada gelmesine bakılarak seçildi: 17/19. Hiç kullanılmamış 11 yeni soruda doğru cümle 8/11 ilk sırada, 9/11 cevabın içinde.
- Yalnızca e5 benzerliği kısa cümlelerde gürültülü çıktı ("Kaç iş günü staj yapmalıyım?" sorusuna proje temelli staj cümlesi geliyordu); maddenin bütününün benzerliği eklenince düzeldi.
- Kısa cevap "bulamadım" durumunda gösterilmiyor. "Belirsiz" durumda uyarıyla gösteriliyor.
- Sınır: özet cümleleri elle yazıldığı için belge güncellenince ilgili cümlelerin de güncellenmesi gerekiyor (test, her parçanın özeti olduğunu kontrol ediyor).
