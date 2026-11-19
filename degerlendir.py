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


if __name__ == "__main__":
    sys.exit(main())
