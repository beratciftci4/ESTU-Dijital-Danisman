# 4. Aşama: Arama sonuçları

Hibrit = BM25 ve e5 sıralamalarının Reciprocal Rank Fusion ile eşit ağırlıkla birleşimi.

## Ana test seti (tests/soru_seti.yaml)

30 soru (27 cevaplı, 3 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.52 | 0.93 | 0.96 | 0.70 |
| e5 | 0.59 | 0.85 | 0.93 | 0.75 |
| hibrit | 0.74 | 0.96 | 0.96 | 0.85 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Kaydımı en fazla kaç dönem dondurabilirim? (sıra: 6; ilk 3: hakli_nedenler#bent-3, danismanlik#madde-10, yonetmelik#madde-10)

## Ayrık test seti (tests/soru_seti_ayrik.yaml)

12 soru (10 cevaplı, 2 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.70 | 1.00 | 1.00 | 0.83 |
| e5 | 0.60 | 0.80 | 0.80 | 0.73 |
| hibrit | 0.90 | 1.00 | 1.00 | 0.95 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Yok.

## Doğrulama seti (tests/soru_seti_dogrulama.yaml)

16 soru (8 cevaplı, 8 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.62 | 0.88 | 0.88 | 0.76 |
| e5 | 0.88 | 0.88 | 1.00 | 0.91 |
| hibrit | 0.88 | 1.00 | 1.00 | 0.92 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Yok.

## Fen Fakültesi diğer bölümler (tests/soru_seti_fen.yaml, Biyoloji/Fizik/Kimya/Matematik)

18 soru (16 cevaplı, 2 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.56 | 0.75 | 0.81 | 0.68 |
| e5 | 0.38 | 0.75 | 0.81 | 0.55 |
| hibrit | 0.69 | 0.81 | 0.88 | 0.78 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Kimya bölümünde staj zorunlu mu? (sıra: 5; ilk 3: fen_staj#madde-11, fen_staj#madde-7, kimya_ders_plani#bolum-V.YARIYIL)
- Biyoloji bölümünde hazırlık okumak zorunlu mu? (sıra: 8; ilk 3: biyoloji_program_bilgileri#bolum-İstihdam_Olanakları, biyoloji_program_bilgileri#bolum-Program_Profili, biyoloji_ders_plani#bolum-I.YARIYIL)
- Matematik bölümünde kaç AKTS ile mezun olunur? (sıra: 9; ilk 3: matematik_ders_plani#bolum-II.YARIYIL, matematik_ders_plani#bolum-I.YARIYIL, matematik_ders_plani#bolum-VI.YARIYIL)

## Mühendislik Fakültesi (tests/soru_seti_muhendislik.yaml, 9 bölüm)

20 soru (18 cevaplı, 2 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.33 | 0.72 | 0.89 | 0.54 |
| e5 | 0.50 | 0.67 | 0.72 | 0.62 |
| hibrit | 0.61 | 0.78 | 0.89 | 0.73 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Elektrik elektronik mühendisliğinde kaç tane staj var? (sıra: 20+; ilk 3: muh_staj#madde-10, muh_staj#madde-3, elektrik_elektronik_muh_program_bilgileri#bolum-Program_Profili)
- Bilgisayar mühendisliğinde kaç AKTS mesleki seçmeli almalıyım? (sıra: 5; ilk 3: bilgisayar_muh_ders_plani#bolum-VI.YARIYIL, bilgisayar_muh_ders_plani#bolum-VIII.YARIYIL, bilgisayar_muh_ders_plani#bolum-VII.YARIYIL)
- Çevre mühendisliğinde sosyal seçmeli kaç kredi? (sıra: 4; ilk 3: cevre_muh_ders_plani#bolum-VII.YARIYIL, cevre_muh_ders_plani#bolum-VIII.YARIYIL, cevre_muh_ders_plani#bolum-Mesleki_Seçmeli_Dersler)
- Uçak mühendisliğinde kaç AKTS ile mezun olunur? (sıra: 9; ilk 3: ucak_muh_ders_plani#bolum-VII.YARIYIL, ucak_muh_ders_plani#bolum-VIII.YARIYIL, ucak_muh_program_bilgileri#bolum-İstihdam_Olanakları)

## Bilgisayar ve Bilişim Bilimleri Fakültesi (tests/soru_seti_bbbf.yaml, 3 bölüm)

17 soru (15 cevaplı, 2 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.47 | 0.73 | 0.93 | 0.62 |
| e5 | 0.47 | 0.80 | 1.00 | 0.67 |
| hibrit | 0.73 | 1.00 | 1.00 | 0.86 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Yok.

## Havacılık ve Uzay Bilimleri Fakültesi (tests/soru_seti_hubf.yaml, 5 bölüm)

20 soru (18 cevaplı, 2 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.39 | 0.72 | 0.83 | 0.57 |
| e5 | 0.61 | 0.89 | 0.89 | 0.75 |
| hibrit | 0.83 | 0.94 | 0.94 | 0.89 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Staj yapmak zorunlu mu? (sıra: 20+; ilk 3: hubf_staj#madde-9, proje_temelli_staj#madde-18, proje_temelli_staj#madde-10)

## Notlar

- Eş anlamlı listesi ("üst sınır" -> "en çok" gibi) ve soru kalıbı listesi ana test setindeki hatalara bakılarak eklendi. Bu yüzden ayrık sette ayrıca ölçüldü.
- e5'e daha fazla ağırlık vermek ana sette biraz daha iyi sonuç verdi ama ayrık sette kötüleştirdi (aşırı uyum). Eşit ağırlıkta kalındı.
- BM25 için kök bulma denendi (hibrit, hit@3 / MRR, ana-ayrık-doğrulama): ilk 4 harf .93/.81, 1.00/.90, 1.00/.88; ilk 5 harf .96/.79, 1.00/.90, .88/.83; Snowball Türkçe .93/.83, 1.00/.95, .88/.77; Snowball + ilk 5 harf .96/.81, 1.00/.95, 1.00/.81. Farklar 45 soruda 1-2 soru, tutarlı bir kazanan yok. Ek paket gerektirmeyen ilk 5 harf yönteminde kalındı.
- Bölüm seçimi (2026-11-25): arama sadece genel belgeler + bölümün fakültesinin staj yönergesi + bölümün Bologna sayfalarında yapılıyor. İlk setler İstatistik seçiliyken ölçülüyor; İstatistik'in parçaları eskisiyle aynı olduğu için sonuçlar karşılaştırılabilir.
- Bölümün kendi Bologna sayfalarının arama metninden bölüm adı çıkarıldı. Yoksa "Kimya bölümünde staj zorunlu mu?" gibi sorularda o bölümün ders planı öne çıkıyordu. Adı sorudan çıkarmak da denendi, daha kötü oldu (Fen seti hit@3 .62): staj yönergesindeki "Kimya ve Matematik için staj isteğe bağlı" notu tam da bölüm adıyla bulunuyor.
- RRF'ye üçüncü sıralama olarak elle yazılmış özet cümleleriyle e5 benzerliği eklendi (özetler öğrencinin kullandığı kelimelerle yazıldı). MRR: ana .79 -> .85, doğrulama .83 -> .92, Fen seti .66 -> .78. "Bulundu/bulamadım" eşiği değişmedi, hâlâ madde metninin benzerliğine bakıyor.
- Staj kuralı bölüme göre değişiyor (Fen'de Kimya ve Matematik isteğe bağlı) ama yönergenin maddesi genel ("en az 20 iş günü"). Kimya seçiliyken "Staj zorunlu mu?" sorusuna "20 gün zorundasın" deniyordu. Her bölüme kendi staj cümlesi eklendi (programlar.yaml'dan, yönergenin EK-3 notuna bağlı), sadece o bölüm seçiliyken kullanılıyor.
- Mühendislik (2026-11-25): yönerge md. 8 "toplam staj en az 40 gün". Bölümün Bologna sayfası daha ayrıntılıysa o kullanıldı (Endüstri: Staj I 20 + Staj II 25 iş günü; Elektrik-Elektronik: 2 x 20 iş günü). Uçak Mühendisliği yönergenin bölüm listesinde geçmiyor, kısa cevapta belirtiliyor.
- Bologna "program hakkında" sayfalarında İstatistik'tekiyle kelimesi kelimesine aynı olan bölümlerin (kabul, üst derece, ölçme ...) özetleri şablondan üretiliyor, farklı olanlar elle yazıldı.
- Bilinen hata: "Elektrik elektronik mühendisliğinde kaç tane staj var?" sorusunda doğru madde özet sıralamasında 1., ama BM25 "staj" ile "stajın" kelimelerini farklı köke ayırıyor (ilk 5 harf). Özet sıralamasına 1,5 ve 2 ağırlık denendi, toplam MRR değişmedi (.827/.832/.825), eşit ağırlıkta kalındı.
- Bölümün staj cümlesi, bağlı olduğu madde aramada ilk 5'e girmese de kısa cevaba aday (Endüstri'nin süresi Bologna sayfasında). Benzerlikle seçince "kaç gün staj" sorusunda "haftada 3 tam gün dersin yoksa" ya da proje temelli staj (45-90 gün) cümleleri öne çıkıyordu. Soru stajın süresini/zorunluluğunu soruyorsa (staj_suresi_soruluyor, kurala dayalı) bölümün staj cümlesi doğrudan ilk sıraya konuyor; itiraz, başvuru, PTS gibi staj soruları bu kurala girmiyor.
- Bilgisayar ve Bilişim Bilimleri (2026-11-26): yönerge md. 8 "her biri en az 20 iş günü, ders planındaki sayıda staj"; üç programda da iki staj dersi var (kodlarında SJ), toplam 40 iş günü. Cevabı olmayan iki sorunun ikisine de "bulundu" deniyor; bölüm sayısı arttıkça eşik zayıflıyor.
- Ders planı sorularında "birinci dönem" ile "I.YARIYIL" eşleşmesi için yarıyıl numarası arama metnine ve eş anlamlılara eklendi.
- "Bütünleme" sorusu bilerek cevapsız: yeni yönetmelikte bütünleme sınavı yok. "bütünleme" kelimesi "ek sınav"a eşlenmedi, çünkü ikisi aynı şey değil.
