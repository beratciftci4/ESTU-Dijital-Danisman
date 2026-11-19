"""2. aşama testleri: madde ayrıştırma, sayfa numaraları ve Türkçe karakterler."""
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from ayristir import tablo_bozuk_mu, tum_belgeler
from belge_kontrol import KAYNAK_KLASORU, belgeleri_oku

PARCALAR = tum_belgeler()
BELGELER = {b["id"]: b for b in belgeleri_oku()}


def parcalari(belge_id, tur=None):
    return [p for p in PARCALAR if p["belge_id"] == belge_id and (tur is None or p["tur"] == tur)]


def bul(pid):
    return next(p for p in PARCALAR if p["id"] == pid)


def sadele(s):
    return re.sub(r"[\s|.…]+", "", unicodedata.normalize("NFC", s))


# ---------- madde sayıları ve sırası ----------

BEKLENEN = {
    # belge_id: (tür, beklenen numaralar)
    "yonetmelik": ("madde", [str(i) for i in range(1, 21)] + ["20/A"] + [str(i) for i in range(21, 30)]),
    "fen_staj": ("madde", [str(i) for i in range(1, 19)]),
    "danismanlik": ("madde", [str(i) for i in range(1, 16)]),
    "proje_temelli_staj": ("madde", [str(i) for i in range(1, 23)]),
    "hakli_nedenler": ("bent", [str(i) for i in range(1, 12)]),
    "tek_ders": ("bent", [str(i) for i in range(1, 10)]),
    "yaz_okulu": ("bent", [str(i) for i in range(1, 24)]),
    "not_karsiliklari": ("bent", [str(i) for i in range(1, 10)]),
    "ek_sinav": ("bent", ["1", "2", "3"]),
}


@pytest.mark.parametrize("belge_id", BEKLENEN)
def test_madde_numaralari_eksiksiz_ve_sirali(belge_id):
    tur, numaralar = BEKLENEN[belge_id]
    assert [p["no"] for p in parcalari(belge_id, tur)] == numaralar


def test_hicbir_madde_kacmamis():
    # bir parçanın içinde satır başında "MADDE 12" kalmışsa bölme kaçmış demektir
    for p in PARCALAR:
        assert not re.search(r"(^|\n)MADDE\s+\d", p["metin"]), p["id"]


def test_id_benzersiz_ve_metin_bos_degil():
    idler = [p["id"] for p in PARCALAR]
    assert len(idler) == len(set(idler))
    for p in PARCALAR:
        assert len(p["metin"]) > 20, p["id"]


# ---------- sayfa numaraları ----------

def test_sayfa_numaralari_dogru():
    """Her madde/bentin ilk cümlesi, kayıtlı sayfa_bas sayfasında gerçekten geçmeli."""
    for belge_id, (tur, _) in BEKLENEN.items():
        if belge_id == "ek_sinav":
            continue  # taranmış, sayfa metni yok
        doc = pymupdf.open(KAYNAK_KLASORU / BELGELER[belge_id]["dosya"])
        for p in parcalari(belge_id, tur):
            ilk = sadele(p["metin"])[:30]
            assert ilk in sadele(doc[p["sayfa_bas"] - 1].get_text()), (p["id"], p["sayfa_bas"])
            assert p["sayfa_bas"] <= p["sayfa_bit"] <= len(doc)


def test_bilinen_madde_sayfalari():
    assert bul("yonetmelik#madde-10")["sayfa_bas"] == 3
    assert bul("yonetmelik#madde-25")["sayfa_bas"] == 9
    assert bul("yonetmelik#madde-20/A")["sayfa_bas"] == 7


# ---------- içerik: bilinen cevaplar doğru parçada mı ----------

def test_yonetmelik_basliklar_ve_icerik():
    m10 = bul("yonetmelik#madde-10")
    assert m10["baslik"] == "Kayıt yenileme ve ders kaydı"
    assert "en çok 45 AKTS" in m10["metin"] and "en çok 60 AKTS" in m10["metin"]
    assert m10["bolum"].startswith("İKİNCİ BÖLÜM")

    assert bul("yonetmelik#madde-7")["baslik"] == "Ek sınav hakkı"
    assert bul("yonetmelik#madde-20/A")["baslik"] == "Yaz okulu"
    assert "en çok 20 AKTS" in bul("yonetmelik#madde-20/A")["metin"]
    assert "en az 240 AKTS" in bul("yonetmelik#madde-25")["metin"]


def test_bolum_basliklari_maddeye_karismamis():
    for p in parcalari("yonetmelik", "madde"):
        assert "BÖLÜM" not in p["metin"], p["id"]


def test_fikralar_ayri_satirda():
    satirlar = bul("yonetmelik#madde-10")["metin"].split("\n")
    assert [s[:3] for s in satirlar] == ["(1)", "(2)", "(3)", "(4)"]


def test_staj_suresi_istatistik():
    metin = " ".join(p["metin"] for p in parcalari("fen_staj"))
    assert "Fizik, İstatistik ve Biyoloji Bölümlerinin öğrencileri ise 20 iş günü staj" in metin


def test_kunye_maddeye_karismamis():
    assert "Açıklama" not in bul("fen_staj#madde-18")["metin"]
    assert "33162" in bul("yonetmelik#kunye-1")["metin"]


def test_tablo_satirlari_duzgun():
    metin = bul("not_karsiliklari#bent-1")["metin"]
    assert "50‒55 | CC | 2,00" in metin
    assert "0‒32 | FF | 0,00" in metin


def test_birlesik_hucreli_tablo():
    metin = bul("not_karsiliklari#bent-6")["metin"]
    assert "800 | 166 | 100" in metin and "760 | 160 | 90" in metin
    assert "800 797" not in metin
    # ECTS tablosunda birleşik hücreler: AA ve AB -> A
    assert "AA AB | A | AA" in bul("not_karsiliklari#bent-5")["metin"]


def test_bozuk_tablo_tespiti():
    assert tablo_bozuk_mu(["800 797 | 166 165 | 100 99", "797 794 | 165 ‒ | 99 98"])
    assert not tablo_bozuk_mu(["800 | 166 | 100", "797 | 165 | 99"])


def test_gorsel_tablolar_isaretli():
    sayfalar = [p["sayfa_bas"] for p in parcalari("not_karsiliklari", "tablo_gorsel")]
    assert sayfalar == [2, 3, 4, 5]


def test_ocr_belgesi():
    for p in parcalari("ek_sinav"):
        assert p["ocr"] is True
    m2 = bul("ek_sinav#bent-2")
    assert "iki ek sınav hakkı verilir" in m2["metin"]
    assert "sınırsız ek sınav hakkı" in m2["metin"]
    # elle düzeltilen tablo
    assert "50-55 | 2.00 | CC" in bul("ek_sinav#kunye-1")["metin"]


def test_bologna_sayfalari():
    assert "240 ECTS" in bul("program_bilgileri#bolum-Mezuniyet_Koşulları")["metin"]
    yariyillar = [p["no"] for p in parcalari("ders_plani")]
    assert yariyillar[:8] == ["I.YARIYIL", "II.YARIYIL", "III.YARIYIL", "IV.YARIYIL",
                              "V.YARIYIL", "VI.YARIYIL", "VII.YARIYIL", "VIII.YARIYIL"]
    assert "Mesleki Seçmeli Dersler" in yariyillar and "Seçmeli Dersler" in yariyillar
    assert "İST239 | Probability I (Olasılık I) | İngilizce | 4+0 | 6.0" in bul("ders_plani#bolum-III.YARIYIL")["metin"]
    assert "YİST303 | Data Visualization" in bul("ders_plani#bolum-Mesleki_Seçmeli_Dersler")["metin"]


# ---------- Türkçe karakterler ----------

def test_turkce_karakter_bozulmasi_yok():
    bozuk = re.compile(r"[�̇]|Ã|Ä±|Å[Ÿž]|Ä[Ÿž]")
    for p in PARCALAR:
        assert not bozuk.search(p["metin"]), p["id"]
        assert unicodedata.normalize("NFC", p["metin"]) == p["metin"], p["id"]


@pytest.mark.parametrize("belge_id", BELGELER)
def test_her_belgede_turkce_harfler_var(belge_id):
    metin = " ".join(p["metin"] for p in parcalari(belge_id))
    for harf in "ğüşıöçİ":
        assert harf in metin, (belge_id, harf)


def test_bilinen_kelimeler_dogru_yazilmis():
    metin = " ".join(p["metin"] for p in PARCALAR)
    for kelime in ["Eskişehir Teknik Üniversitesi", "öğrenci", "yükseköğretim", "Öğretim",
                   "değerlendirme", "İstatistik", "çekilebilir", "yarıyıl", "başarısız"]:
        assert kelime in metin, kelime


# ---------- metin kaybı ----------

@pytest.mark.parametrize("belge_id", [b for b in BEKLENEN if b != "ek_sinav"])
def test_metin_kaybi_yok(belge_id):
    """PDF'teki karakterlerin neredeyse hepsi parçalarda olmalı.
    Kayıp sayılabilecekler: "MADDE 10-", "1)" gibi numaralar ve belge başlığı."""
    doc = pymupdf.open(KAYNAK_KLASORU / BELGELER[belge_id]["dosya"])
    ham_metin = re.sub(r"Sayfa\s*:?\s*\d+\s*/\s*\d+", "", "\n".join(s.get_text() for s in doc))
    # tamamı büyük harf satırlar belge başlığı, o zaten belge_adi alanında duruyor
    ham_metin = "\n".join(x for x in ham_metin.split("\n") if not (x.strip().isupper() and len(x.strip()) > 15))
    ham = Counter(sadele(ham_metin))
    parca = Counter(sadele("".join(p["metin"] + (p["baslik"] or "") + (p["bolum"] or "")
                                   for p in parcalari(belge_id))))
    kayip = sum((ham - parca).values()) / sum(ham.values())
    assert kayip < 0.04, f"{belge_id}: %{100 * kayip:.1f} kayıp"
