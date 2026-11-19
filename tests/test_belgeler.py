import copy
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from belge_kontrol import belgeleri_oku, hatalari_bul

belgeler = belgeleri_oku()


def test_liste_hatasiz():
    assert hatalari_bul(belgeler) == []


def test_zorunlu_belgeler_var():
    idler = {b["id"] for b in belgeler}
    for i in ["yonetmelik", "fen_staj", "ders_plani", "program_bilgileri"]:
        assert i in idler


def test_yonetmelik_guncel_surum():
    y = next(b for b in belgeler if b["id"] == "yonetmelik")
    assert y["yayim"] == date(2025, 9, 9)
    assert y["son_degisiklik"] == date(2026, 2, 8)
    assert "33012" in y["dayanak"] and "33162" in y["dayanak"]


def test_turkce_karakterler():
    y = next(b for b in belgeler if b["id"] == "yonetmelik")
    for harf in "şÜÖğı":
        assert harf in y["ad"]


def test_hepsi_aktif_ve_dosyasi_var():
    from belge_kontrol import KAYNAK_KLASORU, sha256
    for b in belgeler:
        assert b["durum"] == "aktif", b["id"]
        yol = KAYNAK_KLASORU / b["dosya"]
        assert yol.exists(), b["dosya"]
        assert sha256(yol) == b["sha256"], b["id"]


def test_yonetmelik_dogru_pdf():
    # eski 2018 sürümü (RG 30540) yanlışlıkla gelmesin
    import pymupdf
    from belge_kontrol import KAYNAK_KLASORU
    metin = "".join(s.get_text() for s in pymupdf.open(KAYNAK_KLASORU / "yonetmelik.pdf"))
    assert "33012" in metin and "33162" in metin
    assert "MADDE 20/A" in metin
    assert "45 AKTS" in metin


def test_ayni_id_yakalaniyor():
    bozuk = belgeler + [copy.deepcopy(belgeler[0])]
    assert any("iki kere" in h for h in hatalari_bul(bozuk))


def test_yanlis_tarih_yakalaniyor():
    bozuk = copy.deepcopy(belgeler)
    bozuk[0]["yururluk"] = "22.09.2025"
    assert any("YYYY-AA-GG" in h for h in hatalari_bul(bozuk))


def test_turkce_dosya_adi_yakalaniyor():
    bozuk = copy.deepcopy(belgeler)
    bozuk[0]["dosya"] = "yönetmelik.pdf"
    assert len(hatalari_bul(bozuk)) == 1


def test_nfd_yakalaniyor():
    bozuk = copy.deepcopy(belgeler)
    bozuk[0]["ad"] = unicodedata.normalize("NFD", bozuk[0]["ad"])
    assert any("NFC" in h for h in hatalari_bul(bozuk))


def test_aktif_belge_eksik_olamaz():
    bozuk = copy.deepcopy(belgeler)
    bozuk[0]["sha256"] = None
    bozuk[0]["indirme_tarihi"] = None
    hatalar = hatalari_bul(bozuk)
    assert any("sha256 boş" in h for h in hatalar)
    assert any("indirme_tarihi boş" in h for h in hatalar)
