# ESTÜ Dijital Danışman

ESTÜ öğrencilerinin "Kaç AKTS üst sınırım var?", "Tek ders sınavına kimler girebilir?",
"Kaç iş günü staj yapmam lazım?" gibi sorularına **resmi belgelerden**, belge adı, madde
numarası ve sayfasıyla cevap veren bir arama asistanı.

Cevap olarak metin üretmiyor; soruya en uygun maddeyi bulup ilgili fıkrasını olduğu gibi
gösteriyor. Belgelerde cevap yoksa "bulamadım" diyor. Hiçbir ücretli API ya da servis kullanmıyor.

"Mezun olmak için neyim eksik?" sorusu için ayrı bir **mezuniyet kontrolü** sekmesi var:
tamamlanan AKTS, GNO, kalan FF/YZ/DZ/EK/ÇK notları ve staj gününü girince yönetmeliğin
25. maddesine ve staj yönergesinin 7. maddesine göre neyin eksik olduğunu, maddesiyle birlikte gösteriyor.

![Ekran görüntüsü](docs/ekran.png)

## Kaynak belgeler

Hepsi 19.11.2026'da resmi sitelerden indirildi (`kaynaklar/`, ayrıntılar `belgeler.yaml`).

| Belge | Yürürlük | Son değişiklik |
|---|---|---|
| Ön Lisans ve Lisans Eğitim-Öğretim ve Sınav Yönetmeliği (RG 33012) | 22.09.2025 | 08.02.2026 (RG 33162) |
| Fen Fakültesi Staj Yönergesi | 05.10.2018 | 08.11.2022 |
| Akademik Danışmanlık Yönergesi | 11.09.2025 | |
| Haklı ve Geçerli Nedenlere İlişkin Usul ve Esaslar | 11.09.2025 | |
| Tek Ders Sınavı Uygulama Esasları | 18.12.2025 | |
| Ek Sınav Esasları (azami süre sonu) | 23.11.2018 | 05.10.2021 |
| Yaz Okulu Uygulama Esasları | 11.09.2025 | 10.03.2026 |
| Not Karşılıkları ve Yabancı Dil Eşdeğerlikleri Uygulama Esasları | 10.07.2018 | 29.07.2025 |
| Proje Temelli Staj Yönergesi | 04.01.2024 | 26.06.2025 |
| İstatistik Bölümü ders planı ve program bilgileri (Bologna sayfaları) | web sayfası | |

Not: Yönetmelik 2025'te tamamen yenilendi. İnternette hâlâ 2018 tarihli eski metin (RG 30540)
dolaşıyor; buradaki metin mevzuat.gov.tr'deki güncel, değişiklikleri işlenmiş hali.

## Nasıl çalışıyor

```
kaynaklar/*.pdf, *.html
   │  ayristir.py   madde madde parçalama (MADDE 10-, 1), 1- ...), sayfa ve başlık bilgisi
   ▼
cikti/parcalar.jsonl  (190 parça)
   │  indeks.py     e5-small (ONNX, int8) ile vektörler + FAISS, BM25 için Türkçe kök
   ▼
indeks/
   │  arama.py      BM25 ve e5 sıralamaları Reciprocal Rank Fusion ile birleşiyor
   │  cevap.py      en uygun 3 parçadan ilgili fıkralar + atıf + "bulamadım" eşiği
   ▼
app.py (Streamlit)
```

Birkaç ayrıntı:

- **Madde bazlı parçalama.** Sabit uzunlukta bölmek yerine her madde (ya da usul ve esaslardaki
  numaralı bent) ayrı parça. Böylece cevapta "Madde 10, s. 3" diye kaynak gösterilebiliyor.
- **Tablolar** `a | b | c` satırları olarak tutuluyor. Görüntü olarak eklenmiş tablolar okunamadığı
  için "bu sayfaya bakın" diye işaretli.
- **Taranmış PDF.** Ek Sınav Esasları'nın metin katmanı yok, `tesseract` ile okundu ve not dönüşüm
  tablosu görüntüye bakılarak elle düzeltildi (`kaynaklar/ek_sinav_esaslari.ocr.txt`).
- **Model.** [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small)
  modelinin int8 ONNX hali (~118 MB). CPU'da çalışıyor, ilk açılışta Hugging Face'ten ücretsiz iniyor.
  Tokenizer, Hugging Face `tokenizer.json`'ın SentencePiece'e çevrilmiş hali (`indeks/tokenizer.model`,
  `tokenizer_donustur.py`): aynı token id'lerini veriyor ama bellekte ~300 MB yerine ~70 MB tutuyor.
  Uygulamanın toplam belleği ~290 MB, bir soru ~0,01 sn.
- **"Bulamadım".** En iyi parçanın benzerliği 0.850'nin üstündeyse cevap gösteriliyor, 0.825'in
  altındaysa "bulamadım" deniyor, arada kalırsa "kesin cevap bulamadım, ilgili olabilecek maddeler" deniyor.

## Sonuçlar

Test setleri `tests/` altında, her sorunun cevabı belgelerden kontrol edildi.

**Arama** (doğru kaynak ilk k sonuçta mı):

| Set | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| Ana set (27 cevaplı soru) | 0.63 | 0.96 | 0.96 | 0.79 |
| Ayrık set (10 cevaplı, ayarlamada kullanılmadı) | 0.80 | 1.00 | 1.00 | 0.90 |

Hibrit arama iki sette de sadece BM25'ten ve sadece e5'ten daha iyi.

**Cevap** (cevaplı soruda beklenen ifade gösterilen alıntıda geçiyor mu, cevapsız soruda
asistan cevap bulduğunu iddia etmiyor mu):

| Set | Cevaplı | Cevapsız |
|---|---|---|
| Ana set | 26/27 | 3/3 |
| Kalibrasyon (sadece cevapsız) | | 15/15 |
| Ayrık set | 10/10 | 2/2 |
| Doğrulama (eşikten sonra yazıldı) | 7/8 | 6/8 |

Ayrıntılar ve hatalı sorular: [raporlar/4_arama.md](raporlar/4_arama.md),
[raporlar/5_cevap.md](raporlar/5_cevap.md). Parçalama kontrolleri:
[raporlar/2_ayristirma.md](raporlar/2_ayristirma.md).

## Kurulum

Python 3.12 ya da 3.13 (sabitlenen numpy sürümü 3.12+ istiyor).

```bash
git clone https://github.com/beratciftci4/ESTU-Dijital-Danisman.git
cd ESTU-Dijital-Danisman
pip install -r requirements.txt
streamlit run app.py
```

İndeks repoda hazır geliyor, model ilk çalıştırmada `model/` klasörüne iniyor.

Belgeler değişirse:

```bash
python belge_kontrol.py   # belge listesi, tarihler ve sha256 kontrolü
python ayristir.py        # parçaları yeniden üret
python indeks.py          # indeksi yeniden kur
python degerlendir.py     # test setleriyle ölç, raporlar/ güncellenir
pytest                    # 97 test
```

## Ücretsiz yayınlama (Streamlit Community Cloud)

1. https://share.streamlit.io adresine GitHub hesabıyla gir.
2. **Create app** → bu repo, `main` dalı, dosya `app.py`.
3. **Advanced settings** → Python sürümü olarak 3.12 ya da 3.13 seç.
4. **Deploy**. Kart bilgisi istemiyor; ücretsiz planda çalışıyor.

API anahtarı ya da gizli bilgi gerekmiyor.

## Sınırlar

- Bu bir arama aracı, **resmi görüş değil**. Kesin bilgi için Öğrenci İşleri'ne ya da akademik
  danışmana sorun.
- Sadece yukarıdaki belgeleri biliyor. Akademik takvim, burs, yurt, Erasmus gibi konular yok.
- Benzerlik eşiği tek başına mükemmel değil: belgelerdeki kelimelere yakın ama kapsam dışı
  bir soru (örneğin "mezunlar derneği") bazen eşiği geçebiliyor. Bu durumda bile gösterilen
  metin resmi metnin aynısı, kaynak ve sayfası yazılı.
- Bologna sayfalarının yürürlük tarihi yok, erişim tarihi esas alınıyor.

## Dosyalar

| Dosya | Ne yapıyor |
|---|---|
| `belgeler.yaml` | Belge listesi: URL, yürürlük, son değişiklik, sha256 |
| `belge_kontrol.py` | Belge listesini ve dosyaları kontrol eder |
| `ayristir.py` | Belgeleri madde/bent parçalarına ayırır |
| `indeks.py` | Embedding modeli, BM25 kelime ayırma, FAISS indeksi |
| `tokenizer_donustur.py` | tokenizer.json'ı küçük SentencePiece modeline çevirir |
| `arama.py` | Hibrit arama |
| `cevap.py` | Atıflı cevap ve "bulamadım" kararı |
| `mezuniyet.py` | Mezuniyet koşulları kontrolü |
| `degerlendir.py` | Test setleriyle ölçüm, `raporlar/` |
| `app.py` | Streamlit arayüzü |
| `tests/` | Testler ve soru setleri |
