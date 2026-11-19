"""
Test setiyle aramayı ölçer, raporlar/4_arama.md dosyasını yazar.

    python degerlendir.py

hit@k : doğru kaynak ilk k sonuçta var mı (cevabı olan sorular üzerinden oran)
MRR   : doğru kaynağın sırasının tersinin ortalaması (1. sırada = 1, 2. = 0.5 ...)
"""
import sys
from pathlib import Path

import yaml

from arama import Arayici

KLASOR = Path(__file__).parent
SORU_SETI = KLASOR / "tests" / "soru_seti.yaml"
AYRIK_SET = KLASOR / "tests" / "soru_seti_ayrik.yaml"
DOGRULAMA_SET = KLASOR / "tests" / "soru_seti_dogrulama.yaml"
KALIBRASYON = KLASOR / "tests" / "kalibrasyon_cevapsiz.yaml"


def sorulari_oku(yol=SORU_SETI):
    return yaml.safe_load(yol.read_text(encoding="utf-8"))


def arama_olc(arayici, sorular, yontem, k_lar=(1, 3, 5)):
    cevapli = [s for s in sorular if not s.get("cevapsiz")]
    hit = {k: 0 for k in k_lar}
    mrr = 0.0
    kacan = []
    for s in cevapli:
        idler = [p["id"] for p, _ in arayici.ara(s["soru"], k=20, yontem=yontem)]
        sira = next((i + 1 for i, x in enumerate(idler) if x in s["kaynak"]), None)
        for k in k_lar:
            hit[k] += bool(sira and sira <= k)
        mrr += 1 / sira if sira else 0
        if not sira or sira > 3:
            kacan.append((s["soru"], sira, idler[:3]))
    n = len(cevapli)
    return {f"hit@{k}": hit[k] / n for k in k_lar} | {"MRR": mrr / n}, kacan


def cevap_olc(arayici, sorular):
    """Cevap doğruluğu.
    Cevaplı soru doğru: asistan "bulamadım" demedi VE beklenen ifade gösterilen alıntılarda geçiyor.
    Cevapsız soru doğru: asistan "bulundu" demedi (bulamadım ya da "kesin cevap yok" dedi)."""
    from cevap import cevapla
    sonuc = {"cevapli": 0, "cevapli_dogru": 0, "cevapsiz": 0, "cevapsiz_dogru": 0,
             "cevapsiz_tam_red": 0, "durumlar": [], "hatalar": []}
    for s in sorular:
        c = cevapla(s["soru"], arayici)
        alinti = " ".join(" ".join(k["alinti"]) for k in c["kaynaklar"])
        if s.get("cevapsiz"):
            sonuc["cevapsiz"] += 1
            dogru = c["durum"] != "bulundu"
            sonuc["cevapsiz_dogru"] += dogru
            sonuc["cevapsiz_tam_red"] += c["durum"] == "bulunamadi"
        else:
            sonuc["cevapli"] += 1
            dogru = c["durum"] != "bulunamadi" and any(a in alinti for a in s["anahtar"])
            sonuc["cevapli_dogru"] += dogru
        sonuc["durumlar"].append(c["durum"])
        if not dogru:
            sonuc["hatalar"].append((s["soru"], c["durum"], c["en_iyi_benzerlik"]))
    return sonuc


def cevap_tablosu(arayici, setler):
    satirlar = ["# 5. Aşama: Cevap doğruluğu (API'siz)", "",
                "Cevap = en uygun 3 parçadan seçilen 1-2 fıkra/cümle + belge, madde, sayfa, yürürlük tarihi.",
                "Metin üretilmiyor, gösterilen her şey resmi metnin aynısı.", "",
                "- Cevaplı soru doğru: asistan \"bulamadım\" demedi ve beklenen ifade gösterilen alıntıda geçiyor.",
                "- Cevapsız soru doğru: asistan cevabı bulduğunu iddia etmedi (\"bulamadım\" ya da "
                "\"kesin cevap bulamadım, ilgili olabilecek maddeler\").", "",
                f"Eşikler: e5 benzerliği >= {__import__('cevap').ESIK_YUKSEK} ise \"bulundu\", "
                f"< {__import__('cevap').ESIK_DUSUK} ise \"bulamadım\", arası \"belirsiz\".", "",
                "| Set | Cevaplı doğru | Cevapsız doğru | Cevapsızda doğrudan \"bulamadım\" |",
                "|---|---|---|---|"]
    hatalar = []
    for ad, sorular in setler:
        o = cevap_olc(arayici, sorular)
        cvp = f"{o['cevapli_dogru']}/{o['cevapli']}" if o["cevapli"] else "-"
        cvs = f"{o['cevapsiz_dogru']}/{o['cevapsiz']}" if o["cevapsiz"] else "-"
        red = f"{o['cevapsiz_tam_red']}/{o['cevapsiz']}" if o["cevapsiz"] else "-"
        satirlar.append(f"| {ad} | {cvp} | {cvs} | {red} |")
        print("cevap", ad, cvp, cvs, red)
        hatalar += [(ad, *h) for h in o["hatalar"]]
    satirlar += ["", "## Hatalı sonuçlar", ""]
    satirlar += [f"- [{ad}] {soru} -> {durum} (benzerlik {b})" for ad, soru, durum, b in hatalar] or ["- Yok."]
    return satirlar


def tablo(arayici, sorular, baslik):
    satirlar = [f"## {baslik}", "",
                f"{len(sorular)} soru ({sum(not s.get('cevapsiz') for s in sorular)} cevaplı, "
                f"{sum(bool(s.get('cevapsiz')) for s in sorular)} cevapsız). "
                "Ölçüler cevaplı sorular üzerinden.", "",
                "| Yöntem | hit@1 | hit@3 | hit@5 | MRR |", "|---|---|---|---|---|"]
    kacanlar = []
    for yontem in ["bm25", "e5", "hibrit"]:
        olcu, kacan = arama_olc(arayici, sorular, yontem)
        if yontem == "hibrit":
            kacanlar = kacan
        satirlar.append(f"| {yontem} | " + " | ".join(f"{v:.2f}" for v in olcu.values()) + " |")
        print(baslik[:12], yontem, {k: round(v, 3) for k, v in olcu.items()})
    satirlar += ["", "Hibrit aramada doğru kaynağı ilk 3'e giremeyen sorular:", ""]
    satirlar += [f"- {soru} (sıra: {sira or '20+'}; ilk 3: {', '.join(ilk3)})"
                 for soru, sira, ilk3 in kacanlar] or ["- Yok."]
    return satirlar + [""]


def main():
    arayici = Arayici()
    satirlar = ["# 4. Aşama: Arama sonuçları", "",
                "Hibrit = BM25 ve e5 sıralamalarının Reciprocal Rank Fusion ile eşit ağırlıkla birleşimi.", ""]
    satirlar += tablo(arayici, sorulari_oku(), "Ana test seti (tests/soru_seti.yaml)")
    satirlar += tablo(arayici, sorulari_oku(AYRIK_SET), "Ayrık test seti (tests/soru_seti_ayrik.yaml)")
    satirlar += ["## Notlar", "",
                 "- Eş anlamlı listesi (\"üst sınır\" -> \"en çok\" gibi) ve soru kalıbı listesi ana test "
                 "setindeki hatalara bakılarak eklendi. Bu yüzden ayrık sette ayrıca ölçüldü.",
                 "- e5'e daha fazla ağırlık vermek ana sette biraz daha iyi sonuç verdi ama ayrık sette "
                 "kötüleştirdi (aşırı uyum). Eşit ağırlıkta kalındı.",
                 "- \"Bütünleme\" sorusu bilerek cevapsız: yeni yönetmelikte bütünleme sınavı yok. "
                 "\"bütünleme\" kelimesi \"ek sınav\"a eşlenmedi, çünkü ikisi aynı şey değil."]
    (KLASOR / "raporlar" / "4_arama.md").write_text("\n".join(satirlar) + "\n", encoding="utf-8")

    kalibrasyon = [{"soru": q, "cevapsiz": True} for q in sorulari_oku(KALIBRASYON)]
    setler = [("Ana set (eşik ayarında kullanıldı)", sorulari_oku()),
              ("Kalibrasyon, cevapsız (eşik ayarında kullanıldı)", kalibrasyon),
              ("Ayrık set", sorulari_oku(AYRIK_SET)),
              ("Doğrulama seti (eşikten sonra yazıldı)", sorulari_oku(DOGRULAMA_SET))]
    satirlar = cevap_tablosu(arayici, setler)
    satirlar += ["", "## Notlar", "",
                 "- Eşikler ana set + kalibrasyon sorularına bakılarak seçildi, doğrulama seti ondan sonra "
                 "yazıldı. Doğrulama sonucuna göre eşik değiştirilmedi, yoksa o set de bağımsız olmazdı.",
                 "- Cevapsız bir soruya \"bulundu\" denmesi en riskli hata. Bu durumda bile asistan metin "
                 "uydurmuyor, sadece alakasız bir maddeyi gösteriyor; kaynak ve sayfa her zaman yazılı.",
                 "- Benzerlik eşiği tek başına sınırlı: \"Mezunlar derneği\" gibi yönetmelikteki kelimelere "
                 "yakın sorular eşiği geçebiliyor. Kelime kapsamı gibi ek sinyaller denendi, net ayırmadı."]
    (KLASOR / "raporlar" / "5_cevap.md").write_text("\n".join(satirlar) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
