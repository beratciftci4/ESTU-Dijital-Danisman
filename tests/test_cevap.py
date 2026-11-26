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
    assert atif(parca(arayici, "istatistik_program_bilgileri#bolum-Mezuniyet_Koşulları")) == \
        "İstatistik Bölümü Program Bilgileri (Bologna), Mezuniyet Koşulları"


def test_gecerlilik_bilgisi(arayici):
    assert gecerlilik(parca(arayici, "yonetmelik#madde-10")) == \
        "Yürürlük: 22.09.2025, son değişiklik: 08.02.2026"
    assert "erişim" in gecerlilik(parca(arayici, "istatistik_ders_plani#bolum-III.YARIYIL"))


def test_cevap_sadece_resmi_metin(arayici):
    """Gösterilen her alıntı, kaynağın tam metninde aynen geçmeli (uydurma yok)."""
    sorular = sorulari_oku() + sorulari_oku(AYRIK_SET) + sorulari_oku(DOGRULAMA_SET)
    for s in sorular:
        for k in cevapla(s["soru"], arayici, program="istatistik")["kaynaklar"]:
            assert k["alinti"], k["id"]
            for a in k["alinti"]:
                assert a in k["tam_metin"], (s["soru"], k["id"])


def test_her_kaynakta_atif_ve_tarih(arayici):
    c = cevapla("Mazeret sınavına girmek için belgemi ne zamana kadar vermeliyim?", arayici, program="istatistik")
    assert c["durum"] == "bulundu"
    for k in c["kaynaklar"]:
        assert ", " in k["atif"] and k["gecerlilik"]
    # aynı kural hem yönetmelik md. 17'de hem haklı nedenler 6. maddede var
    dogru = [k for k in c["kaynaklar"] if k["atif"].endswith(("Madde 17 (Sınavlar ve değerlendirme), s. 5",
                                                               "Usul ve Esaslar, 6. madde, s. 2"))]
    assert dogru and any("üç iş günü" in a for k in dogru for a in k["alinti"])


def test_alakasiz_soru_bulamadim(arayici):
    c = cevapla("Kampüste kaç tane kantin var?", arayici, program="istatistik")
    assert c["durum"] == "bulunamadi"
    assert c["kaynaklar"] == []
    assert "bulamadım" in c["mesaj"]


def test_bos_soru(arayici):
    assert cevapla("  ", arayici, program="istatistik")["durum"] == "bulunamadi"


def test_butunleme_icin_cevap_uydurmaz(arayici):
    c = cevapla("Bütünleme sınavına kimler girebilir?", arayici, program="istatistik")
    assert c["durum"] != "bulundu"


def test_ocr_kaynak_isaretli(arayici):
    c = cevapla("Azami süreyi dolduran son sınıf öğrencisine kaç ek sınav hakkı verilir?", arayici, program="istatistik")
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
    # özet sıralaması eklenince "Erasmus için kaç dil puanı gerekiyor?" bulundu'ya geçti (raporlar/5_cevap.md)
    assert kal["cevapsiz_dogru"] >= kal["cevapsiz"] - 1


def test_fen_bolumleri(arayici):
    from degerlendir import FEN_SET
    fen = cevap_olc(arayici, sorulari_oku(FEN_SET))
    assert fen["cevapli_dogru"] >= 12 and fen["ozet_dogru"] >= 13


def test_bbbf_bolumleri(arayici):
    from degerlendir import BBBF_SET
    bbbf = cevap_olc(arayici, sorulari_oku(BBBF_SET))
    assert bbbf["cevapli_dogru"] >= 12 and bbbf["ozet_dogru"] >= 13


def test_muhendislik_bolumleri(arayici):
    from degerlendir import MUH_SET
    muh = cevap_olc(arayici, sorulari_oku(MUH_SET))
    assert muh["cevapli_dogru"] >= 12 and muh["ozet_dogru"] >= 15


# --- kısa cevap (ozetler.yaml) ---

def test_her_parcanin_ozeti_var(arayici):
    from cevap import ozetleri_oku, tum_ozetler
    ozetler = tum_ozetler()
    idler = {p["id"] for p in arayici.parcalar if p["tur"] != "kunye"}
    assert idler == set(ozetler), "ozetler.yaml ile parçalar uyuşmuyor"
    # ders planları otomatik, elle yazılanlarla karışmasın
    assert not any(k.split("#")[0].endswith("_ders_plani") for k in ozetleri_oku())
    for pid, cumleler in ozetler.items():
        assert cumleler and all(isinstance(c, str) and c.strip() for c in cumleler), pid


def test_ozet_vektorleri_guncel():
    """ozetler.yaml değişip vektörler yeniden hesaplanmadıysa uygulama ilk soruda bekler."""
    import numpy as np
    from cevap import OZET_VEKTORLERI, ozet_cumleleri, ozet_hash
    v = np.load(OZET_VEKTORLERI)
    assert str(v["ozet_hash"]) == ozet_hash()
    assert v["vektorler"].shape[0] == len(ozet_cumleleri())


@pytest.mark.parametrize("soru, beklenen, madde", [
    ("Derslere devam zorunluluğu yüzde kaç?", "%80", "yonetmelik#madde-12"),
    ("Mezuniyet şartları neler?", "240 AKTS", "istatistik_program_bilgileri#bolum-Mezuniyet_Koşulları"),
    ("Kaç iş günü staj yapmalıyım?", "20 iş günü", "fen_staj#ek-4"),   # bölüme özel staj cümlesi
    ("Mazeret sınavına nasıl başvurulur?", "üç iş günü", "hakli_nedenler#bent-6"),
])
def test_kisa_cevap(arayici, soru, beklenen, madde):
    c = cevapla(soru, arayici, program="istatistik")
    assert beklenen in c["ozet"]["cumleler"][0]
    assert c["ozet"]["ilk_parca"] == madde


def test_kisa_cevabin_dayanagi_kaynaklarda(arayici):
    """Kısa cevabın dayandığı her madde aşağıdaki kaynaklarda da gösterilmeli."""
    for s in sorulari_oku() + sorulari_oku(AYRIK_SET):
        c = cevapla(s["soru"], arayici, program="istatistik")
        if c["ozet"]:
            gosterilen = {k["id"] for k in c["kaynaklar"]}
            assert set(c["ozet"]["parcalar"]) <= gosterilen, s["soru"]
            assert len(c["ozet"]["cumleler"]) <= 3


def test_bulunamayinca_kisa_cevap_yok(arayici):
    c = cevapla("Kampüste kaç tane kantin var?", arayici, program="istatistik")
    assert c["durum"] == "bulunamadi" and c["ozet"] is None


@pytest.mark.parametrize("program, olmali, olmamali", [
    ("kimya", "isteğe bağlı", "staj yapman gerekir"),
    ("matematik", "isteğe bağlı", "staj yapman gerekir"),
    ("biyoloji", "20 iş günü", "staj zorunlu değildir"),
    ("endustri_muh", "45 iş günü", "staj zorunlu değildir"),
    ("makine_muh", "40 gün", "staj zorunlu değildir"),
    ("ucak_muh", "bölüme de sor", "staj zorunlu değildir"),
    ("yapay_zeka", "40 iş günü", "staj zorunlu değildir"),
])
def test_staj_cevabi_bolume_gore(arayici, program, olmali, olmamali):
    """Stajı isteğe bağlı bölüme "zorunlu" dememeli (genel kural 20 gün, istisna yönergenin ekinde)."""
    metin = cevapla("Kaç gün staj yapmalıyım?", arayici, program=program)["ozet"]["metin"]
    assert olmali in metin and olmamali not in metin, metin


def test_staj_suresi_niyeti():
    from cevap import staj_suresi_soruluyor
    for s in ["Kaç gün staj yapmalıyım?", "Staj zorunlu mu?", "Staj süresi ne kadar?", "Mezun olmak için staj şart mı?"]:
        assert staj_suresi_soruluyor(s), s
    for s in ["Staj notuna itiraz süresi ne kadar?", "Stajı ne zaman yapabilirim?",
              "Proje temelli staj kaç gün?", "Staj başvurusunu kaç gün önceden yapmalıyım?", "Kaç AKTS alabilirim?",
              "Stajın başarılı sayılması için değerlendirme notu en az kaç olmalı?",
              "Staj yerindeki sorumlu kişinin bilişim alanında yetkin olması gerekir mi?"]:
        assert not staj_suresi_soruluyor(s), s
