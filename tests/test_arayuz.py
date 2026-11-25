"""6. aşama testleri: Streamlit arayüzü (tarayıcı olmadan, streamlit.testing ile)."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

KLASOR = Path(__file__).parent.parent
sys.path.insert(0, str(KLASOR))


def uygulama(bolum="istatistik"):
    at = AppTest.from_file(str(KLASOR / "app.py"), default_timeout=120)
    if bolum:
        at.query_params["bolum"] = bolum
    return at.run()


def sor(soru, bolum="istatistik"):
    at = uygulama(bolum)
    at.text_input(key="soru").set_value(soru)
    at.button[0].click()  # ilk sekmedeki "Sor" düğmesi
    at.run()
    assert not at.exception, at.exception
    return [m.value for m in at.markdown]


def test_acilis_hatasiz():
    at = uygulama()
    assert not at.exception
    metin = " ".join(m.value for m in at.markdown)
    assert "Dijital Danışman" in metin


def test_kenar_cubugunda_bolumun_belgeleri():
    """Bölüm seçilince ortak belgeler + fakültenin staj yönergesi + bölümün Bologna sayfaları."""
    kenar = " ".join(m.value for m in uygulama("istatistik").sidebar.markdown)
    assert kenar.count('class="belge-satir"') == 11
    assert "Yürürlük 22.09.2025, son değişiklik 08.02.2026" in kenar
    assert "İstatistik Bölümü Dersler" in kenar and "Fizik Bölümü" not in kenar

    kenar = " ".join(m.value for m in uygulama("fizik").sidebar.markdown)
    assert "Fizik Bölümü Dersler" in kenar and "Fen Fakültesi Staj" in kenar and "İstatistik Bölümü" not in kenar

    kenar = " ".join(m.value for m in uygulama(None).sidebar.markdown)
    assert kenar.count('class="belge-satir"') == 8 and "Staj Yönergesi" not in kenar.replace("Proje Temelli Staj Yönergesi", "")


def test_bolum_secimi_aramayi_degistiriyor():
    md = sor("Birinci yarıyılda hangi zorunlu dersler var?", bolum="fizik")
    kisa = next(m for m in md if 'class="cevap' in m)
    assert "Fizik" in kisa and "İstatistik" not in kisa


def test_soru_kaynakli_cevap():
    md = sor("Derslere devam zorunluluğu yüzde kaç?")
    # önce sade kısa cevap, altında resmi maddeler
    kisa = [m for m in md if 'class="cevap bulundu"' in m]
    assert len(kisa) == 1 and "%80" in kisa[0] and "Dayanak:" in kisa[0] and "Madde 12" in kisa[0]
    assert md.index(kisa[0]) < min(i for i, m in enumerate(md) if 'class="kaynak"' in m)
    kaynaklar = [m for m in md if 'class="kaynak"' in m]
    assert len(kaynaklar) >= 3
    assert any("Madde 12" in m and "%80" in m and "Sayfa 4" in m for m in kaynaklar)


def test_alakasiz_soru():
    md = sor("Kampüste kaç tane kantin var?")
    assert any('class="durum bulunamadi"' in m and "bulamadım" in m for m in md)
    assert not any('class="kaynak"' in m for m in md)


def test_html_kaciriliyor():
    md = sor("<script>alert(1)</script> AKTS")
    assert not any("<script>alert(1)</script>" in m for m in md if 'class="durum' in m or 'class="kaynak"' in m)


def test_ornek_sorular_net_cevapli():
    import ast
    agac = ast.parse((KLASOR / "app.py").read_text(encoding="utf-8"))
    ORNEK_SORULAR = next(ast.literal_eval(d.value) for d in agac.body
                         if isinstance(d, ast.Assign) and d.targets[0].id == "ORNEK_SORULAR")
    from arama import Arayici
    from cevap import cevapla
    a = Arayici()
    for s in ORNEK_SORULAR:
        assert cevapla(s, a, program="istatistik")["durum"] == "bulundu", s


def test_mezuniyet_sekmesi():
    at = uygulama()
    at.number_input(key="akts").set_value(228.0)
    at.number_input(key="gno").set_value(2.4)
    at.number_input(key="staj").set_value(20)
    at.number_input(key="not_FF").set_value(1)
    at.button[1].click()  # "Kontrol et"
    at.run()
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "2 koşul henüz sağlanmıyor" in md
    assert "12 AKTS eksik" in md and "1 ders FF" in md
    assert "Madde 25 (Diplomalar ve belgeler), s. 9" in md
    assert any("tek ders sınavına" in i.value for i in at.info)


def test_mezuniyet_bolum_secmeden():
    at = uygulama(None)
    assert any("önce yukarıdan bölümünü seç" in i.value for i in at.info)


def test_mezuniyet_stajsiz_bolum_ve_ek_kosul():
    at = uygulama("kimya")
    at.number_input(key="akts").set_value(240.0)
    at.number_input(key="gno").set_value(2.4)
    at.button[1].click()
    at.run()
    md = " ".join(m.value for m in at.markdown)
    assert "Zorunlu staj yok" in md and "koşullarının hepsi sağlanıyor" in md
    assert any("72 AKTS İngilizce" in i.value for i in at.info)
