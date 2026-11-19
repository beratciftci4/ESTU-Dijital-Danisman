# 4. Aşama: Arama sonuçları

Hibrit = BM25 ve e5 sıralamalarının Reciprocal Rank Fusion ile eşit ağırlıkla birleşimi.

## Ana test seti (tests/soru_seti.yaml)

30 soru (27 cevaplı, 3 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.48 | 0.89 | 0.96 | 0.68 |
| e5 | 0.59 | 0.89 | 0.93 | 0.74 |
| hibrit | 0.59 | 0.93 | 0.96 | 0.76 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Ek sınavda 77-83 arası alan öğrencinin harf notu ne olur? (sıra: 4; ilk 3: yonetmelik#madde-18, program_bilgileri#bolum-Ölçme_ve_Değerlendirme, tek_ders#bent-4)
- Kaydımı en fazla kaç dönem dondurabilirim? (sıra: 12; ilk 3: hakli_nedenler#bent-3, danismanlik#madde-10, yonetmelik#madde-10)

## Ayrık test seti (tests/soru_seti_ayrik.yaml)

12 soru (10 cevaplı, 2 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.60 | 1.00 | 1.00 | 0.77 |
| e5 | 0.60 | 0.80 | 0.80 | 0.73 |
| hibrit | 0.70 | 1.00 | 1.00 | 0.85 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Yok.

## Notlar

- Eş anlamlı listesi ("üst sınır" -> "en çok" gibi) ve soru kalıbı listesi ana test setindeki hatalara bakılarak eklendi. Bu yüzden ayrık sette ayrıca ölçüldü.
- e5'e daha fazla ağırlık vermek ana sette biraz daha iyi sonuç verdi ama ayrık sette kötüleştirdi (aşırı uyum). Eşit ağırlıkta kalındı.
- "Bütünleme" sorusu bilerek cevapsız: yeni yönetmelikte bütünleme sınavı yok. "bütünleme" kelimesi "ek sınav"a eşlenmedi, çünkü ikisi aynı şey değil.
