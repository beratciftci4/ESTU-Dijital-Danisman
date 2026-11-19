# 4. Aşama: Arama sonuçları

Hibrit = BM25 ve e5 sıralamalarının Reciprocal Rank Fusion ile eşit ağırlıkla birleşimi.

## Ana test seti (tests/soru_seti.yaml)

30 soru (27 cevaplı, 3 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.52 | 0.93 | 0.96 | 0.70 |
| e5 | 0.59 | 0.89 | 0.93 | 0.74 |
| hibrit | 0.63 | 0.96 | 0.96 | 0.79 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Kaydımı en fazla kaç dönem dondurabilirim? (sıra: 12; ilk 3: hakli_nedenler#bent-3, danismanlik#madde-10, yonetmelik#madde-10)

## Ayrık test seti (tests/soru_seti_ayrik.yaml)

12 soru (10 cevaplı, 2 cevapsız). Ölçüler cevaplı sorular üzerinden.

| Yöntem | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.60 | 1.00 | 1.00 | 0.77 |
| e5 | 0.60 | 0.80 | 0.80 | 0.73 |
| hibrit | 0.80 | 1.00 | 1.00 | 0.90 |

Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:

- Yok.

## Notlar

- Eş anlamlı listesi ("üst sınır" -> "en çok" gibi) ve soru kalıbı listesi ana test setindeki hatalara bakılarak eklendi. Bu yüzden ayrık sette ayrıca ölçüldü.
- e5'e daha fazla ağırlık vermek ana sette biraz daha iyi sonuç verdi ama ayrık sette kötüleştirdi (aşırı uyum). Eşit ağırlıkta kalındı.
- BM25 için kök bulma denendi (hibrit, hit@3 / MRR, ana-ayrık-doğrulama): ilk 4 harf .93/.81, 1.00/.90, 1.00/.88; ilk 5 harf .96/.79, 1.00/.90, .88/.83; Snowball Türkçe .93/.83, 1.00/.95, .88/.77; Snowball + ilk 5 harf .96/.81, 1.00/.95, 1.00/.81. Farklar 45 soruda 1-2 soru, tutarlı bir kazanan yok. Ek paket gerektirmeyen ilk 5 harf yönteminde kalındı.
- "Bütünleme" sorusu bilerek cevapsız: yeni yönetmelikte bütünleme sınavı yok. "bütünleme" kelimesi "ek sınav"a eşlenmedi, çünkü ikisi aynı şey değil.
