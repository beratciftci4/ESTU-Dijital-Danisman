"""4. aşama testleri: hibrit arama ve test setleri üzerindeki başarı."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from arama import Arayici
from degerlendir import AYRIK_SET, arama_olc, sorulari_oku
from indeks import parcalari_oku, soru_kelimeleri


@pytest.fixture(scope="module")
def arayici():
    return Arayici()


def test_soru_kaliplari_atiliyor():
    k = soru_kelimeleri("Kaç AKTS üst sınırım var?")
    assert "kaç" not in k and "var" not in k
    assert "akts" in k


def test_esanlamlilar_ekleniyor():
    assert "çok" in soru_kelimeleri("En fazla kaç ders alabilirim?")
    assert "saklı" in soru_kelimeleri("Kaydımı dondurabilir miyim?")
    # bütünleme bilerek ek sınava eşlenmiyor
    assert "ek" not in soru_kelimeleri("Bütünleme sınavı var mı?")


def test_test_setleri_gecerli():
    """Her sorunun kaynağı gerçekten var ve anahtar ifade o kaynakta geçiyor."""
    parcalar = {p["id"]: p for p in parcalari_oku()}
    for yol in [None, AYRIK_SET]:
        sorular = sorulari_oku() if yol is None else sorulari_oku(yol)
        for s in sorular:
            if s.get("cevapsiz"):
                continue
            assert all(k in parcalar for k in s["kaynak"]), s["soru"]
            assert any(a in parcalar[k]["metin"] for k in s["kaynak"] for a in s["anahtar"]), s["soru"]
    assert len(sorulari_oku()) == 30


def test_sonuclar_tekil_ve_sirali(arayici):
    sonuc = arayici.ara("Mazeret sınavı", k=10)
    idler = [p["id"] for p, _ in sonuc]
    assert len(idler) == len(set(idler)) == 10


def test_ayni_soru_ayni_sonuc(arayici):
    a = [p["id"] for p, _ in arayici.ara("Tek ders sınavına kimler girebilir?")]
    b = [p["id"] for p, _ in arayici.ara("Tek ders sınavına kimler girebilir?")]
    assert a == b


def test_ana_set_basarisi(arayici):
    olcu, _ = arama_olc(arayici, sorulari_oku(), "hibrit")
    assert olcu["hit@3"] >= 0.90
    assert olcu["hit@5"] >= 0.95


def test_ayrik_set_basarisi(arayici):
    olcu, _ = arama_olc(arayici, sorulari_oku(AYRIK_SET), "hibrit")
    assert olcu["hit@3"] >= 0.90


def test_hibrit_tek_yontemlerden_iyi(arayici):
    sorular = sorulari_oku() + sorulari_oku(AYRIK_SET)
    hibrit = arama_olc(arayici, sorular, "hibrit")[0]["MRR"]
    assert hibrit >= arama_olc(arayici, sorular, "bm25")[0]["MRR"]
    assert hibrit >= arama_olc(arayici, sorular, "e5")[0]["MRR"]
