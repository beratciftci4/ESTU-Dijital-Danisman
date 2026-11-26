"""5. aşama testleri: API'siz cevap, atıf biçimi ve "bulamadım" davranışı."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from arama import Arayici
from cevap import ONLISANS, atif, birimlere_bol, cevapla, gecerlilik
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


def test_havacilik_bolumleri(arayici):
    from degerlendir import HUBF_SET
    hubf = cevap_olc(arayici, sorulari_oku(HUBF_SET))
    assert hubf["cevapli_dogru"] >= 12 and hubf["ozet_dogru"] >= 14


def test_mimarlik_bolumleri(arayici):
    from degerlendir import MTF_SET
    mtf = cevap_olc(arayici, sorulari_oku(MTF_SET))
    assert mtf["cevapli_dogru"] >= 15 and mtf["ozet_dogru"] >= 14


def test_pts_cumlesi_normal_staji_ezmiyor(arayici):
    from cevap import cevapla
    c = cevapla("Stajda devamsızlık hakkım var mı?", arayici, program="mimarlik")
    assert "PTS" not in c["ozet"]["metin"].split(".")[0]


def test_spor_bolumleri(arayici):
    from degerlendir import SPOR_SET
    spor = cevap_olc(arayici, sorulari_oku(SPOR_SET))
    assert spor["cevapli_dogru"] >= 12 and spor["ozet_dogru"] >= 13


def test_spor_staj_uydurmuyor(arayici):
    from cevap import cevapla
    c = cevapla("Kaç gün staj yapmam gerekiyor?", arayici, program="spor_yoneticiligi")
    assert "bölümüne sor" in c["ozet"]["metin"]


def test_cevapsiz_dogrulama_seti(arayici):
    # eşik seçilirken bakılmayan 40 cevapsız soru: çoğuna doğrudan "bulamadım" denmeli
    from cevap import cevapla
    from degerlendir import CEVAPSIZ_DOGRULAMA
    durumlar = [cevapla(s["soru"], arayici, program=s["program"])["durum"]
                for s in sorulari_oku(CEVAPSIZ_DOGRULAMA)]
    assert durumlar.count("bulunamadi") >= 22 and durumlar.count("bulundu") <= 8


def test_onlisans_programlari(arayici):
    from degerlendir import ONLISANS_SET
    s = cevap_olc(arayici, sorulari_oku(ONLISANS_SET))
    assert s["cevapli_dogru"] >= 14 and s["ozet_dogru"] >= 14 and s["cevapsiz_dogru"] == 2


def test_myo_yonergesi_lisansa_karismiyor(arayici):
    # MYO staj yönergesi "duzey:onlisans" kapsamında; lisans bölümünde aramaya girmemeli
    idler = {arayici.parcalar[i]["belge_id"] for i in arayici.alt_kume("istatistik")[0]}
    assert "myo_staj" not in idler
    assert "myo_staj" in {arayici.parcalar[i]["belge_id"] for i in arayici.alt_kume("lojistik")[0]}
    from cevap import cevapla
    c = cevapla("Kaç gün staj yapmam gerekiyor?", arayici, program="lojistik")
    assert "Lojistik programında" in c["ozet"]["metin"] and "20 iş günü" in c["ozet"]["metin"]


def test_sorulan_yariyil():
    from cevap import sorulan_yariyil
    assert [sorulan_yariyil(s) for s in ["Birinci yarıyılın dersleri", "3. dönem dersleri", "5.yarıyıl",
                                         "1. sınıf", "ilk dönem", "yaz dönemi"]] == [1, 3, 5, None, 1, None]


def test_butun_bolumlerde_staj_ve_ilk_yariyil(arayici):
    # 53 bölüm/programın hepsinde staj cevabı programdaki gün sayısını söylemeli (ya da belirsizliği),
    # "birinci yarıyıl" sorusu da o bölümün 1. yarıyılını getirmeli
    from belge_kontrol import programlari_oku
    from cevap import cevapla
    for p in programlari_oku()[1]:
        m = cevapla("Kaç gün staj yapmalıyım?", arayici, program=p["id"])["ozet"]["metin"]
        assert (str(p["staj_gunu"]) in m) if p["staj_gunu"] else \
            re.search(r"sor\.|şartı yok|net anlaşılmıyor", m), (p["id"], m)
        c = cevapla("Birinci yarıyılın zorunlu dersleri neler?", arayici, program=p["id"])
        assert c["ozet"]["ilk_parca"] == f"{p['id']}_ders_plani#bolum-I.YARIYIL", p["id"]


def test_egitim_dili(arayici):
    from cevap import egitim_dili_soruluyor
    assert egitim_dili_soruluyor("Eğitim dili nedir?") and egitim_dili_soruluyor("Bölüm İngilizce mi?")
    assert not egitim_dili_soruluyor("İngilizce hazırlık zorunlu mu?")
    assert not egitim_dili_soruluyor("Türk Dili dersi kaç AKTS?")
    c = cevapla("Eğitim dili nedir?", arayici, program="istatistik")
    assert c["durum"] == "bulundu" and "%30 İngilizce" in c["ozet"]["metin"]
    c = cevapla("Dersler hangi dilde?", arayici, program="bilgisayar_muh")
    assert "İngilizce" in c["ozet"]["cumleler"][0]
    c = cevapla("Öğretim dili ne?", arayici, program="lojistik")
    assert "Türkçe" in c["ozet"]["cumleler"][0]


def test_ders_adiyla_soru(arayici):
    from cevap import sorulan_ders_cumleleri
    assert sorulan_ders_cumleleri("İST333 kaç AKTS?", "istatistik")
    assert not sorulan_ders_cumleleri("Staj hangi dönemde yapılır?", "istatistik")
    assert not sorulan_ders_cumleleri("Matematik dersinden kalırsam ne olur?", "istatistik")
    c = cevapla("Regresyon analizi hangi dönemde?", arayici, program="istatistik")
    assert c["durum"] == "bulundu" and "5. yarıyıl" in c["ozet"]["metin"]
    c = cevapla("Öğretmenlik uygulaması hangi dönemde?", arayici, program="beden_egitimi")
    assert c["durum"] == "bulundu" and "Öğretmenlik Uygulaması" in c["ozet"]["metin"]


def test_program_bolumu_niyetleri(arayici):
    from cevap import sorulan_program_bolumu
    assert sorulan_program_bolumu("Dikey geçiş yapabilir miyim?", "lojistik").endswith("Üst_Derece_Programlarına_Geçiş")
    assert sorulan_program_bolumu("Dikey geçiş yapabilir miyim?", "istatistik") is None   # lisansta DGS yok
    assert sorulan_program_bolumu("Mezunlar ortalama kaç maaş alıyor?", "istatistik") is None
    c = cevapla("Mezun olunca nerelerde çalışabilirim?", arayici, program="istatistik")
    assert c["durum"] == "bulundu" and "banka" in c["ozet"]["metin"]


def test_bolume_ozel_ornek_sorular_butun_programlarda(arayici):
    # arayüzdeki bölüme özel örnek soruların hepsi her programda net cevaplı olmalı
    from belge_kontrol import programlari_oku
    for p in programlari_oku()[1]:
        sorular = ["Eğitim dili nedir?"]
        sorular.append("Dikey geçiş yapabilir miyim?" if p["id"] in ONLISANS else "Mezun olunca nerelerde çalışabilirim?")
        for s in sorular:
            assert cevapla(s, arayici, program=p["id"])["durum"] == "bulundu", (p["id"], s)
