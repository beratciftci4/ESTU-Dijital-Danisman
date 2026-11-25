"""
5. aşama: API kullanmadan, kaynak göstererek cevap.

Cevap iki kısımdan oluşuyor:
  - kısa cevap: ozetler.yaml'daki elle yazılmış sade özet cümlelerinden soruya en uygun 1-3 tanesi
  - kaynaklar: soruya en uygun maddelerin kendisi (belge adı, madde, sayfa, yürürlük tarihi)
Cümleler önceden yazıldığı için çalışırken metin üretilmiyor, uydurma riski yok.

Güven seviyesi (en iyi parçanın e5 benzerliğine göre):
  - "bulundu"     : >= ESIK_YUKSEK, cevap olarak gösterilir
  - "belirsiz"    : arada, "kesin cevap bulamadım, ilgili olabilecek maddeler" denir
  - "bulunamadi"  : < ESIK_DUSUK, "bulamadım" denir

Eşikler tests/ altındaki cevaplı ve cevapsız sorulara bakılarak seçildi (raporlar/5_cevap.md).

    python cevap.py "Kaç AKTS üst sınırım var?"
"""
import hashlib
import re
import sys

import numpy as np
import yaml

from indeks import INDEKS_KLASORU, KLASOR, kelimeler, soru_kelimeleri

ESIK_YUKSEK = 0.850
ESIK_DUSUK = 0.825
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
    "danismanlik": "Akademik Danışmanlık Yönergesi",
    "proje_temelli_staj": "Proje Temelli Staj Yönergesi",
    "hakli_nedenler": "Haklı ve Geçerli Nedenlere İlişkin Usul ve Esaslar",
    "tek_ders": "Tek Ders Sınavı Uygulama Esasları",
    "ek_sinav": "Ek Sınav Esasları",
    "yaz_okulu": "Yaz Okulu Uygulama Esasları",
    "not_karsiliklari": "Not Karşılıkları ve Eşdeğerlikler Uygulama Esasları",
    "ders_plani": "İstatistik Bölümü Ders Planı (Bologna)",
    "program_bilgileri": "İstatistik Bölümü Program Bilgileri (Bologna)",
}


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
    metin = f"{BELGE_KISA_ADI.get(p['belge_id'], p['belge_adi'])}, {konum(p)}"
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
    return "Bologna web sayfası, erişim: 19.11.2026"


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


def ozet_cumleleri():
    """[(parça id, cümle no, cümle), ...] ozetler.yaml'daki sırayla."""
    return [(pid, i, c) for pid, cumleler in ozetleri_oku().items() for i, c in enumerate(cumleler)]


def ozet_indeksi_olustur(gomucu):
    """Özet cümlelerinin e5 vektörlerini indeks/ klasörüne kaydeder (özetler değişince yeniden çalıştır)."""
    cumleler = ozet_cumleleri()
    vektorler = gomucu.vektor([c for _, _, c in cumleler], "passage")
    np.savez(OZET_VEKTORLERI, vektorler=vektorler, ozet_hash=dosya_hash(OZET_DOSYASI))
    return len(cumleler)


def dosya_hash(yol):
    return hashlib.sha256(open(yol, "rb").read()).hexdigest()


_ozet_vektorleri = None


def ozet_vektorleri(gomucu):
    global _ozet_vektorleri
    if _ozet_vektorleri is None:
        if not OZET_VEKTORLERI.exists() or str(np.load(OZET_VEKTORLERI)["ozet_hash"]) != dosya_hash(OZET_DOSYASI):
            print("ozetler.yaml değişmiş, özet vektörleri yeniden hesaplanıyor...")
            ozet_indeksi_olustur(gomucu)
        _ozet_vektorleri = np.load(OZET_VEKTORLERI)["vektorler"]
    return _ozet_vektorleri


def benzer_mi(a, b):
    """İki cümle aynı şeyi mi söylüyor? (farklı belgelerde aynı kural tekrar ediyor)"""
    ka, kb = set(kelimeler(a)), set(kelimeler(b))
    return len(ka & kb) / max(1, min(len(ka), len(kb))) >= 0.6


def kisa_cevap(soru, sonuclar, arayici, en_fazla=OZET_CUMLE_SAYISI, agirlik=None):
    """En iyi 3 parçanın özet cümlelerinden soruya en uygun 1-3 tanesini seçip paragraf yapar.
    Cümle puanı = e5 benzerliği + kelime örtüşmesi (idf ağırlıklı, 0-1 arası) * KELIME_AGIRLIGI
                  + parçanın arama sırasına göre küçük bir pay. En iyi cümle başa yazılır."""
    kelime_agirligi, sira_payi, ilk_payi, madde_agirligi = agirlik or (
        KELIME_AGIRLIGI, SIRA_PAYI, ILK_CUMLE_PAYI, MADDE_AGIRLIGI)
    cumleler = ozet_cumleleri()
    vektorler = ozet_vektorleri(arayici.gomucu)
    q = arayici.soru_vektoru(soru)
    idf = arayici.bm25.idf
    sorudakiler = set(soru_kelimeleri(soru))
    toplam_idf = sum(idf.get(k, 0) for k in sorudakiler) or 1

    adaylar = []
    for sira, (p, b) in enumerate(sonuclar[:ADAY_PARCA]):
        for j, (pid, i, c) in enumerate(cumleler):
            if pid != p["id"]:
                continue
            ortak = sum(idf.get(k, 0) for k in sorudakiler & set(kelimeler(c))) / toplam_idf
            puan = (float(vektorler[j] @ q) + kelime_agirligi * ortak - sira_payi * sira
                    + (ilk_payi if i == 0 else 0) + madde_agirligi * b["e5"])
            adaylar.append((puan, sira, i, c, p))
    if not adaylar:
        return None

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
        "dayanak": [f"{BELGE_KISA_ADI.get(p['belge_id'], p['belge_adi'])}, {konum(p)}" for p in kullanilan],
    }


def cevapla(soru, arayici, k=KAYNAK_SAYISI):
    soru = soru.strip()
    if len(soru) < 3:
        return {"durum": "bulunamadi", "mesaj": "Lütfen bir soru yazın.", "kaynaklar": []}

    tum = arayici.ara(soru, k=max(k, ADAY_PARCA))
    sonuclar = tum[:k]   # güven seviyesi ilk k parçaya göre (eşikler buna göre seçildi)
    en_iyi = max(b["e5"] for _, b in sonuclar)
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
    ozet = kisa_cevap(soru, tum, arayici) if durum != "bulunamadi" else None
    if durum != "bulunamadi":
        # kısa cevabın dayandığı parça ilk k'nın dışındaysa o da kaynaklara eklenir
        ekler = [(p, b) for p, b in tum[k:] if p["id"] in ozet["parcalar"]]
        for p, b in sonuclar + ekler:
            kaynaklar.append({
                "id": p["id"],
                "atif": atif(p),
                "belge": BELGE_KISA_ADI.get(p["belge_id"], p["belge_adi"]),
                "konum": konum(p),
                "baslik": p["baslik"] if p["tur"] == "madde" else None,
                "sayfa": sayfa_metni(p),
                "gecerlilik": gecerlilik(p),
                "alinti": ilgili_kisim(p, soru, arayici.bm25.idf),
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
