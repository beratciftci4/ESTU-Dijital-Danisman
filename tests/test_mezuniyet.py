"""Mezuniyet kontrolü testleri: kurallar kaynaktakiyle aynı mı, hesap doğru mu."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from indeks import parcalari_oku
from mezuniyet import (GEREKEN_AKTS, GEREKEN_GNO, GEREKEN_STAJ_GUNU, KAYNAK_MEZUNIYET, KAYNAK_STAJ,
                       KAYNAK_TEK_DERS, kontrol)

PARCALAR = {p["id"]: p["metin"] for p in parcalari_oku()}
HIC = {"FF": 0, "YZ": 0, "DZ": 0, "EK": 0, "ÇK": 0}


def test_kurallar_kaynakla_ayni():
    """Koddaki sayılar belgedeki sayılarla aynı olmalı, belge değişirse test patlasın."""
    md25 = PARCALAR[KAYNAK_MEZUNIYET]
    assert f"lisans programında en az {GEREKEN_AKTS} AKTS" in md25
    assert "ÇK, DZ, EK, FF ve YZ harf notu olmayan" in md25
    assert f"GNO’su en az {GEREKEN_GNO:.2f}".replace(".", ",") in md25
    assert f"en az {GEREKEN_STAJ_GUNU} iş günü staj yapmak zorundadır" in PARCALAR[KAYNAK_STAJ]
    assert "tek dersten FF veya YZ" in PARCALAR[KAYNAK_TEK_DERS]


def test_her_sey_tamam():
    s = kontrol(242, 2.85, HIC, 20)
    assert s["mezun_olabilir"]
    assert all(x["tamam"] for x in s["satirlar"])


def test_eksikler_tek_tek():
    s = kontrol(228, 1.95, HIC | {"FF": 2}, 0)
    assert not s["mezun_olabilir"]
    eksik = {x["ad"]: x["aciklama"] for x in s["satirlar"] if not x["tamam"]}
    assert "12 AKTS eksik" in eksik["En az 240 AKTS"]
    assert "1,95" in eksik["GNO en az 2,00"]
    assert "2 ders FF" in eksik["ÇK, DZ, EK, FF ve YZ notu olmaması"]
    assert "20 iş günü eksik" in eksik["En az 20 iş günü staj"]


def test_sinir_degerler():
    s = kontrol(240, 2.00, HIC, 20)
    assert s["mezun_olabilir"]
    assert not kontrol(239.5, 2.00, HIC, 20)["mezun_olabilir"]
    assert not kontrol(240, 1.99, HIC, 20)["mezun_olabilir"]


def test_tek_ders_onerisi():
    assert kontrol(234, 2.40, HIC | {"FF": 1}, 20)["oneriler"]
    assert not kontrol(234, 2.40, HIC | {"FF": 2}, 20)["oneriler"]
    assert not kontrol(234, 2.40, HIC | {"FF": 1, "DZ": 1}, 20)["oneriler"]
    assert kontrol(234, 2.40, HIC | {"FF": 1}, 20)["oneriler"][0]["kaynak"] == KAYNAK_TEK_DERS


def test_her_satirin_kaynagi_var():
    for x in kontrol(100, 1.5, HIC, 5)["satirlar"]:
        assert x["kaynak"] in PARCALAR
