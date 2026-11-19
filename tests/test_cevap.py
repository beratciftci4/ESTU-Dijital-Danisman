"""5. aşama testleri: API'siz cevap, atıf biçimi ve "bulamadım" davranışı."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from arama import Arayici
from cevap import atif, birimlere_bol, cevapla, gecerlilik
from degerlendir import AYRIK_SET, DOGRULAMA_SET, KALIBRASYON, cevap_olc, sorulari_oku


@pytest.fixture(scope="module")
def arayici():
    return Arayici()


def parca(arayici, pid):
    return next(p for p in arayici.parcalar if p["id"] == pid)


def test_atif_bicimi(arayici):
    assert atif(parca(arayici, "yonetmelik#madde-10")) == \
        "Ön Lisans ve Lisans Eğitim-Öğretim ve Sınav Yönetmeliği, Madde 10 (Kayıt yenileme ve ders kaydı), s. 3"
    assert atif(parca(arayici, "yonetmelik#madde-20/A")).endswith("Madde 20/A (Yaz okulu), s. 7-8")
    assert atif(parca(arayici, "tek_ders#bent-5")) == "Tek Ders Sınavı Uygulama Esasları, 5. madde, s. 1"
    assert atif(parca(arayici, "program_bilgileri#bolum-Mezuniyet_Koşulları")) == \
        "İstatistik Bölümü Program Bilgileri (Bologna), Mezuniyet Koşulları"


def test_gecerlilik_bilgisi(arayici):
    assert gecerlilik(parca(arayici, "yonetmelik#madde-10")) == \
        "Yürürlük: 22.09.2025, son değişiklik: 08.02.2026"
    assert "erişim" in gecerlilik(parca(arayici, "ders_plani#bolum-III.YARIYIL"))


def test_cevap_sadece_resmi_metin(arayici):
    """Gösterilen her alıntı, kaynağın tam metninde aynen geçmeli (uydurma yok)."""
    sorular = sorulari_oku() + sorulari_oku(AYRIK_SET) + sorulari_oku(DOGRULAMA_SET)
    for s in sorular:
        for k in cevapla(s["soru"], arayici)["kaynaklar"]:
            assert k["alinti"], k["id"]
            for a in k["alinti"]:
                assert a in k["tam_metin"], (s["soru"], k["id"])


def test_her_kaynakta_atif_ve_tarih(arayici):
    c = cevapla("Mazeret sınavına girmek için belgemi ne zamana kadar vermeliyim?", arayici)
    assert c["durum"] == "bulundu"
    for k in c["kaynaklar"]:
        assert ", " in k["atif"] and k["gecerlilik"]
    # aynı kural hem yönetmelik md. 17'de hem haklı nedenler 6. maddede var
    dogru = [k for k in c["kaynaklar"] if k["atif"].endswith(("Madde 17 (Sınavlar ve değerlendirme), s. 5",
                                                               "Usul ve Esaslar, 6. madde, s. 2"))]
    assert dogru and any("üç iş günü" in a for k in dogru for a in k["alinti"])


def test_alakasiz_soru_bulamadim(arayici):
    c = cevapla("Kampüste kaç tane kantin var?", arayici)
    assert c["durum"] == "bulunamadi"
    assert c["kaynaklar"] == []
    assert "bulamadım" in c["mesaj"]


def test_bos_soru(arayici):
    assert cevapla("  ", arayici)["durum"] == "bulunamadi"


def test_butunleme_icin_cevap_uydurmaz(arayici):
    c = cevapla("Bütünleme sınavına kimler girebilir?", arayici)
    assert c["durum"] != "bulundu"


def test_ocr_kaynak_isaretli(arayici):
    c = cevapla("Azami süreyi dolduran son sınıf öğrencisine kaç ek sınav hakkı verilir?", arayici)
    assert any(k["ocr"] for k in c["kaynaklar"])


def test_birimlere_bolme():
    metin = "(1) Kısa fıkra.\n(2) " + "Uzun cümle burada. " * 30
    birimler = birimlere_bol(metin)
    assert birimler[0] == "(1) Kısa fıkra."
    assert all(len(b) <= 420 for b in birimler)
    bentli = "Talepler karara bağlanır: (a) birinci durum " + "x " * 150 + ", (b) ikinci durum " + "y " * 150
    assert [b[:3] for b in birimlere_bol(bentli)][1:] == ["(a)", "(b)"]


def test_cevap_dogrulugu(arayici):
    ana = cevap_olc(arayici, sorulari_oku())
    assert ana["cevapli_dogru"] >= 25 and ana["cevapsiz_dogru"] == ana["cevapsiz"]
    ayrik = cevap_olc(arayici, sorulari_oku(AYRIK_SET))
    assert ayrik["cevapli_dogru"] >= 9
    kal = cevap_olc(arayici, [{"soru": q, "cevapsiz": True} for q in sorulari_oku(KALIBRASYON)])
    assert kal["cevapsiz_dogru"] == kal["cevapsiz"]
