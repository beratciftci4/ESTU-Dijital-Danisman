# 2. Aşama: Maddelere ayrıştırma

`python ayristir.py` kaynaklar/ altındaki 11 belgeyi 189 parçaya ayırıyor (`cikti/parcalar.jsonl`).

| Belge | Parçalar | Not |
|---|---|---|
| Yönetmelik | 30 madde (1-29 + 20/A), künye | `MADDE 10-` biçimi |
| Fen Fakültesi Staj Yönergesi | 18 madde, 11 ek, künye | `MADDE 1‒`, `MADDE 14 Öğrenci...` (ayraçsız) |
| Akademik Danışmanlık Yönergesi | 15 madde, künye | `MADDE 1 –` |
| Proje Temelli Staj Yönergesi | 22 madde, 1 ek, künye | |
| Haklı ve Geçerli Nedenler | giriş, 11 bent, künye | `1)` numaralı |
| Tek Ders Sınavı Esasları | giriş, 9 bent, 1 ek (dilekçe), künye | |
| Yaz Okulu Esasları | 23 bent, künye | |
| Not Karşılıkları | giriş, 9 bent, künye, 4 görsel tablo uyarısı | `1-` numaralı, tablolu |
| Ek Sınav Esasları | giriş, 3 bölüm, künye | taranmış, OCR |
| Bologna ders planı | 8 yarıyıl + mesleki seçmeli + seçmeli | html tablo |
| Bologna program bilgileri | 9 başlık | html |

Her parçada belge adı, madde/bent no, başlık, bölüm, başlangıç ve bitiş sayfası, kaynak URL,
yürürlük ve son değişiklik tarihi tutuluyor.

## Nasıl ayrıştırılıyor

- Madde sınırı satır başındaki `MADDE n` (ya da `n)`, `n-`, OCR'da `n.`). Numaraların sırayla
  gitmesi şartı var, böylece metin içindeki bir sayı yanlışlıkla yeni madde sayılmıyor.
- Maddenin üstündeki kısa satır başlık, `İKİNCİ BÖLÜM` + sonraki satır bölüm adı olarak alınıyor.
- Son maddeden sonra gelen `EK-1`, `Açıklama`, `YÜRÜRLÜĞE GİRİŞ` gibi kısımlar maddeye
  karışmasın diye ayrı `ek` / `kunye` parçası oluyor.
- Tablolar `a | b | c` satırları olarak yazılıyor. Hücre metni kelime konumlarından toplanıyor
  (PyMuPDF'in `extract()`i bazı fontlarda boşlukları yutuyordu).
- Satırlarındaki sayılar iç içe geçmiş tablolar güvenilmez sayılıp yerine "sayfaya bakın" notu
  yazılıyor. Görüntü olarak eklenmiş tablolar da (not karşılıkları s. 2-5) aynı şekilde işaretli.
- Ek Sınav Esasları taranmış PDF. `tesseract` (tur) ile okundu, bariz hatalar ve 4. sayfadaki
  not dönüşüm tablosu görüntüye bakılarak elle düzeltildi: `kaynaklar/ek_sinav_esaslari.ocr.txt`.
- Her sayfada tekrar eden üst/alt bilgiler ve `Sayfa x/y` satırları atılıyor.

## Hız

Tablo bulma yavaş olduğu için okunan satırlar PDF'in sha256'sı ile `cikti/onbellek/` altında
saklanıyor. İlk çalıştırma ~19 sn, sonrakiler ~0,3 sn. PDF değişirse otomatik yeniden okunuyor.

## Kontroller (`pytest`, 56 test, hepsi geçti)

- Madde numaraları her belgede eksiksiz ve sıralı (yönetmelikte 20/A dahil).
- Hiçbir parçada satır başında `MADDE n` kalmamış, yani bölme kaçmamış.
- Her madde/bentin ilk cümlesi, kayıtlı başlangıç sayfasında gerçekten geçiyor.
  Örnek: Madde 10 → s. 3, Madde 20/A → s. 7, Madde 25 → s. 9.
- Bilinen cevaplar doğru parçada: 45/60 AKTS (md. 10), yaz okulu 20 AKTS (md. 20/A),
  240 AKTS (md. 25), İstatistik için 20 iş günü staj, ek sınav dönüşüm tablosu.
- Türkçe karakter: bozuk kodlama (`Ã`, `Ä±`, `�`, birleşik nokta) yok, metinler NFC,
  her belgede ğ ü ş ı ö ç İ var.
- Metin kaybı: PDF'teki karakterlerin %96'dan fazlası parçalarda. Eksik kalanlar madde
  numaraları ve büyük harfli belge başlığı.
- Temiz bir sanal ortamda (sadece `requirements.txt`) çıktı bayt bayt aynı.
