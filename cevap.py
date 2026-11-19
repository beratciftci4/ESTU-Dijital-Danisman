"""
5. aşama: API kullanmadan, kaynak göstererek cevap.

Cevap = soruya en uygun madde(ler)in kendisi. Her kaynağın belge adı, madde numarası,
sayfası ve yürürlük tarihi yazılıyor. Metin üretmediğimiz için uydurma riski yok.

Güven seviyesi (en iyi parçanın e5 benzerliğine göre):
  - "bulundu"     : >= ESIK_YUKSEK, cevap olarak gösterilir
  - "belirsiz"    : arada, "kesin cevap bulamadım, ilgili olabilecek maddeler" denir
  - "bulunamadi"  : < ESIK_DUSUK, "bulamadım" denir

Eşikler tests/ altındaki cevaplı ve cevapsız sorulara bakılarak seçildi (raporlar/5_cevap.md).

    python cevap.py "Kaç AKTS üst sınırım var?"
"""
import re
import sys

from indeks import kelimeler, soru_kelimeleri

ESIK_YUKSEK = 0.850
ESIK_DUSUK = 0.825
KAYNAK_SAYISI = 3

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


def cevapla(soru, arayici, k=KAYNAK_SAYISI):
    soru = soru.strip()
    if len(soru) < 3:
        return {"durum": "bulunamadi", "mesaj": "Lütfen bir soru yazın.", "kaynaklar": []}

    sonuclar = arayici.ara(soru, k=k)
    en_iyi = max(b["e5"] for _, b in sonuclar)
    if en_iyi >= ESIK_YUKSEK:
        durum = "bulundu"
        mesaj = "İlgili hükümler aşağıda. Cevap doğrudan resmi metinden alınmıştır."
    elif en_iyi >= ESIK_DUSUK:
        durum = "belirsiz"
        mesaj = ("Bu soruya belgelerde kesin bir cevap bulamadım. "
                 "İlgili olabilecek maddeler aşağıda, lütfen kontrol edin.")
    else:
        durum = "bulunamadi"
        mesaj = ("Bu sorunun cevabını eklenen resmi belgelerde bulamadım. "
                 "Öğrenci İşleri'ne ya da akademik danışmanınıza sorabilirsiniz.")

    kaynaklar = []
    if durum != "bulunamadi":
        for p, b in sonuclar:
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
    return {"durum": durum, "mesaj": mesaj, "kaynaklar": kaynaklar, "en_iyi_benzerlik": round(en_iyi, 3)}


def yazdir(c):
    print(c["mesaj"], f"(benzerlik {c['en_iyi_benzerlik']})")
    for i, k in enumerate(c["kaynaklar"], 1):
        print(f"\n[{i}] {k['atif']}  |  {k['gecerlilik']}")
        for a in k["alinti"]:
            print("    " + a)


if __name__ == "__main__":
    from arama import Arayici
    yazdir(cevapla(" ".join(sys.argv[1:]) or "Kaç AKTS üst sınırım var?", Arayici()))
