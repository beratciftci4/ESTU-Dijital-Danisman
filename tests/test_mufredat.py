"""Bölüm sitesindeki yıllık ders planları (istatistik 2024-25, 2025-26, 2026-27)."""
import json

import pytest

from arama import Arayici
from belge_kontrol import bolum_ve_yil, ders_plani_mi
from degerlendir import KLASOR, MUFREDAT_SET, cevap_olc, sorulari_oku

PARCALAR = {json.loads(s)["id"]: json.loads(s) for s in open(KLASOR / "cikti" / "parcalar.jsonl", encoding="utf-8")}


@pytest.fixture(scope="module")
def arayici():
    return Arayici()


def test_anahtar_ve_belge_adlari():
    assert ders_plani_mi("istatistik_ders_plani") == ("istatistik", None)
    assert ders_plani_mi("istatistik_ders_plani_2024") == ("istatistik", 2024)
    assert ders_plani_mi("istatistik_program_bilgileri") is None
    assert bolum_ve_yil("istatistik@2025") == ("istatistik", 2025)
    assert bolum_ve_yil("istatistik") == ("istatistik", None)


def test_yillik_planlar_dogru_okundu():
    # her yarıyıl 30 AKTS, PDF'teki değerlerle karşılaştırıldı
    for yil in (2024, 2025, 2026):
        for no in ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]:
            metin = PARCALAR[f"istatistik_ders_plani_{yil}#bolum-{no}.YARIYIL"]["metin"]
            assert metin.endswith("Toplam | 30"), (yil, no)
    assert "EMAT113 | Calculus I (Genel Matematik I) | İngilizce | 4+2 | 7.5" in \
        PARCALAR["istatistik_ders_plani_2024#bolum-I.YARIYIL"]["metin"]
    # iki satıra bölünmüş ders adı birleşmiş olmalı
    assert "İST438 | Machine Learning Methods and Applications (Makine Öğrenmesi Yöntemleri ve Uygulamaları)" in \
        PARCALAR["istatistik_ders_plani_2024#bolum-Mesleki_Seçmeli_Dersler"]["metin"]
    assert "Mobil Programlama" in PARCALAR["istatistik_ders_plani_2024#bolum-Mesleki_Seçmeli_Dersler"]["metin"]
    assert "Mobil Programlama" not in PARCALAR["istatistik_ders_plani_2025#bolum-Mesleki_Seçmeli_Dersler"]["metin"]


def test_plan_farki_cumleleri():
    from cevap import tum_ozetler
    oz = tum_ozetler()
    c25 = " ".join(oz["istatistik_ders_plani_2025#bolum-Mesleki_Seçmeli_Dersler"])
    assert "çıkarılan (kaldırılan) dersler: Mobil Programlama" in c25
    assert "Benzetim dersinin AKTS'si 6 iken 4,5 oldu" in c25
    c1 = " ".join(oz["istatistik_ders_plani_2025#bolum-I.YARIYIL"])
    assert "kodu EMAT113 iken MAT1013" in c1
    assert "zorunlu derslere ders eklenmedi ya da çıkarılmadı" in c1


def test_yil_secilince_sadece_o_plan_aranir(arayici):
    for anahtar, beklenen in [("istatistik", None), ("istatistik@2024", 2024), ("istatistik@2026", 2026)]:
        yillar = {ders_plani_mi(arayici.parcalar[i]["belge_id"])[1] for i in arayici.alt_kume(anahtar)[0]
                  if ders_plani_mi(arayici.parcalar[i]["belge_id"])}
        assert yillar == {beklenen}, anahtar


def test_mufredat_sorulari(arayici):
    s = cevap_olc(arayici, sorulari_oku(MUFREDAT_SET))
    assert s["ozet_dogru"] >= 12 and s["cevapli_dogru"] >= 10
