"""
5. aşama: API kullanmadan, kaynak göstererek cevap.

Cevap iki kısımdan oluşuyor:
  - kısa cevap: ozetler.yaml'daki elle yazılmış sade özet cümlelerinden soruya en uygun 1-3 tanesi
  - kaynaklar: soruya en uygun maddelerin kendisi (belge adı, madde, sayfa, yürürlük tarihi)
Cümleler önceden yazıldığı için çalışırken metin üretilmiyor, uydurma riski yok.

Güven skoru = (en yakın özet cümlesinin e5 benzerliği + 0.35 * ilk 3 parçanın en iyi e5 benzerliği) / 1.35
  - "bulundu"     : >= ESIK_YUKSEK, cevap olarak gösterilir
  - "belirsiz"    : arada, "kesin cevap bulamadım, ilgili olabilecek maddeler" denir
  - "bulunamadi"  : < ESIK_DUSUK, "bulamadım" denir

Önceden yalnızca parça benzerliğine bakılıyordu. Belge sayısı arttıkça her soruya benzeyen bir
parça çıkmaya başladı ve cevapsız soruların çoğu "bulundu" oldu. Özet cümleleri tek bir kurala
odaklandığı için cevaplı ve cevapsız soruları daha iyi ayırıyor (AUC 0.91 -> 0.95).
Eşikler tests/ altındaki sorularla seçildi, tests/cevapsiz_dogrulama.yaml ile ayrıca kontrol
edildi (raporlar/5_cevap.md).

    python cevap.py "Kaç AKTS üst sınırım var?"
"""
import hashlib
import json
import re
import sys

import numpy as np
import yaml

from belge_kontrol import bolum_ve_yil, ders_plani_mi, programlari_oku
from indeks import INDEKS_KLASORU, KLASOR, kelimeler, soru_kelimeleri, turkce_kucuk

ESIK_YUKSEK = 0.868
ESIK_DUSUK = 0.850
PARCA_AGIRLIGI = 0.35   # güven skorunda parça benzerliğinin özet benzerliğine göre ağırlığı
KAYNAK_SAYISI = 3
OZET_DOSYASI = KLASOR / "ozetler.yaml"
OZET_VEKTORLERI = INDEKS_KLASORU / "ozet_vektorleri.npz"
OZET_CUMLE_SAYISI = 3
KELIME_AGIRLIGI = 0.10   # degerlendir.py ile seçildi
SIRA_PAYI = 0.0
ILK_CUMLE_PAYI = 0.02   # her maddenin ilk cümlesi o maddenin genel özeti
MADDE_AGIRLIGI = 1.0    # maddenin bütününün soruya benzerliği
YAKINLIK = 0.015         # en iyi cümleye bu kadar yakın olanlar da gösterilir
# ders planından üretilen tek ders cümlesi ("... Benzetim (İST432) ...") ya da plan farkı cümlesi
TEK_DERS_CUMLESI = re.compile(r"\([A-ZÇĞİÖŞÜ]{2,6}SJ?\d{3,4}\) |planına göre")
ADAY_PARCA = 5           # cümleler en iyi 5 parçadan seçilir

_ozetler = None


def ozetleri_oku():
    global _ozetler
    if _ozetler is None:
        with open(OZET_DOSYASI, encoding="utf-8") as f:
            _ozetler = yaml.safe_load(f)
    return _ozetler

BELGE_KISA_ADI = {
    "yonetmelik": "Ön Lisans ve Lisans Eğitim-Öğretim ve Sınav Yönetmeliği",
    "fen_staj": "Fen Fakültesi Staj Yönergesi",
    "muh_staj": "Mühendislik Fakültesi Staj Yönergesi",
    "bbbf_staj": "Bilgisayar ve Bilişim Bilimleri Fakültesi Staj Yönergesi",
    "hubf_staj": "Havacılık ve Uzay Bilimleri Fakültesi Staj Yönergesi",
    "mtf_staj": "Mimarlık ve Tasarım Fakültesi Staj Yönergesi",
    "mtf_proje": "Mimarlık ve Tasarım Fakültesi Proje Dersleri Uygulama Yönergesi",
    "spor_staj": "Spor Bilimleri Fakültesi Staj Yönergesi",
    "myo_staj": "Meslek Yüksekokulları Staj ve İşletmede Mesleki Eğitim Yönergesi",
    "danismanlik": "Akademik Danışmanlık Yönergesi",
    "proje_temelli_staj": "Proje Temelli Staj Yönergesi",
    "hakli_nedenler": "Haklı ve Geçerli Nedenlere İlişkin Usul ve Esaslar",
    "tek_ders": "Tek Ders Sınavı Uygulama Esasları",
    "ek_sinav": "Ek Sınav Esasları",
    "yaz_okulu": "Yaz Okulu Uygulama Esasları",
    "not_karsiliklari": "Not Karşılıkları ve Eşdeğerlikler Uygulama Esasları",
}
PROGRAM_ADI = {p["id"]: p["ad"] for p in programlari_oku()[1]}
# önlisansta "bölüm" yerine "program" deniyor: "Lojistik programında", "Fizik bölümünde"
ONLISANS = {p["id"] for p in programlari_oku()[1]
            if (p.get("duzey") or programlari_oku()[0][p["fakulte"]].get("duzey")) == "onlisans"}


def bolum_eki(pid, ek):
    """bolum_eki("lojistik", "nda") -> "programında", bolum_eki("fizik", "nda") -> "bölümünde"."""
    kok = "program" if pid in ONLISANS else "bölüm"
    return kok + {"nda": "ında" if kok == "program" else "ünde",
                  "nun": "ının" if kok == "program" else "ünün",
                  "ndan": "ından" if kok == "program" else "ünden",
                  "": "ı" if kok == "program" else "ü"}[ek]
STAJ_MADDESI = {p["id"]: programlari_oku()[0][p["fakulte"]]["staj_maddesi"] for p in programlari_oku()[1]}


def program_id(p):
    """Bölüme ait parçaysa bölüm id'si (istatistik_ders_plani(_2024) -> istatistik), değilse None."""
    plan = ders_plani_mi(p["belge_id"])
    if plan:
        return plan[0]
    if p["belge_id"].endswith("_program_bilgileri"):
        return p["belge_id"][: -len("_program_bilgileri")]
    return None


def kisa_ad(p):
    """Atıflarda kullanılan kısa belge adı."""
    pid = program_id(p)
    if pid:
        plan = ders_plani_mi(p["belge_id"])
        if plan and plan[1]:
            return f"{PROGRAM_ADI[pid]} Bölümü {plan[1]}-{plan[1] + 1} Öğretim Yılı Ders Planı (bölüm sitesi)"
        tur = "Programı" if pid in ONLISANS else "Bölümü"
        return f"{PROGRAM_ADI[pid]} {tur} {'Ders Planı' if plan else 'Program Bilgileri'} (Bologna)"
    return BELGE_KISA_ADI.get(p["belge_id"], p["belge_adi"])


def tarih(t):
    if not t:
        return None
    y, a, g = t.split("-")
    return f"{g}.{a}.{y}"


def konum(p):
    """Madde 10 / 3. madde (bent) / EK-1 / Mezuniyet Koşulları gibi."""
    if p["tur"] == "madde":
        return f"Madde {p['no']}"
    if p["tur"] == "bent":
        return f"{p['no']}. madde"
    if p["tur"] == "giris":
        return "Giriş"
    if p["tur"] in ("ek", "kunye", "bolum"):
        return p["baslik"]
    return p["baslik"] or p["tur"]


def sayfa_metni(p):
    if not p["sayfa_bas"]:
        return None
    if p["sayfa_bas"] == p["sayfa_bit"]:
        return str(p["sayfa_bas"])
    return f"{p['sayfa_bas']}-{p['sayfa_bit']}"


def atif(p):
    """'Ön Lisans ve Lisans ... Yönetmeliği, Madde 10 (Kayıt yenileme ve ders kaydı), s. 3'"""
    metin = f"{kisa_ad(p)}, {konum(p)}"
    if p["baslik"] and p["tur"] == "madde":
        metin += f" ({p['baslik']})"
    if p["sayfa_bas"]:
        metin += f", s. {sayfa_metni(p)}"
    return metin


def gecerlilik(p):
    """Yürürlük / son değişiklik / erişim bilgisi."""
    if p["yururluk"]:
        metin = f"Yürürlük: {tarih(p['yururluk'])}"
        if p["son_degisiklik"]:
            metin += f", son değişiklik: {tarih(p['son_degisiklik'])}"
        return metin
    return f"Bologna web sayfası, erişim: {tarih(p.get('indirme_tarihi') or '2026-11-19')}"


def birimlere_bol(metin):
    """Parçayı fıkra/satır, çok uzun satırları cümle bazında birimlere böler."""
    birimler = []
    for satir in metin.split("\n"):
        if len(satir) <= 400:
            birimler.append(satir)
        else:
            # cümle sonları ve satır içindeki "(a)", "(b)" ya da "a)", "b)" bentleri
            birimler += [c for c in re.split(
                r"(?<=[.;:,])\s+(?=\(?[a-zçğıöşü]\)\s)|(?<=\.)\s+(?=[A-ZÇĞİÖŞÜ])", satir) if c]
    return [b.strip() for b in birimler if b.strip()]


def ilgili_kisim(p, soru, idf, en_fazla=2):
    """Parçadaki, soruyla en çok ortak (ağırlıklı) kelimesi olan 1-2 birimi seçer."""
    birimler = birimlere_bol(p["metin"])
    if len(birimler) <= en_fazla:
        return birimler
    sorudakiler = set(soru_kelimeleri(soru))
    sayi_soruluyor = bool(re.search(r"\bkaç|ne kadar|yüzde|en (az|çok|fazla)", soru.lower()))
    puanlar = []
    for i, b in enumerate(birimler):
        ortak = sorudakiler & set(kelimeler(b))
        puan = sum(idf.get(k, 0) for k in ortak)
        if sayi_soruluyor and re.search(r"\d", b):
            puan += 0.5
        puanlar.append((puan, -i))
    secilen = sorted(sorted(range(len(birimler)), key=lambda i: puanlar[i], reverse=True)[:en_fazla])
    if max(p_ for p_, _ in puanlar) <= 0:
        return birimler[:en_fazla]
    return [birimler[i] for i in secilen]


ROMA = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}


def akts(x):
    """'4.5' -> '4,5', '6.0' -> '6'"""
    x = float(x)
    return str(int(x)) if x == int(x) else str(x).replace(".", ",")


def ders_plani_ozeti(p):
    """Ders planı tablosundan özet cümleleri üretir (elle yazmak yerine, 30 bölüm var).
    Satırlar: 'KOD | Ad | Dil | T+U | AKTS', 'Seçmeli Dersler | 5.0', 'Toplam | 30'.
    Yarıyıl/havuz listesinin yanında her ders için ayrı bir cümle de var: "Benzetim kaç AKTS?" gibi
    tek ders sorularında uzun liste cümlesi soruya pek benzemiyordu."""
    bolum = PROGRAM_ADI[program_id(p)]
    yil = ders_plani_mi(p["belge_id"])[1]
    # yıllık planlarda cevap hangi plan olduğunu söylesin
    kim = (f"{bolum} {bolum_eki(program_id(p), 'nun')} {yil}-{yil + 1} ders planında" if yil
           else f"{bolum} {bolum_eki(program_id(p), 'nda')}")
    dersler, ekler, toplam = [], [], None
    for satir in p["metin"].split("\n"):
        h = [x.strip() for x in satir.split("|")]
        if len(h) == 5 and h[0] != "Ders Kodu":
            dersler.append((h[0], h[1], h[2], akts(h[4])))
        elif len(h) == 2 and h[0] == "Toplam":
            toplam = akts(h[1])
        elif len(h) == 2:
            ekler.append(f"{akts(h[1])} AKTS {h[0].lower().replace('dersler', 'ders')}")

    # aynı ders Türkçe ve İngilizce iki şube olarak açılabiliyor:
    # "Biyokimya II" ve "Biochemistry II (Biyokimya II)" -> "Biyokimya II (Türkçe ya da İngilizce)"
    turkce_adlar = {ad for _, ad, _, _ in dersler}
    listelenen, tekil = [], []
    for kod, ad, dil, kredi in dersler:
        ic = re.search(r"\(([^()]+)\)\s*$", ad)
        if ic and ic.group(1) in turkce_adlar:
            continue
        iki_dil = any(re.search(r"\(" + re.escape(ad) + r"\)\s*$", a) for _, a, _, _ in dersler)
        listelenen.append(f"{ad} ({'Türkçe ya da İngilizce, ' if iki_dil else ''}{kredi} AKTS)")
        tekil.append((kod, ad, "Türkçe ya da İngilizce" if iki_dil else dil, kredi))

    yariyil = ROMA.get(p["no"].replace(".YARIYIL", ""))
    if yariyil:
        cumleler = [f"{kim} {yariyil}. yarıyılın zorunlu dersleri şunlardır: {', '.join(listelenen)}."]
        if ekler or toplam:
            ek = f"ayrıca {' ve '.join(ekler)} alınır" if ekler else "seçmeli ders yoktur"
            cumleler.append(f"{kim} {yariyil}. yarıyılda {ek}"
                            + (f"; yarıyılın toplamı {toplam} AKTS'dir." if toplam else "."))
        donem = f"{(yariyil + 1) // 2}. sınıf {'güz' if yariyil % 2 else 'bahar'} dönemi"
        cumleler += [f"{kim} {ad} ({kod}) {yariyil}. yarıyılın ({donem}) zorunlu dersidir; {kredi} AKTS, {dil}."
                     for kod, ad, dil, kredi in tekil]
        return cumleler
    # seçmeli ders havuzları: uzun listeyi 10'arlı cümlelere böl
    havuz = p["no"].lower()
    cumleler = [f"{kim} {havuz} listesinde şunlar var: {', '.join(listelenen[i:i + 10])}."
                for i in range(0, len(listelenen), 10)]
    if "seçmeli" in havuz:
        cumleler += [f"{kim} {ad} ({kod}) zorunlu değil, {havuz} listesinde seçmeli bir derstir; {kredi} AKTS, {dil}."
                     for kod, ad, dil, kredi in tekil]
    else:
        cumleler += [f"{kim} {ad} ({kod}) dersi {p['no']} listesindedir; {kredi} AKTS, {dil}."
                     for kod, ad, dil, kredi in tekil]
    return cumleler


_parca_listesi = None


def parcalar_oku():
    global _parca_listesi
    if _parca_listesi is None:
        _parca_listesi = json.loads((INDEKS_KLASORU / "parcalar.json").read_text(encoding="utf-8"))
    return _parca_listesi


# Bologna "program hakkında" sayfalarındaki bazı bölümler çoğu programda kelimesi kelimesine aynı.
# Metin İstatistik'teki standart metinle aynıysa özet bu şablondan üretiliyor ({ad} = bölüm adı);
# farklıysa ozetler.yaml'da elle yazılmış olmalı (test kontrol ediyor).
STANDART_BOLUMLER = {
    "Kabul_ve_Kayıt_Koşulları": [
        "{ad} programına kabul için Türk ve yabancı öğrencilere yönelik genel kabul şartları geçerlidir."],
    "Yeterlilik_Koşulları_ve_Kuralları": [
        "{ad} programını tamamlamak için bütün dersleri geçmen, FF, DZ veya YZ notunun olmaması, "
        "en az 240 AKTS ve en az 2,00 GNO gerekir."],
    "Üst_Derece_Programlarına_Geçiş": [
        "{ad} mezunları her alanda yüksek lisans ve doktora programlarına başvurabilir."],
    "Mezuniyet_Koşulları": [
        "{ad} bölümünden mezun olmak için bütün derslerini geçmen, FF, DZ veya YZ notunun olmaması, "
        "en az 240 AKTS tamamlaman ve GNO'nun 4,00 üzerinden en az 2,00 olması gerekir."],
    "Ölçme_ve_Değerlendirme": [
        "Bologna sayfasına göre dönem içi değerlendirmelerin başarı notuna katkısı %30 ile %70 arasındadır; "
        "ancak güncel yönetmelikte üst sınır %60'tır.",
        "Harf notun, dersi alan öğrencilerin genel başarısı da dikkate alınarak belirlenir; "
        "AA 4,0'dan FF 0,0'a kadar katsayılar kullanılır.",
        "DZ devamsızlık notudur ve FF ya da YZ ile aynı sayılır; EK notu eksikler tamamlanmazsa FF veya YZ'ye dönüşür."],
    "Önceki_Öğrenmenin_Tanınması": [
        "Daha önce başka bir üniversitede okuduysan, kesin kayıttan sonra ilk hafta içinde başvurursan "
        "kredi ve not transferin bir defaya mahsus değerlendirilir.",
        "{ad} programında zorunlu İngilizce hazırlık vardır; yeterlik sınavından 100 üzerinden 70 alanlar "
        "ya da YDS, TOEFL gibi sınavlardan yeterli puanı olanlar muaf olur."],
}
STANDART_KAYNAK = "istatistik_program_bilgileri"


def standart_ozet(p, parcalar):
    """Standart metinli Bologna bölümü için şablon özet, değilse None."""
    bolum = p["id"].split("#bolum-")[-1]
    ref = parcalar.get(f"{STANDART_KAYNAK}#bolum-{bolum}")
    if bolum not in STANDART_BOLUMLER or not ref or ref["metin"] != p["metin"]:
        return None
    ad = PROGRAM_ADI[program_id(p)]
    return [c.format(ad=ad) for c in STANDART_BOLUMLER[bolum]]


def plan_dersleri(p):
    """Ders planı parçasındaki dersler: [(kod, ad, dil, akts), ...]. İki dilli adlarda
    ("Statistics I (İstatistik I)") parantez içindeki Türkçe ad alınıyor."""
    dersler = []
    for satir in p["metin"].split("\n"):
        h = [x.strip() for x in satir.split("|")]
        if len(h) != 5 or h[0] == "Ders Kodu":
            continue
        ic = re.search(r"\(([^()]+)\)\s*$", h[1])
        dersler.append((h[0], ic.group(1) if ic else h[1], h[2], akts(h[4])))
    return dersler


def dersleri_eslestir(eski, yeni):
    """İki plandaki dersleri eşleştirir: önce aynı kod, kalanlar Türkçe adla (kodlar yıllar arasında
    değişebiliyor: EMAT113 -> MAT1013; ad da değişebiliyor: İstatistik I -> Statistics I).
    Dönüş: {anahtar: (eski şubeler, yeni şubeler)}; bir tarafta yoksa boş liste."""
    def grupla(dersler, anahtar):
        g = {}
        for d in dersler:
            g.setdefault(anahtar(d), []).append(d)
        return g
    kod = lambda d: d[0]
    ad = lambda d: turkce_kucuk(re.sub(r"\s+", " ", d[1]))
    e_kod, y_kod = grupla(eski, kod), grupla(yeni, kod)
    sonuc = {k: (e_kod[k], y_kod[k]) for k in sorted(e_kod.keys() & y_kod.keys())}
    e_kalan = grupla([d for d in eski if d[0] not in sonuc], ad)
    y_kalan = grupla([d for d in yeni if d[0] not in sonuc], ad)
    for k in sorted(e_kalan.keys() | y_kalan.keys()):
        sonuc["ad:" + k] = (e_kalan.get(k, []), y_kalan.get(k, []))
    return sonuc


def plan_farki_cumleleri(p, parcalar):
    """Yıllık plan parçası için bir önceki yılın aynı parçasına göre değişiklikler (otomatik)."""
    plan = ders_plani_mi(p["belge_id"])
    if not plan or not plan[1]:
        return []
    onceki = parcalar.get(p["id"].replace(f"_ders_plani_{plan[1]}#", f"_ders_plani_{plan[1] - 1}#"))
    if not onceki:
        return []
    bolum = PROGRAM_ADI[plan[0]]
    yer = ROMA.get(p["no"].replace(".YARIYIL", ""))
    yer = f"{yer}. yarıyılda" if yer else f"{p['no'].lower()} listesinde"
    donem = f"{plan[1]}-{plan[1] + 1} ders planında, {plan[1] - 1}-{plan[1]} planına göre"
    eklenen, cikan, degisenler = [], [], []
    for e, y in dersleri_eslestir(plan_dersleri(onceki), plan_dersleri(p)).values():
        if not e:
            eklenen.append(y[0][1])
            continue
        if not y:
            cikan.append(e[0][1])
            continue
        degisen = []
        if e[0][1] != y[0][1]:
            degisen.append(f"adı {e[0][1]} iken {y[0][1]}")
        if e[0][3] != y[0][3]:
            degisen.append(f"AKTS'si {e[0][3]} iken {y[0][3]}")
        e_dil, y_dil = sorted({d[2] for d in e}), sorted({d[2] for d in y})
        if e_dil != y_dil:
            degisen.append(f"dili {' ya da '.join(e_dil)} iken {' ya da '.join(y_dil)}")
        if e[0][0] != y[0][0]:
            degisen.append(f"kodu {e[0][0]} iken {y[0][0]}")
        if degisen:
            degisenler.append(f"{bolum} bölümünün {donem} {e[0][1]} dersinin {', '.join(degisen)} oldu.")
    cumleler = []
    if eklenen:
        cumleler.append(f"{bolum} bölümünün {donem} {yer} yeni eklenen dersler: {', '.join(eklenen)}.")
    if cikan:
        cumleler.append(f"{bolum} bölümünün {donem} {yer} çıkarılan (kaldırılan) dersler: {', '.join(cikan)}.")
    cumleler += degisenler
    # zorunlu derslerin genel durumu tek cümle, 1. yarıyıl parçasında (her yarıyıla yazınca
    # "değişiklik yok" cümleleri her değişiklik sorusunda öne çıkıyordu)
    if p["no"] == "I.YARIYIL":
        yeni_ok = eski_ok = 0
        for no in ROMA:
            y_p = parcalar.get(p["id"].replace("#bolum-I.YARIYIL", f"#bolum-{no}.YARIYIL"))
            e_p = parcalar.get(onceki["id"].replace("#bolum-I.YARIYIL", f"#bolum-{no}.YARIYIL"))
            if y_p and e_p:
                for e, y in dersleri_eslestir(plan_dersleri(e_p), plan_dersleri(y_p)).values():
                    yeni_ok += not e
                    eski_ok += not y
        if yeni_ok == eski_ok == 0:
            cumleler.append(f"{bolum} bölümünün {donem} zorunlu derslere ders eklenmedi ya da çıkarılmadı; "
                            "yarıyılları ve AKTS'leri aynı, değişenler sadece bazı derslerin kodu, adı ya da dili.")
    return cumleler


def dil_cumlesi(p, parcalar):
    """"Eğitim dili nedir?" sorusu için: zorunlu derslerin kaçı Türkçe, kaçı İngilizce.
    Program bilgileri sayfasında dil yazmıyor, ders planındaki Dil sütunundan sayılıyor.
    Cümle her planın sadece 1. yarıyıl parçasına ekleniyor (her yarıyılda tekrar etmesin)."""
    if p["no"] != "I.YARIYIL":
        return []
    dersler = []
    for q in parcalar.values():
        if q["belge_id"] == p["belge_id"] and q["no"].endswith(".YARIYIL"):
            for satir in q["metin"].split("\n"):
                h = [x.strip() for x in satir.split("|")]
                if len(h) == 5 and h[0] != "Ders Kodu":
                    dersler.append((h[1], h[2]))
    adlar = {ad for ad, _ in dersler}
    # Türkçe şubesi olan İngilizce dersler ("Biochemistry II (Biyokimya II)") ayrıca sayılmasın
    dersler = [(ad, dil) for ad, dil in dersler
               if not (re.search(r"\(([^()]+)\)\s*$", ad) and re.search(r"\(([^()]+)\)\s*$", ad).group(1) in adlar)]
    if not dersler:
        return []
    # "İngilizce I" gibi yabancı dil dersleri eğitim dilini göstermez, ayrı söylenir
    dil_dersi = lambda ad: ad.startswith(("İngilizce", "English", "Yabancı Dil", "İNGİLİZCE"))
    ingilizce = [ad for ad, dil in dersler if dil == "İngilizce" and not dil_dersi(ad)]
    haric = " (İngilizce dil dersleri hariç)" if any(dil_dersi(ad) for ad, _ in dersler) else ""
    pid = program_id(p)
    kim = f"{PROGRAM_ADI[pid]} {bolum_eki(pid, 'nda')}"
    n, m = len(dersler), len(ingilizce)
    # bölümün Bologna tanıtımında dil yazıyorsa ("eğitim dili %30 İngilizcedir") o esas
    profil = parcalar.get(f"{pid}_program_bilgileri#bolum-Program_Profili", {}).get("metin", "")
    resmi = re.search(r"(?:eğitim|öğretim) dili\s*%\s*\u2060?(\d+)\s*(İngilizce|Türkçe)", profil, re.I) \
        or re.search(r"%\s*(\d+)\s*(İngilizce|Türkçe) [Ee]ğitim", profil)
    if resmi:
        dil = f"%{resmi.group(1)} {resmi.group(2)}"
    elif re.search(r"(?:eğitim|öğretim) dili (İngilizce|Türkçe)", profil, re.I):
        dil = re.search(r"(?:eğitim|öğretim) dili (İngilizce|Türkçe)", profil, re.I).group(1)
    else:
        dil = None
    if dil:
        ayrinti = (f"ders planındaki {n} zorunlu dersin {m} tanesi İngilizce okutulur (ör. {', '.join(ingilizce[:3])})."
                   if m else f"ders planındaki zorunlu derslerin hepsi{haric} Türkçe okutulur.")
        return [f"{kim} eğitim dili {dil}dir (bölümün Bologna tanıtım sayfasına göre).",
                f"{kim} {ayrinti}"]
    # kısa cümle soruya daha çok benziyor; ayrıntı ikinci cümlede
    if m == 0:
        return [f"{kim} eğitim dili Türkçedir.",
                f"{kim} ders planındaki zorunlu derslerin hepsi{haric} Türkçe okutulur."]
    if m / n > 0.7:
        agirlik = "İngilizcedir"
    elif m / n < 0.3:
        agirlik = "Türkçedir"
    else:
        agirlik = "Türkçe ve İngilizcedir"
    return [f"{kim} eğitim dili ağırlıklı olarak {agirlik}.",
            f"{kim} ders planındaki {n} zorunlu dersin {m} tanesi İngilizce okutulur "
            f"(ör. {', '.join(ingilizce[:3])})."]


def tum_ozetler():
    """ozetler.yaml + ders planlarından ve standart Bologna metinlerinden üretilen özetler."""
    ozetler = dict(ozetleri_oku())
    parcalar = {p["id"]: p for p in parcalar_oku()}
    for p in parcalar.values():
        if p["id"] in ozetler:
            continue
        if ders_plani_mi(p["belge_id"]):
            ozetler[p["id"]] = (ders_plani_ozeti(p) + dil_cumlesi(p, parcalar)
                                  + plan_farki_cumleleri(p, parcalar))
        elif p["belge_id"].endswith("_program_bilgileri"):
            sablon = standart_ozet(p, parcalar) or alinti_ozeti(p)
            if sablon:
                ozetler[p["id"]] = sablon
    return ozetler


def alinti_ozeti(p, sinir=320):
    """Elle özeti olmayan Bologna bölümü için metnin ilk cümleleri (önlisans programlarının 184 bölümü
    için elle yazmak yerine). Kaynak metinden aynen alındığı için yanlış bilgi eklemiyor; başa program
    adı ekleniyor ki "Mezuniyet için kaç AKTS?" gibi sorularda hangi programın cümlesi olduğu belli olsun."""
    metin = re.sub(r"\s+", " ", p["metin"]).strip()
    if not metin:
        return []
    cumleler = [c.strip() for c in re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])", metin) if len(c.strip()) > 15]
    secilen, uzunluk = [], 0
    for c in cumleler:
        if secilen and uzunluk + len(c) > sinir:
            break
        secilen.append(c)
        uzunluk += len(c)
    ad = PROGRAM_ADI[program_id(p)]
    return [f"{ad} ({p['no']}): {secilen[0]}"] + secilen[1:3] if secilen else []


def bolum_staj_cumleleri():
    """Bölüme özel staj cümleleri: [(parça id, cümle, bölüm id), ...].
    Staj yönergesindeki kural genel ("en az 20 iş günü"), hangi bölümde zorunlu olduğu ekteki bir
    notta. Bölüm seçiliyken doğru cevabı vermek için her bölüme kendi cümlesi, o notun parçasına bağlı.
    Bilgi programlar.yaml'dan (staj_gunu), o da yönergenin notundan alındı; testte karşılaştırılıyor."""
    fakulteler, programlar = programlari_oku()
    sonuc = []
    for p in programlar:
        fak = fakulteler[p["fakulte"]]
        parca_id = p.get("staj_kaynagi") or fak["staj_listesi"]
        birim = p.get("staj_birimi") or fak["staj_birimi"]
        if p.get("staj_cumlesi"):               # bölüme özel elle yazılmış cümle
            c = p["staj_cumlesi"]
        elif p.get("staj_durumu_belirsiz"):
            c = f"{p['ad']} {bolum_eki(p['id'], 'nda')} staj zorunlu mu, belgelerden net anlaşılmıyor. {p['staj_ek']}"
        elif p.get("staj_suresi_belirsiz"):
            c = f"{p['ad']} {bolum_eki(p['id'], 'nda')} staj zorunludur. {p['staj_ek']}"
        elif p["staj_gunu"]:
            c = (f"{p['ad']} {bolum_eki(p['id'], 'nda')} staj zorunludur; mezun olmak için toplam en az {p['staj_gunu']} {birim} "
                 "staj yapman gerekir." + (f" {p['staj_ek']}" if p.get("staj_ek") else ""))
        else:
            c = (f"{p['ad']} {bolum_eki(p['id'], 'nda')} staj zorunlu değildir, isteğe bağlıdır; mezuniyet için staj şartı yok."
                 + (f" {p['staj_ek']}" if p.get("staj_ek") else ""))
        sonuc.append((parca_id, c, p["id"]))
    return sonuc


PTS_PAYI = 0.05


def egitim_dili_soruluyor(soru):
    """"Eğitim dili nedir?", "Bölüm İngilizce mi?", "Dersler hangi dilde?" gibi sorular.
    Cevap ders planının Dil sütunundan üretilen cümlede (dil_cumlesi); anlam benzerliği bu kısa
    soruları yönetmeliğin genel maddelerine kaçırdığı için kurala dayalı tanınıyor."""
    s = turkce_kucuk(soru)
    if re.search(r"hazırlık|muaf|sınav|yabancı dil dersi|zorunlu (mu|mı)|hangi dönem|kaç akts", s):
        return False
    return bool(re.search(r"(eğitim|öğretim|ders) dil|hangi dilde|(bölüm|program|dersler)\w* (tamamen )?(ingilizce|türkçe) m[ıi]|"
                          r"(yüzde|%) ?\d* ?ingilizce|ingilizce (eğitim|öğretim)|türkçe (eğitim|öğretim)", s))


def dil_parcasi(program):
    """Bölümün güncel ders planında dil cümlesinin bulunduğu parça (1. yarıyıl)."""
    bolum, yil = bolum_ve_yil(program)
    return f"{bolum}_ders_plani{f'_{yil}' if yil else ''}#bolum-I.YARIYIL"


DERS_SORUSU = re.compile(r"hangi (dönem|yarıyıl|sınıf|yıl)|kaçıncı|kaç akts|akts(si)? kaç|zorunlu m|seçmeli m|"
                         r"dersi var m|hangi dilde|kodu ne")
ROMA_KELIME = {"ii", "iii", "iv", "vi", "vii", "viii"}


def sorulan_ders_cumleleri(soru, program):
    """Soru seçili bölümün ders planındaki bir dersi adıyla (ya da koduyla) soruyorsa o dersin
    tek ders cümleleri ("... 5. yarıyılın zorunlu dersidir; 6 AKTS, Türkçe."). Ders adının ilk iki
    kelimesi (5 harflik kökleriyle) soruda geçmeli; soru da dönem/AKTS/zorunluluk sormalı.
    Anlam benzerliği bu cümleleri doğru buluyor ama güven skoru eşiğin hemen altında kalıyordu."""
    if program in (None, "genel"):
        return []
    s = turkce_kucuk(soru)
    kodlar = {k.replace(" ", "") for k in re.findall(r"[a-zçğıöşü]{2,4} ?\d{3}", s)}
    if not (DERS_SORUSU.search(s) or kodlar):
        return []
    bolum, yil = bolum_ve_yil(program)
    plan = f"{bolum}_ders_plani{f'_{yil}' if yil else ''}#"
    sorudaki = set(kelimeler(soru))
    bulunan = []
    for pid, i, c in ozet_cumleleri():
        if not pid.startswith(plan):
            continue
        m = re.search(r"(?:nda|nde) ([^;]+?) \(([A-ZÇĞİÖŞÜ]{2,6}(?:SJ)?\d{3,4})\) ", c)
        if not m:
            continue
        ad = re.sub(r"\([^()]*\)", " ", m.group(1))
        if "SJ" in m.group(2) or turkce_kucuk(ad).startswith("staj"):
            continue      # staj sorularının kendi kuralı var (yönerge maddesi + bölüm cümlesi)
        kokler = [k for k in kelimeler(ad) if k not in ROMA_KELIME and not k.isdigit()]
        if turkce_kucuk(m.group(2)) in kodlar or (kokler and set(kokler[:2]) <= sorudaki):
            bulunan.append((pid, c))
    return bulunan


# Bologna program sayfasının bölümleri için kurala dayalı niyetler: (soru deseni, bölüm, sadece önlisans mı).
# Bu sorular kısa ve genel olduğu için anlam benzerliği yönetmeliğin genel maddelerine kayıyordu.
BOLUM_NIYETLERI = [
    (r"dikey geçiş|\bdgs\b|lisans tamamla|lisansa geç", "Üst_Derece_Programlarına_Geçiş", True),
    (r"(yüksek lisans|doktora|lisansüstü)\w* (yapabilir|başvur|okuyabilir|devam ed)|üst derece", "Üst_Derece_Programlarına_Geçiş", False),
    (r"iş imkan|istihdam|nerede çalış|nerelerde çalış|ne iş yap|iş bul|iş olanak|kariyer imkan", "İstihdam_Olanakları", False),
]


def sorulan_program_bolumu(soru, program):
    """Soru bölümün Bologna sayfasındaki bir başlığı soruyorsa o parçanın id'si, yoksa None."""
    if program in (None, "genel"):
        return None
    s = turkce_kucuk(soru)
    if re.search(r"maaş|ücret|kazan|yatay", s):     # belgelerde yok / başka kural
        return None
    bolum, _ = bolum_ve_yil(program)
    for desen, baslik, sadece_onlisans in BOLUM_NIYETLERI:
        if re.search(desen, s) and (not sadece_onlisans or bolum in ONLISANS):
            return f"{bolum}_program_bilgileri#bolum-{baslik}"
    return None


def one_al(tum, pid, arayici, soru, program, yer=0):
    """Aday listesinde pid'li parçayı verilen sıraya koyar. Parça bu bölümün alt kümesinde yoksa
    listeyi değiştirmeden döner; ikinci değer parçanın eklenip eklenmediği."""
    sira = {p["id"]: i for i, p in enumerate(arayici.parcalar)}
    alt = list(arayici.alt_kume(program)[0])
    if pid not in sira or sira[pid] not in alt:
        return tum, False
    e5 = arayici.e5_skorlari(soru, program)
    bilgi = {"e5": float(e5[alt.index(sira[pid])]), "bm25": 0.0}
    digerleri = [x for x in tum if x[0]["id"] != pid]
    return digerleri[:yer] + [(arayici.parcalar[sira[pid]], bilgi)] + digerleri[yer:], True


def staj_suresi_soruluyor(soru):
    """Soru stajın süresini ya da zorunlu olup olmadığını mı soruyor? (diğer staj konuları değil)"""
    s = turkce_kucuk(soru)
    return ("staj" in s and bool(re.search(r"kaç|ne kadar|süre|zorunlu|zorunda|gerek|lazım|şart", s))
            and not re.search(r"proje temelli|proje tabanl|pts|önlisans|yarıyıl|dönem|sınıf|itiraz|başvur|ne zaman|nerede|değiş|muaf|sigorta|rapor|"
                              r"devamsız|not|puan|başarı|değerlendir|yeri|yerin|yetkin|sorumlu", s))


BOLUM_STAJ_CUMLESI = {}
for _pid, _c, _b in bolum_staj_cumleleri():
    BOLUM_STAJ_CUMLESI.setdefault(_b, set()).add(_c)


def ozet_cumleleri():
    """[(parça id, cümle no, cümle), ...]  Bölüme özel cümleler en sonda, cümle no'ları 0."""
    genel = [(pid, i, c) for pid, cumleler in tum_ozetler().items() for i, c in enumerate(cumleler)]
    return genel + [(pid, 0, c) for pid, c, _ in bolum_staj_cumleleri()]


def ozet_bolumleri():
    """ozet_cumleleri() ile aynı sırada: cümle sadece bir bölüm içinse o bölümün id'si, yoksa None."""
    genel = sum(len(v) for v in tum_ozetler().values())
    return [None] * genel + [b for _, _, b in bolum_staj_cumleleri()]


def cumle_gecerli_mi(bolum, program):
    return bolum is None or bolum == bolum_ve_yil(program)[0]


def ozet_indeksi_olustur(gomucu):
    """Özet cümlelerinin e5 vektörlerini indeks/ klasörüne kaydeder (özetler değişince yeniden çalıştır)."""
    cumleler = ozet_cumleleri()
    vektorler = gomucu.vektor([c for _, _, c in cumleler], "passage")
    np.savez(OZET_VEKTORLERI, vektorler=vektorler, ozet_hash=ozet_hash())
    return len(cumleler)


def dosya_hash(yol):
    return hashlib.sha256(open(yol, "rb").read()).hexdigest()


def ozet_hash():
    """Özet cümleleri hem ozetler.yaml'a hem parçalara (otomatik ders planı özetleri) bağlı."""
    return hashlib.sha256("\n".join(c for _, _, c in ozet_cumleleri()).encode("utf-8")).hexdigest()


_ozet_vektorleri = None


def ozet_vektorleri(gomucu):
    global _ozet_vektorleri
    if _ozet_vektorleri is None:
        if not OZET_VEKTORLERI.exists() or str(np.load(OZET_VEKTORLERI)["ozet_hash"]) != ozet_hash():
            print("özetler değişmiş, özet vektörleri yeniden hesaplanıyor...")
            ozet_indeksi_olustur(gomucu)
        _ozet_vektorleri = np.load(OZET_VEKTORLERI)["vektorler"]
    return _ozet_vektorleri


def benzer_mi(a, b):
    """İki cümle aynı şeyi mi söylüyor? (farklı belgelerde aynı kural tekrar ediyor)"""
    ka, kb = set(kelimeler(a)), set(kelimeler(b))
    return len(ka & kb) / max(1, min(len(ka), len(kb))) >= 0.6


def kisa_cevap(soru, sonuclar, arayici, en_fazla=OZET_CUMLE_SAYISI, agirlik=None, program=None):
    """En iyi 3 parçanın özet cümlelerinden soruya en uygun 1-3 tanesini seçip paragraf yapar.
    Cümle puanı = e5 benzerliği + kelime örtüşmesi (idf ağırlıklı, 0-1 arası) * KELIME_AGIRLIGI
                  + parçanın arama sırasına göre küçük bir pay. En iyi cümle başa yazılır."""
    anahtar = program                       # arama için "istatistik@2024" gibi yıllı anahtar
    program = bolum_ve_yil(program)[0]      # bölüme özel cümleler için sadece bölüm
    kelime_agirligi, sira_payi, ilk_payi, madde_agirligi = agirlik or (
        KELIME_AGIRLIGI, SIRA_PAYI, ILK_CUMLE_PAYI, MADDE_AGIRLIGI)
    cumleler = ozet_cumleleri()
    bolumler = ozet_bolumleri()
    vektorler = ozet_vektorleri(arayici.gomucu)
    q = arayici.soru_vektoru(soru)
    idf = arayici.bm25_icin(anahtar).idf
    sorudakiler = set(soru_kelimeleri(soru))
    toplam_idf = sum(idf.get(k, 0) for k in sorudakiler) or 1

    e5 = {}
    if program not in (None, "genel"):
        alt = arayici.alt_kume(anahtar)[0]
        e5 = dict(zip((arayici.parcalar[x]["id"] for x in alt), arayici.e5_skorlari(soru, anahtar)))

    def madde_benzerligi(pid, j, varsayilan):
        # bölüme özel staj cümlesi, fakültenin staj maddesinin bölüme özel hali: o maddenin
        # benzerliğinden aşağı sayılmasın (cümle bazen bir form ekine ya da Bologna sayfasına bağlı)
        if bolumler[j] == program and program in STAJ_MADDESI:
            return max(varsayilan, e5.get(STAJ_MADDESI[program], varsayilan))
        # ders planı parçası onlarca dersin listesi; tek bir dersin cümlesini o uzun listenin
        # benzerliğiyle cezalandırmamak için cümlenin kendi benzerliği kullanılıyor
        if ders_plani_mi(pid.split("#")[0]) and TEK_DERS_CUMLESI.search(cumleler[j][2]):
            return max(varsayilan, float(vektorler[j] @ q))
        return varsayilan

    adaylar = []
    for sira, (p, b) in enumerate(sonuclar[:ADAY_PARCA]):
        for j, (pid, i, c) in enumerate(cumleler):
            if pid != p["id"] or not cumle_gecerli_mi(bolumler[j], program):
                continue
            ortak = sum(idf.get(k, 0) for k in sorudakiler & set(kelimeler(c))) / toplam_idf
            puan = (float(vektorler[j] @ q) + kelime_agirligi * ortak - sira_payi * sira
                    + (ilk_payi if i == 0 else 0) + madde_agirligi * madde_benzerligi(pid, j, b["e5"]))
            adaylar.append((puan, sira, i, c, p))

    # Seçili bölümün kendi staj cümlesi, bağlı olduğu madde ilk 5'te olmasa da aday
    # (Endüstri'de süre Bologna sayfasında yazıyor, o sayfa "kaç gün staj" sorusunda üste çıkmıyor).
    secilenler = {p["id"] for p, _ in sonuclar[:ADAY_PARCA]}
    if program not in (None, "genel"):
        for j, (pid, i, c) in enumerate(cumleler):
            if bolumler[j] != program or pid in secilenler:
                continue
            p = next(x for x in arayici.parcalar if x["id"] == pid)
            ortak = sum(idf.get(k, 0) for k in sorudakiler & set(kelimeler(c))) / toplam_idf
            puan = (float(vektorler[j] @ q) + kelime_agirligi * ortak - sira_payi * ADAY_PARCA
                    + ilk_payi + madde_agirligi * madde_benzerligi(pid, j, e5[pid]))
            adaylar.append((puan, ADAY_PARCA, i, c, p))
    if not adaylar:
        return None

    # "kaç gün staj", "staj zorunlu mu" gibi sorularda bölümün staj cümlesi doğrudan cevap
    if staj_suresi_soruluyor(soru) and program not in (None, "genel"):
        adaylar = [(a[0] + 1.0, *a[1:]) if a[3] in BOLUM_STAJ_CUMLESI.get(program, ()) else a for a in adaylar]

    # Proje Temelli Staj yönergesi genel kapsamlı; soru PTS'yi sormuyorsa onun cümleleri
    # fakültenin normal staj kuralının önüne geçmesin ("stajda devamsızlık hakkım" gibi)
    if not re.search(r"proje|pts", turkce_kucuk(soru)):
        adaylar = [(a[0] - PTS_PAYI, *a[1:]) if a[4]["belge_id"] == "proje_temelli_staj" else a for a in adaylar]

    if egitim_dili_soruluyor(soru) and program not in (None, "genel"):
        # iki cümle birlikte gelsin: önce dil, sonra ayrıntı (puanlar sabitleniyor)
        adaylar = [(10.0 if "eğitim dili" in a[3] else 9.99, *a[1:]) if a[4]["id"] == dil_parcasi(program)
                   and ("eğitim dili" in a[3] or "okutulur" in a[3]) else a for a in adaylar]

    bolum_parcasi = sorulan_program_bolumu(soru, program)
    if bolum_parcasi:
        adaylar = [(a[0] + 1.0, *a[1:]) if a[4]["id"] == bolum_parcasi else a for a in adaylar]

    ders_cumleleri = {c for _, c in sorulan_ders_cumleleri(soru, program)}
    if ders_cumleleri:
        adaylar = [(a[0] + 1.0, *a[1:]) if a[3] in ders_cumleleri else a for a in adaylar]

    yariyil = sorulan_yariyil(soru)
    if yariyil:
        hedef = f"#bolum-{ROMA_RAKAM[yariyil - 1]}.YARIYIL"
        adaylar = [(a[0] + 0.05, *a[1:]) if a[4]["id"].endswith(hedef) else a for a in adaylar]

    adaylar.sort(key=lambda x: -x[0])
    en_iyi = adaylar[0][0]
    secilen = []
    for a in adaylar:
        if len(secilen) == en_fazla or a[0] < en_iyi - YAKINLIK:
            break
        if not any(benzer_mi(a[3], s[3]) for s in secilen):
            secilen.append(a)

    kullanilan = []
    for x in secilen:
        if x[4]["id"] not in [p["id"] for p in kullanilan]:
            kullanilan.append(x[4])
    return {
        "metin": " ".join(x[3] for x in secilen),
        "cumleler": [x[3] for x in secilen],
        "parcalar": [p["id"] for p in kullanilan],
        "ilk_parca": secilen[0][4]["id"],
        "dayanak": [f"{kisa_ad(p)}, {konum(p)}" for p in kullanilan],
    }


SIRA_SOZCUGU = {"birinci": 1, "ilk": 1, "ikinci": 2, "üçüncü": 3, "dördüncü": 4, "beşinci": 5,
                "altıncı": 6, "yedinci": 7, "sekizinci": 8}
ROMA_RAKAM = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def sorulan_yariyil(soru):
    """"Birinci yarıyılın dersleri", "3. dönem", "5.yarıyıl" -> yarıyıl numarası; yoksa None.
    "1. sınıf" yarıyıl değil (iki yarıyıl), ona karışmıyoruz."""
    s = turkce_kucuk(soru)
    m = re.search(r"\b([1-8])\s*\.?\s*(?:yarıyıl|dönem)", s)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(" + "|".join(SIRA_SOZCUGU) + r")\s+(?:yarıyıl|dönem)", s)
    return SIRA_SOZCUGU[m.group(1)] if m else None


def guven_skoru(soru, sonuclar, arayici, program=None):
    """Özet cümlesi benzerliği ile parça benzerliğinin ağırlıklı ortalaması (0-1 arası)."""
    parca = max(b["e5"] for _, b in sonuclar)
    ozet = float(arayici.ozet_skorlari(soru, program).max())
    return (ozet + PARCA_AGIRLIGI * parca) / (1 + PARCA_AGIRLIGI)


def cevapla(soru, arayici, k=KAYNAK_SAYISI, program=None):
    soru = soru.strip()
    if len(soru) < 3:
        return {"durum": "bulunamadi", "mesaj": "Lütfen bir soru yazın.", "kaynaklar": []}

    tum = arayici.ara(soru, k=max(k, ADAY_PARCA), program=program)
    # soruya en çok benzeyen özet cümlesinin parçası ilk 5'te değilse yine de aday olsun: tek ders
    # sorularında ("Benzetim kaç AKTS?") dersin cümlesi çok yakın ama uzun ders listesi parçası
    # aramada yönetmelik maddelerinin gerisinde kalıyor
    alt = arayici.alt_kume(program)[0]
    oz = arayici.ozet_skorlari(soru, program)
    en_yakin = arayici.parcalar[alt[int(np.argmax(oz))]]
    if en_yakin["id"] not in {p["id"] for p, _ in tum[:ADAY_PARCA]}:
        e5 = float(arayici.e5_skorlari(soru, program)[int(np.argmax(oz))])
        tum = tum[:ADAY_PARCA - 1] + [(en_yakin, {"e5": e5, "bm25": 0.0})] + tum[ADAY_PARCA - 1:]
    # soru belli bir yarıyılı soruyorsa ("birinci yarıyılın dersleri") o yarıyılın ders planı
    # parçası en başa: anlam benzerliği yarıyıl numarasını iyi ayırt etmiyor (1. ile 3. yarıyıl
    # listeleri birbirine çok benziyor)
    yariyil = sorulan_yariyil(soru)
    if yariyil and program not in (None, "genel"):
        bolum, yil = bolum_ve_yil(program)
        hedef = f"{bolum}_ders_plani{f'_{yil}' if yil else ''}#bolum-{ROMA_RAKAM[yariyil - 1]}.YARIYIL"
        sira = {p["id"]: i for i, p in enumerate(arayici.parcalar)}
        if hedef in sira:
            e5 = arayici.e5_skorlari(soru, program)
            alt = list(arayici.alt_kume(program)[0])
            bilgi = {"e5": float(e5[alt.index(sira[hedef])]), "bm25": 0.0}
            tum = [(arayici.parcalar[sira[hedef]], bilgi)] + [x for x in tum if x[0]["id"] != hedef]
    # eğitim dili: cevap her zaman bölümün ders planından üretilen cümle, parça en başa
    dil_sorusu = egitim_dili_soruluyor(soru) and program not in (None, "genel")
    if dil_sorusu:
        hedef = dil_parcasi(program)
        sira = {p["id"]: i for i, p in enumerate(arayici.parcalar)}
        if hedef in sira:
            e5 = arayici.e5_skorlari(soru, program)
            alt = list(arayici.alt_kume(program)[0])
            bilgi = {"e5": float(e5[alt.index(sira[hedef])]), "bm25": 0.0}
            tum = [(arayici.parcalar[sira[hedef]], bilgi)] + [x for x in tum if x[0]["id"] != hedef]
            # cümle Bologna tanıtımındaki ifadeye dayanıyorsa o sayfa da ikinci kaynak
            profil = f"{bolum_ve_yil(program)[0]}_program_bilgileri#bolum-Program_Profili"
            if profil in sira and sira[profil] in alt:
                bilgi = {"e5": float(e5[alt.index(sira[profil])]), "bm25": 0.0}
                tum = tum[:1] + [(arayici.parcalar[sira[profil]], bilgi)] + [x for x in tum[1:] if x[0]["id"] != profil]
        else:
            dil_sorusu = False
    # soru plandaki bir dersi adıyla soruyorsa dersin parçaları aday olsun (en çok 3)
    ders_parcalari = list(dict.fromkeys(pid for pid, _ in sorulan_ders_cumleleri(soru, program)))[:3]
    if ders_parcalari:
        sira = {p["id"]: i for i, p in enumerate(arayici.parcalar)}
        e5 = arayici.e5_skorlari(soru, program)
        alt = list(arayici.alt_kume(program)[0])
        onde = [(arayici.parcalar[sira[pid]], {"e5": float(e5[alt.index(sira[pid])]), "bm25": 0.0})
                for pid in ders_parcalari if pid in sira and sira[pid] in alt]
        ids = {p["id"] for p, _ in onde}
        tum = onde + [x for x in tum if x[0]["id"] not in ids]
    bolum_parcasi = sorulan_program_bolumu(soru, program)
    if bolum_parcasi:
        tum, eklendi = one_al(tum, bolum_parcasi, arayici, soru, program)
        bolum_parcasi = bolum_parcasi if eklendi else None
    sonuclar = tum[:k]
    en_iyi = guven_skoru(soru, sonuclar, arayici, program)
    if dil_sorusu or ders_parcalari or bolum_parcasi:
        en_iyi = max(en_iyi, ESIK_YUKSEK)
    if en_iyi >= ESIK_YUKSEK:
        durum = "bulundu"
        mesaj = "Kısa cevap aşağıda. Dayandığı resmi maddeler altında, aynen gösteriliyor."
    elif en_iyi >= ESIK_DUSUK:
        durum = "belirsiz"
        mesaj = ("Bu soruya belgelerde kesin bir cevap bulamadım. "
                 "İlgili olabilecek maddeler aşağıda, lütfen kontrol edin.")
    else:
        durum = "bulunamadi"
        mesaj = ("Bu sorunun cevabını eklenen resmi belgelerde bulamadım. "
                 "Öğrenci İşleri'ne ya da akademik danışmanınıza sorabilirsiniz.")

    kaynaklar = []
    ozet = kisa_cevap(soru, tum, arayici, program=program) if durum != "bulunamadi" else None
    if durum != "bulunamadi":
        # kısa cevabın dayandığı parça ilk k'nın dışındaysa o da kaynaklara eklenir
        ekler = [(p, b) for p, b in tum[k:] if p["id"] in ozet["parcalar"]]
        gosterilen = {p["id"] for p, _ in sonuclar + ekler}
        for pid in ozet["parcalar"]:      # bölüme özel staj cümlesinin maddesi aramada çıkmamış olabilir
            if pid not in gosterilen:
                p = next(x for x in arayici.parcalar if x["id"] == pid)
                ekler.append((p, {"e5": float("nan")}))
        for p, b in sonuclar + ekler:
            kaynaklar.append({
                "id": p["id"],
                "atif": atif(p),
                "belge": kisa_ad(p),
                "konum": konum(p),
                "baslik": p["baslik"] if p["tur"] == "madde" else None,
                "sayfa": sayfa_metni(p),
                "gecerlilik": gecerlilik(p),
                "alinti": ilgili_kisim(p, soru, arayici.bm25_icin(program).idf),
                "tam_metin": p["metin"],
                "url": p["url"],
                "ocr": p["ocr"],
                "benzerlik": round(b["e5"], 3),
            })
    return {"durum": durum, "mesaj": mesaj, "ozet": ozet, "kaynaklar": kaynaklar,
            "en_iyi_benzerlik": round(en_iyi, 3)}


def yazdir(c):
    print(c["mesaj"], f"(benzerlik {c['en_iyi_benzerlik']})")
    if c["ozet"]:
        print("\nKısa cevap:", c["ozet"]["metin"])
        print("Dayanak:", "; ".join(c["ozet"]["dayanak"]))
    for i, k in enumerate(c["kaynaklar"], 1):
        print(f"\n[{i}] {k['atif']}  |  {k['gecerlilik']}")
        for a in k["alinti"]:
            print("    " + a)


if __name__ == "__main__":
    from arama import Arayici
    yazdir(cevapla(" ".join(sys.argv[1:]) or "Kaç AKTS üst sınırım var?", Arayici()))
