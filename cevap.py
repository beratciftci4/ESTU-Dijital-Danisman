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

from belge_kontrol import programlari_oku
from indeks import INDEKS_KLASORU, KLASOR, kelimeler, soru_kelimeleri, turkce_kucuk

ESIK_YUKSEK = 0.866
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
    "danismanlik": "Akademik Danışmanlık Yönergesi",
    "proje_temelli_staj": "Proje Temelli Staj Yönergesi",
    "hakli_nedenler": "Haklı ve Geçerli Nedenlere İlişkin Usul ve Esaslar",
    "tek_ders": "Tek Ders Sınavı Uygulama Esasları",
    "ek_sinav": "Ek Sınav Esasları",
    "yaz_okulu": "Yaz Okulu Uygulama Esasları",
    "not_karsiliklari": "Not Karşılıkları ve Eşdeğerlikler Uygulama Esasları",
}
PROGRAM_ADI = {p["id"]: p["ad"] for p in programlari_oku()[1]}
STAJ_MADDESI = {p["id"]: programlari_oku()[0][p["fakulte"]]["staj_maddesi"] for p in programlari_oku()[1]}


def program_id(p):
    """Bologna parçasıysa bölüm id'si (istatistik_ders_plani -> istatistik), değilse None."""
    for son in ("_ders_plani", "_program_bilgileri"):
        if p["belge_id"].endswith(son):
            return p["belge_id"][: -len(son)]
    return None


def kisa_ad(p):
    """Atıflarda kullanılan kısa belge adı."""
    pid = program_id(p)
    if pid:
        tur = "Ders Planı" if p["belge_id"].endswith("_ders_plani") else "Program Bilgileri"
        return f"{PROGRAM_ADI[pid]} Bölümü {tur} (Bologna)"
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
    """Ders planı tablosundan özet cümleleri üretir (elle yazmak yerine, 31 bölüm var).
    Satırlar: 'KOD | Ad | Dil | T+U | AKTS', 'Seçmeli Dersler | 5.0', 'Toplam | 30'."""
    bolum = PROGRAM_ADI[program_id(p)]
    dersler, ekler, toplam = [], [], None
    for satir in p["metin"].split("\n"):
        h = [x.strip() for x in satir.split("|")]
        if len(h) == 5 and h[0] != "Ders Kodu":
            dersler.append((h[1], akts(h[4])))
        elif len(h) == 2 and h[0] == "Toplam":
            toplam = akts(h[1])
        elif len(h) == 2:
            ekler.append(f"{akts(h[1])} AKTS {h[0].lower().replace('dersler', 'ders')}")

    # aynı ders Türkçe ve İngilizce iki şube olarak açılabiliyor:
    # "Biyokimya II" ve "Biochemistry II (Biyokimya II)" -> "Biyokimya II (Türkçe ya da İngilizce)"
    turkce_adlar = {ad for ad, _ in dersler}
    listelenen = []
    for ad, kredi in dersler:
        ic = re.search(r"\(([^()]+)\)\s*$", ad)
        if ic and ic.group(1) in turkce_adlar:
            continue
        iki_dil = any(re.search(r"\(" + re.escape(ad) + r"\)\s*$", a) for a, _ in dersler)
        listelenen.append(f"{ad} ({'Türkçe ya da İngilizce, ' if iki_dil else ''}{kredi} AKTS)")

    yariyil = ROMA.get(p["no"].replace(".YARIYIL", ""))
    if yariyil:
        cumleler = [f"{bolum} bölümünde {yariyil}. yarıyılın zorunlu dersleri şunlardır: {', '.join(listelenen)}."]
        if ekler or toplam:
            ek = f"ayrıca {' ve '.join(ekler)} alınır" if ekler else "seçmeli ders yoktur"
            cumleler.append(f"{bolum} bölümünde {yariyil}. yarıyılda {ek}"
                            + (f"; yarıyılın toplamı {toplam} AKTS'dir." if toplam else "."))
        return cumleler
    # seçmeli ders havuzları: uzun listeyi 10'arlı cümlelere böl
    havuz = p["no"].lower()
    return [f"{bolum} bölümünün {havuz} listesinde şunlar var: {', '.join(listelenen[i:i + 10])}."
            for i in range(0, len(listelenen), 10)]


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


def tum_ozetler():
    """ozetler.yaml + ders planlarından ve standart Bologna metinlerinden üretilen özetler."""
    ozetler = dict(ozetleri_oku())
    parcalar = {p["id"]: p for p in parcalar_oku()}
    for p in parcalar.values():
        if p["id"] in ozetler:
            continue
        if p["belge_id"].endswith("_ders_plani"):
            ozetler[p["id"]] = ders_plani_ozeti(p)
        elif p["belge_id"].endswith("_program_bilgileri"):
            sablon = standart_ozet(p, parcalar)
            if sablon:
                ozetler[p["id"]] = sablon
    return ozetler


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
            c = f"{p['ad']} bölümünde staj zorunlu mu, belgelerden net anlaşılmıyor. {p['staj_ek']}"
        elif p.get("staj_suresi_belirsiz"):
            c = f"{p['ad']} bölümünde staj zorunludur. {p['staj_ek']}"
        elif p["staj_gunu"]:
            c = (f"{p['ad']} bölümünde staj zorunludur; mezun olmak için toplam en az {p['staj_gunu']} {birim} "
                 "staj yapman gerekir." + (f" {p['staj_ek']}" if p.get("staj_ek") else ""))
        else:
            c = (f"{p['ad']} bölümünde staj zorunlu değildir, isteğe bağlıdır; mezuniyet için staj şartı yok."
                 + (f" {p['staj_ek']}" if p.get("staj_ek") else ""))
        sonuc.append((parca_id, c, p["id"]))
    return sonuc


PTS_PAYI = 0.05


def staj_suresi_soruluyor(soru):
    """Soru stajın süresini ya da zorunlu olup olmadığını mı soruyor? (diğer staj konuları değil)"""
    s = turkce_kucuk(soru)
    return ("staj" in s and bool(re.search(r"kaç|ne kadar|süre|zorunlu|zorunda|gerek|lazım|şart", s))
            and not re.search(r"proje temelli|proje tabanl|pts|önlisans|itiraz|başvur|ne zaman|nerede|değiş|muaf|sigorta|rapor|"
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
    return bolum is None or bolum == program


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
    kelime_agirligi, sira_payi, ilk_payi, madde_agirligi = agirlik or (
        KELIME_AGIRLIGI, SIRA_PAYI, ILK_CUMLE_PAYI, MADDE_AGIRLIGI)
    cumleler = ozet_cumleleri()
    bolumler = ozet_bolumleri()
    vektorler = ozet_vektorleri(arayici.gomucu)
    q = arayici.soru_vektoru(soru)
    idf = arayici.bm25_icin(program).idf
    sorudakiler = set(soru_kelimeleri(soru))
    toplam_idf = sum(idf.get(k, 0) for k in sorudakiler) or 1

    e5 = {}
    if program not in (None, "genel"):
        alt = arayici.alt_kume(program)[0]
        e5 = dict(zip((arayici.parcalar[x]["id"] for x in alt), arayici.e5_skorlari(soru, program)))

    def madde_benzerligi(pid, j, varsayilan):
        # bölüme özel staj cümlesi, fakültenin staj maddesinin bölüme özel hali: o maddenin
        # benzerliğinden aşağı sayılmasın (cümle bazen bir form ekine ya da Bologna sayfasına bağlı)
        if bolumler[j] == program and program in STAJ_MADDESI:
            return max(varsayilan, e5.get(STAJ_MADDESI[program], varsayilan))
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
    sonuclar = tum[:k]
    en_iyi = guven_skoru(soru, sonuclar, arayici, program)
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
