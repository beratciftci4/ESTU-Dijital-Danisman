"""Mezuniyet kontrolü testleri: kurallar kaynaktakiyle aynı mı, hesap doğru mu."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from indeks import parcalari_oku
from belge_kontrol import programlari_oku
from mezuniyet import GEREKEN_AKTS, GEREKEN_GNO, KAYNAK_MEZUNIYET, KAYNAK_TEK_DERS, kontrol, staj_kurali

PARCALAR = {p["id"]: p["metin"] for p in parcalari_oku()}
HIC = {"FF": 0, "YZ": 0, "DZ": 0, "EK": 0, "ÇK": 0}


def test_kurallar_kaynakla_ayni():
    """Koddaki sayılar belgedeki sayılarla aynı olmalı, belge değişirse test patlasın."""
    md25 = PARCALAR[KAYNAK_MEZUNIYET]
    assert f"lisans programında en az {GEREKEN_AKTS} AKTS" in md25
    assert "ÇK, DZ, EK, FF ve YZ harf notu olmayan" in md25
    assert f"GNO’su en az {GEREKEN_GNO:.2f}".replace(".", ",") in md25
    gun, kaynak = staj_kurali("istatistik")
    assert f"en az {gun} iş günü staj yapmak zorundadır" in PARCALAR[kaynak]
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


def test_bolumlerin_staj_kurali_yonergeyle_ayni():
    """programlar.yaml'daki staj süreleri Fen staj yönergesinin EK-3 notuyla tutarlı olmalı."""
    ek3 = PARCALAR["fen_staj#ek-4"]
    assert "Kimya ve Matematik Bölümü öğrencileri için staj isteğe bağlıdır" in ek3
    assert "Fizik, İstatistik ve Biyoloji Bölümlerinin öğrencileri ise 20 iş günü staj yapmak zorundadır" in ek3
    _, programlar = programlari_oku()
    gun = {p["id"]: p["staj_gunu"] for p in programlar}
    assert gun["kimya"] is None and gun["matematik"] is None
    assert gun["fizik"] == gun["biyoloji"] == gun["istatistik"] == 20


def test_stajsiz_bolum():
    s = kontrol(240, 2.5, HIC, 0, program="matematik")
    assert s["mezun_olabilir"]
    assert any(x["ad"] == "Zorunlu staj yok" for x in s["satirlar"])
    assert not kontrol(240, 2.5, HIC, 0, program="fizik")["mezun_olabilir"]


def test_programlar_tutarli():
    """programlar.yaml'daki her kaynak gerçekten var olan bir parça, her bölümün Bologna sayfaları listede."""
    from belge_kontrol import belgeleri_oku
    fakulteler, programlar = programlari_oku()
    belge_idleri = {b["id"] for b in belgeleri_oku()}
    for f in fakulteler.values():
        assert f["staj_maddesi"] in PARCALAR and f["staj_listesi"] in PARCALAR
        assert f["staj_belgesi"] in belge_idleri and f["staj_birimi"] in ("gün", "iş günü")
    for p in programlar:
        assert p["fakulte"] in fakulteler, p["id"]
        assert p["staj_gunu"] is not None or "staj_notu" in p, p["id"]
        assert not p.get("staj_suresi_belirsiz") or (p["staj_gunu"] is None and p.get("staj_ek")), p["id"]
        assert {f"{p['id']}_ders_plani", f"{p['id']}_program_bilgileri"} <= belge_idleri, p["id"]
        if p.get("staj_kaynagi"):
            assert p["staj_kaynagi"] in PARCALAR, p["id"]
            # Bologna sayfasındaki süre programlar.yaml'dakiyle tutarlı olmalı
            if p["staj_gunu"]:
                assert str(p["staj_gunu"]) in PARCALAR[p["staj_kaynagi"]] or p["id"] in ("elektrik_elektronik_muh", "endustri_muh"), p["id"]


def test_muhendislik_staji():
    assert "40 (kırk) günden az olamaz" in PARCALAR["muh_staj#madde-8"]
    s = kontrol(240, 2.5, HIC, 40, program="makine_muh")
    assert s["mezun_olabilir"] and any(x["ad"] == "En az 40 gün staj" for x in s["satirlar"])
    s = kontrol(240, 2.5, HIC, 40, program="endustri_muh")
    assert not s["mezun_olabilir"] and any("5 iş günü eksik" in x["aciklama"] for x in s["satirlar"])


def test_havacilik_staji():
    m9 = PARCALAR["hubf_staj#madde-9"]
    assert "en az 40 iş günü karşılığı" in m9 and "en az 30 iş günü karşılığı" in m9
    assert "Bölümde staj isteğe bağlıdır" in PARCALAR["havacilik_yonetimi_program_bilgileri#bolum-Program_Profili"]
    assert kontrol(240, 2.5, HIC, 0, program="havacilik_yonetimi")["mezun_olabilir"]
    assert not kontrol(240, 2.5, HIC, 25, program="hava_trafik")["mezun_olabilir"]
    s = kontrol(240, 2.5, HIC, 0, program="havacilik_uzay_muh")     # süre belgelerde yok
    assert not s["mezun_olabilir"] and any("bölümüne sor" in x["aciklama"] for x in s["satirlar"])


def test_mimarlik_staji():
    assert "60 iş gününden az olamaz" in PARCALAR["mtf_staj#madde-14"]
    assert not kontrol(240, 2.5, HIC, 40, program="mimarlik")["mezun_olabilir"]
    assert kontrol(240, 2.5, HIC, 60, program="endustriyel_tasarim")["mezun_olabilir"]
