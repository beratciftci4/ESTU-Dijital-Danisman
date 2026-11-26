# 5. Aşama: Cevap doğruluğu (API'siz)

Cevap = kısa cevap (ozetler.yaml'daki elle yazılmış sade cümlelerden seçilir) + en uygun 3 parçadan seçilen 1-2 fıkra/cümle + belge, madde, sayfa, yürürlük tarihi.
Çalışırken metin üretilmiyor; kaynak alıntıları resmi metnin aynısı.

- Cevaplı soru doğru: asistan "bulamadım" demedi ve beklenen ifade gösterilen alıntıda geçiyor.
- Cevapsız soru doğru: asistan cevabı bulduğunu iddia etmedi ("bulamadım" ya da "kesin cevap bulamadım, ilgili olabilecek maddeler").

Güven skoru = (en yakın özet cümlesinin e5 benzerliği + 0.35 x ilk 3 parçanın en iyi e5 benzerliği) / 1.35.
Eşikler: skor >= 0.868 ise "bulundu", < 0.85 ise "bulamadım", arası "belirsiz".

- Kısa cevap doğru: kısa cevabın dayandığı maddelerden biri sorunun doğru kaynağı ("ilk cümle" sütununda en üstteki cümlenin maddesi).

| Set | Cevaplı doğru | Cevapsız doğru | Cevapsızda doğrudan "bulamadım" | Kısa cevap doğru maddeye dayanıyor | İlk cümle doğru maddeden |
|---|---|---|---|---|---|
| Ana set (eşik ayarında kullanıldı) | 26/27 | 3/3 | 3/3 | 24/27 | 23/27 |
| Kalibrasyon, cevapsız (eşik ayarında kullanıldı) | - | 15/15 | 11/15 | - | - |
| Ayrık set | 10/10 | 2/2 | 1/2 | 10/10 | 10/10 |
| Doğrulama seti (eşikten sonra yazıldı) | 8/8 | 7/8 | 4/8 | 8/8 | 7/8 |
| Fen Fakültesi diğer bölümler | 13/16 | 2/2 | 1/2 | 14/16 | 14/16 |
| Mühendislik Fakültesi | 14/18 | 2/2 | 0/2 | 17/18 | 16/18 |
| Bilgisayar ve Bilişim Bilimleri Fakültesi | 13/15 | 2/2 | 1/2 | 15/15 | 15/15 |
| Havacılık ve Uzay Bilimleri Fakültesi | 14/18 | 1/2 | 0/2 | 17/17 | 17/17 |
| Mimarlık ve Tasarım Fakültesi | 17/18 | 1/2 | 1/2 | 16/18 | 15/18 |
| Spor Bilimleri Fakültesi | 13/16 | 2/2 | 1/2 | 14/15 | 14/15 |
| Yıllık ders planları ve tek ders soruları | 11/15 | - | - | 13/15 | 12/15 |
| Cevapsız doğrulama, 40 soru (eşik seçilirken bakılmadı) | - | 36/40 | 25/40 | - | - |

## Hatalı sonuçlar

- [Ana set (eşik ayarında kullanıldı)] Kaydımı en fazla kaç dönem dondurabilirim? -> bulundu (benzerlik 0.873)
- [Doğrulama seti (eşikten sonra yazıldı)] Psikolojik danışmanlık randevusu nasıl alınır? -> bulundu (benzerlik 0.869)
- [Fen Fakültesi diğer bölümler] Biyoloji bölümünde hazırlık okumak zorunlu mu? -> bulundu (benzerlik 0.9)
- [Fen Fakültesi diğer bölümler] Fizik bölümünden mezun olmak için proje şartı var mı? -> bulundu (benzerlik 0.884)
- [Fen Fakültesi diğer bölümler] Matematik bölümünde kaç AKTS ile mezun olunur? -> bulundu (benzerlik 0.897)
- [Mühendislik Fakültesi] Dönem içinde staj yapabilir miyim? -> bulundu (benzerlik 0.889)
- [Mühendislik Fakültesi] Elektrik elektronik bölümünde hazırlık var mı? -> bulundu (benzerlik 0.869)
- [Mühendislik Fakültesi] İnşaat mühendisleri nerede çalışabilir? -> bulundu (benzerlik 0.902)
- [Mühendislik Fakültesi] Uçak mühendisliğinde kaç AKTS ile mezun olunur? -> bulundu (benzerlik 0.904)
- [Bilgisayar ve Bilişim Bilimleri Fakültesi] Birinci yarıyılda hangi dersleri alacağım? -> bulundu (benzerlik 0.88)
- [Bilgisayar ve Bilişim Bilimleri Fakültesi] Bilişim sistemlerinde eğitim dili nedir? -> bulundu (benzerlik 0.875)
- [Havacılık ve Uzay Bilimleri Fakültesi] Kaç gün staj yapmam gerekiyor? -> bulundu (benzerlik 0.893)
- [Havacılık ve Uzay Bilimleri Fakültesi] Staja ne zaman başlayabilirim? -> bulundu (benzerlik 0.888)
- [Havacılık ve Uzay Bilimleri Fakültesi] Yatay geçişle geldim, eski stajım sayılır mı? -> belirsiz (benzerlik 0.86)
- [Havacılık ve Uzay Bilimleri Fakültesi] Eğitim dili nedir? -> bulunamadi (benzerlik 0.845)
- [Havacılık ve Uzay Bilimleri Fakültesi] Havacılık yönetimi öğrencilerine uçuş eğitimi veriliyor mu? -> bulundu (benzerlik 0.88)
- [Mimarlık ve Tasarım Fakültesi] Fabrika stajı kaç gün? -> belirsiz (benzerlik 0.86)
- [Mimarlık ve Tasarım Fakültesi] İç mimarlık bölümünde hangi çizim programları öğretiliyor? -> bulundu (benzerlik 0.88)
- [Spor Bilimleri Fakültesi] Staj zorunlu mu? -> bulundu (benzerlik 0.892)
- [Spor Bilimleri Fakültesi] Kaç gün staj yapmam gerekiyor? -> bulundu (benzerlik 0.9)
- [Spor Bilimleri Fakültesi] Öğretmenlik uygulaması hangi dönemde? -> bulunamadi (benzerlik 0.846)
- [Yıllık ders planları ve tek ders soruları] Birinci yarıyılın zorunlu dersleri neler? -> bulundu (benzerlik 0.879)
- [Yıllık ders planları ve tek ders soruları] Mobil programlama dersi kaldırıldı mı? -> bulundu (benzerlik 0.873)
- [Yıllık ders planları ve tek ders soruları] Hangi seçmeli dersler yeni eklendi? -> bulundu (benzerlik 0.869)
- [Yıllık ders planları ve tek ders soruları] Makine öğrenmesi dersi zorunlu mu? -> belirsiz (benzerlik 0.864)
- [Cevapsız doğrulama, 40 soru (eşik seçilirken bakılmadı)] Havacılık yönetimi mezunları ortalama kaç maaş alıyor? -> bulundu (benzerlik 0.882)
- [Cevapsız doğrulama, 40 soru (eşik seçilirken bakılmadı)] Yaz okulunda başka şehirde kalacak yer bulunuyor mu? -> bulundu (benzerlik 0.87)
- [Cevapsız doğrulama, 40 soru (eşik seçilirken bakılmadı)] Danışmanımı değiştirebilir miyim? -> bulundu (benzerlik 0.884)
- [Cevapsız doğrulama, 40 soru (eşik seçilirken bakılmadı)] Sınav sonuçlarına itiraz ederken harç ödenir mi? -> bulundu (benzerlik 0.881)

## Notlar

- Güven skoru 26.11.2026'da değişti. Eskiden sadece en iyi parçanın e5 benzerliğine bakılıyordu; 30 bölümle belge sayısı artınca neredeyse her soruya benzeyen bir parça çıktı ve cevapsız soruların çoğu "bulundu" oldu. 186 soruda (146 cevaplı, 40 cevapsız) sinyaller karşılaştırıldı (ROC AUC): parça e5 0.91, özet cümlesi e5 0.95, ikisinin ağırlıklı ortalaması 0.95 (5 katlı çapraz doğrulama). Eşikler bu sorularla seçildi; ayrıca yazılan 40 cevapsız soruda doğrudan "bulamadım" 11/40'tan 25/40'a çıktı, "bulundu" 8'den 6'ya indi.
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
