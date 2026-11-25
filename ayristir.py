"""
2. aşama: kaynaklar/ altındaki belgeleri madde madde parçalara ayırır.

    python ayristir.py          -> cikti/parcalar.jsonl

Her parça bir madde (ya da numaralı bent) oluyor, sayfa numarası ve başlığıyla birlikte.
Sabit uzunlukta bölmüyoruz çünkü cevapta "Madde 10, s. 3" diye kaynak göstermek istiyoruz.

Belge türleri:
  - "MADDE 10-" / "MADDE 1 –" / "MADDE 14 Öğrenci..." gibi madde başlıklı yönetmelik/yönergeler
  - "1) ..." ya da "1- ..." diye numaralanan usul ve esaslar
  - taranmış PDF (ek sınav): elle düzeltilmiş OCR metni (.ocr.txt) kullanılıyor
  - Bologna sayfaları (html): başlık başlık / yarıyıl yarıyıl
"""
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup

from belge_kontrol import KAYNAK_KLASORU, KLASOR, belgeleri_oku

CIKTI = KLASOR / "cikti" / "parcalar.jsonl"
ONBELLEK = KLASOR / "cikti" / "onbellek"
ONBELLEK_SURUMU = "3"   # satır okuma mantığı değişince artır, eski önbellek kullanılmasın

# madde numarasından sonra gelebilen ayraçlar: - – ‒ — ya da hiçbiri ("MADDE 14 Öğrencinin")
MADDE_DESENI = re.compile(r"^MADDE\s+(\d+(?:/[A-ZÇĞİÖŞÜ])?)\s*[-–‒—]?\s*(.*)$")
NUMARA_DESENI = re.compile(r"^(\d{1,2})\s*[)\-–]\s+(.*)$")      # 1) ... / 1- ...
OCR_NUMARA_DESENI = re.compile(r"^(\d{1,2})\.\s+(.*)$")         # 1. ...
BOLUM_DESENI = re.compile(r"^[A-ZÇĞİÖŞÜ]+\s+BÖLÜM$")
EK_DESENI = re.compile(r"^EK\s*[-–‒]?\s*\d+")
# son maddeden sonra gelen künye/tablo kısımları
KUNYE_DESENI = re.compile(
    r"^(Açıklama(\s*\||$)|YÜRÜRLÜĞE GİRİŞ|Kabul/Revizyon Tarih|Yönetmeliğin Yayımlandığı Resm)"
)
SAYFA_DESENI = re.compile(r"Sayfa\s*:?\s*\d+\s*/\s*\d+")

# hangi belge hangi numaralandırmayı kullanıyor
BICIM = {
    "yonetmelik": "madde",
    "fen_staj": "madde",
    "muh_staj": "madde",
    "danismanlik": "madde",
    "proje_temelli_staj": "madde",
    "hakli_nedenler": "numara",
    "tek_ders": "numara",
    "yaz_okulu": "numara",
    "not_karsiliklari": "numara",
    "ek_sinav": "ocr",
}


def temizle(metin):
    metin = unicodedata.normalize("NFC", metin)
    metin = metin.replace("­", "").replace(" ", " ")
    metin = re.sub(r"[.…]{4,}", "…", metin)          # form boşlukları
    return metin.strip()


# ---------- PDF'ten satır okuma ----------

def tablo_bozuk_mu(satirlar):
    """Birleşik hücreli tablolarda iki satırın sayıları tek hücreye düşüyor ("800 797" gibi).
    Hücrelerin %15'inden fazlası böyleyse tabloyu güvenilmez sayıyoruz."""
    hucreler = [h.strip() for s in satirlar for h in s.split("|")]
    if not hucreler:
        return False
    cift = sum(bool(re.fullmatch(r"[\d,.‒-]+(\s+[\d,.‒-]+)+", h)) for h in hucreler)
    return cift / len(hucreler) > 0.15


def sayfa_metni(sayfa):
    """Sayfanın metni. Tablo varsa satırları 'a | b | c' şeklinde yazıyor."""
    tablolar = sayfa.find_tables().tables
    if not tablolar:
        return sayfa.get_text()

    parcalar = []  # (y, x, metin)
    kutular = [pymupdf.Rect(t.bbox) for t in tablolar]
    # t.extract() bazı fontlarda boşlukları yutuyor. get_textbox da her hücrede sayfayı baştan
    # okuduğu için çok yavaş. Kelimeleri bir kere alıp hücrelere biz dağıtıyoruz.
    kelimeler = sayfa.get_text("words")

    def hucre_metni(kutu):
        k = pymupdf.Rect(kutu)
        icindekiler = [w for w in kelimeler
                       if pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2) in k]
        icindekiler.sort(key=lambda w: (w[5], w[6], w[7]))   # blok, satır, kelime sırası
        return " ".join(w[4] for w in icindekiler)

    for t in tablolar:
        satirlar = []
        for satir in t.rows:
            hucreler = [hucre_metni(h) if h else "" for h in satir.cells]
            hucreler = [h for h in hucreler if h]
            if hucreler:
                satirlar.append(" | ".join(hucreler))
        if tablo_bozuk_mu(satirlar):
            # yanlış sayı vermektense "sayfaya bak" demek daha iyi
            satirlar = [f"[Bu sayfadaki tablo düzgün okunamadı, değerler için {sayfa.number + 1}. "
                        f"sayfaya bakılmalı.]"]
        parcalar.append((t.bbox[1], t.bbox[0], "\n".join(satirlar)))
    # blok değil satır satır bakıyoruz, büyük bir paragraf bloğu tabloyla çakışıp kaybolmasın
    for blok in sayfa.get_text("dict")["blocks"]:
        for satir in blok.get("lines", []):
            x0, y0, x1, y1 = satir["bbox"]
            orta = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
            if not any(orta in k for k in kutular):
                metin = "".join(span["text"] for span in satir["spans"])
                parcalar.append((y0, x0, metin, False))
    parcalar = [p if len(p) == 4 else (*p, True) for p in parcalar]
    parcalar.sort(key=lambda p: (p[0], p[1]))

    # aynı hizadaki satır parçalarını ("1-" ve devamı gibi) tek satırda birleştir
    cikti = []
    for y, x, metin, tablo_mu in parcalar:
        if cikti and not tablo_mu and not cikti[-1][2] and abs(cikti[-1][0] - y) < 3:
            cikti[-1][1] += " " + metin
        else:
            cikti.append([y, metin, tablo_mu])
    return "\n".join(m for _, m, _ in cikti)


def pdf_satirlari(yol):
    """[(sayfa_no, satir), ...] - sayfa numaraları, tekrar eden üst/alt bilgiler atılmış halde.

    Tablo bulma yavaş (belge başına birkaç saniye), o yüzden sonucu dosyanın sha256'sı ile
    cikti/onbellek/ altına kaydediyoruz. PDF ya da bu fonksiyon değişirse yeniden okunur."""
    ozet = hashlib.sha256(Path(yol).read_bytes() + ONBELLEK_SURUMU.encode()).hexdigest()[:16]
    onbellek = ONBELLEK / f"{Path(yol).stem}_{ozet}.json"
    if onbellek.exists():
        veri = json.loads(onbellek.read_text(encoding="utf-8"))
        return [tuple(x) for x in veri["satirlar"]], veri["resimli"]

    satirlar, resimli = _pdf_satirlari_oku(yol)
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    onbellek.write_text(json.dumps({"satirlar": satirlar, "resimli": resimli}, ensure_ascii=False),
                        encoding="utf-8")
    return satirlar, resimli


def _pdf_satirlari_oku(yol):
    doc = pymupdf.open(yol)
    satirlar = []
    resimli_sayfalar = []
    for i, sayfa in enumerate(doc):
        metin = sayfa_metni(sayfa)
        # metni çok az, resmi olan sayfa = tablo görüntü olarak konmuş
        if sayfa.get_images() and len(SAYFA_DESENI.sub("", metin).strip()) < 300:
            resimli_sayfalar.append(i + 1)
        for s in metin.split("\n"):
            s = temizle(SAYFA_DESENI.sub("", s))
            if s:
                satirlar.append((i + 1, s))

    # Üst/alt bilgi: sayfanın ilk 6 ya da son 3 satırında olup en az 3 sayfada aynen tekrar eden
    # satırlar ("Karar Tarihi | 08/11/2022", "Revizyon | 1" gibi). Ekler sayfa sayısını şişirdiği
    # için oran yerine sayfa sayısına bakıyoruz.
    if len(doc) >= 3:
        kenarlar = Counter()
        for sayfa_no in {p for p, _ in satirlar}:
            sayfadakiler = [s for p, s in satirlar if p == sayfa_no]
            kenarlar.update(set(sayfadakiler[:6] + sayfadakiler[-3:]))
        tekrar = {s for s, n in kenarlar.items() if n >= 3 and len(s) < 120}
        satirlar = [(p, s) for p, s in satirlar if s not in tekrar]
        # sayfa numarası: sayfanın ilk ya da son satırı sadece o sayfanın numarasıysa
        kenar_satir = set()
        for sayfa_no in {p for p, _ in satirlar}:
            sira = [i for i, (p, _) in enumerate(satirlar) if p == sayfa_no]
            for i in (sira[0], sira[-1]):
                if satirlar[i][1].strip() == str(sayfa_no):
                    kenar_satir.add(i)
        satirlar = [x for i, x in enumerate(satirlar) if i not in kenar_satir]
    return satirlar, resimli_sayfalar


def ocr_satirlari(yol):
    satirlar = []
    sayfa = 0
    for s in yol.read_text(encoding="utf-8").split("\n"):
        if s.startswith("#"):
            continue
        m = re.match(r"=== SAYFA (\d+) ===", s)
        if m:
            sayfa = int(m.group(1))
            continue
        s = temizle(s)
        if s:
            satirlar.append((sayfa, s))
    return satirlar


# ---------- madde / bent ayırma ----------

def sonraki_mi(onceki, yeni, bicim):
    """Numaralar sırayla gitmeli, yoksa metnin içindeki bir sayı yanlışlıkla madde sanılır."""
    if onceki is None:
        return yeni == "1"
    o_sayi = int(onceki.split("/")[0])
    y_sayi = int(yeni.split("/")[0])
    if bicim == "madde" and "/" in yeni:      # 20/A, 20'den sonra gelir
        return y_sayi == o_sayi
    return y_sayi == o_sayi + 1


def baslik_mi(satir):
    """Maddenin üstündeki kısa başlık satırı mı? ("Ders kaydı", "Amaç ve kapsam" gibi)"""
    return (len(satir) < 90 and not satir.endswith((".", ";", ":", ","))
            and not BOLUM_DESENI.match(satir) and not re.match(r"^\(?\d", satir)
            and not re.match(r"^[a-zçğıöşü]\)", satir))


def birlestir(satirlar):
    """Satırları paragrafa çevirir. Fıkra (1) ve bent a) başları yeni satırda kalır."""
    cikti = []
    for s in satirlar:
        # tablo satırları (" | " içerenler) ve fıkra/bent başları ayrı satırda kalsın
        yeni_satir = " | " in s or re.match(r"^(\(\d+\)|[a-zçğıöşü]\)|[A-Z]\))", s)
        if cikti and not yeni_satir and " | " not in cikti[-1]:
            cikti[-1] = cikti[-1] + " " + s
        else:
            cikti.append(s)
    metin = "\n".join(cikti)
    return re.sub(r"[ \t]+", " ", metin).strip()


def maddelere_ayir(satirlar, bicim):
    """satirlar -> giris, maddeler, kuyruk (son maddeden sonraki künye/ekler)"""
    desen = {"madde": MADDE_DESENI, "numara": NUMARA_DESENI, "ocr": OCR_NUMARA_DESENI}[bicim]
    giris, maddeler, kuyruk = [], [], []
    mevcut = None
    bolum = None
    kuyrukta = False

    for i, (sayfa, s) in enumerate(satirlar):
        if kuyrukta:
            kuyruk.append((sayfa, s))
            continue
        if maddeler and (EK_DESENI.match(s) or KUNYE_DESENI.match(s)):
            kuyrukta = True
            kuyruk.append((sayfa, s))
            continue

        m = desen.match(s)
        if m and sonraki_mi(mevcut["no"] if mevcut else None, m.group(1), bicim):
            baslik = None
            hedef = mevcut["satirlar"] if mevcut else giris
            if bicim == "madde":
                # üstteki başlık satırını (ve varsa bölüm adını) önceki parçadan al
                if hedef and baslik_mi(hedef[-1][1]):
                    baslik = hedef.pop()[1]
                if len(hedef) >= 2 and BOLUM_DESENI.match(hedef[-2][1]):
                    bolum = hedef[-2][1] + " - " + hedef[-1][1]
                    del hedef[-2:]
                elif hedef and BOLUM_DESENI.match(hedef[-1][1]):
                    bolum = hedef.pop()[1]
            mevcut = {"no": m.group(1), "baslik": baslik, "bolum": bolum,
                      "satirlar": [(sayfa, m.group(2))] if m.group(2) else []}
            if not mevcut["satirlar"]:
                mevcut["satirlar"].append((sayfa, ""))
            maddeler.append(mevcut)
        elif mevcut:
            mevcut["satirlar"].append((sayfa, s))
        else:
            giris.append((sayfa, s))
    return giris, maddeler, kuyruk


def turkce_baslik(metin):
    """'ESKİŞEHİR TEKNİK' -> 'Eskişehir Teknik'. str.title() Türkçe İ/ı harflerini bozuyor."""
    def kucuk(x):
        return x.replace("I", "ı").replace("İ", "i").lower()

    def buyuk(x):
        return x.replace("i", "İ").replace("ı", "I").upper()
    return " ".join(buyuk(k[0]) + kucuk(k[1:]) if k else k for k in metin.split(" "))


def kuyrugu_bol(kuyruk):
    """Son maddeden sonrasını künye ve EK-1, EK-2 ... parçalarına böler."""
    bloklar = []
    for i, (sayfa, s) in enumerate(kuyruk):
        # künyeden sonra büyük harfli başlıkla başlayan tablo (ek sınavdaki not dönüşüm tablosu gibi)
        # künyeye karışmasın, ayrı ek olsun
        yeni_tablo = (bloklar and bloklar[-1]["ad"] == "Kabul ve değişiklik bilgisi" and s.isupper()
                      and any("TABLO" in x for _, x in kuyruk[i:i + 3]))
        if EK_DESENI.match(s) or not bloklar or yeni_tablo:
            if yeni_tablo:
                ad = turkce_baslik(" ".join(x for _, x in kuyruk[i:i + 3] if x.isupper()))
            else:
                ad = s if EK_DESENI.match(s) else "Kabul ve değişiklik bilgisi"
            bloklar.append({"ad": ad, "satirlar": []})
        bloklar[-1]["satirlar"].append((sayfa, s))
    return bloklar


# ---------- parça üretme ----------

def parca(belge, tur, no, baslik, bolum, satirlar, ocr=False):
    metin = birlestir([s for _, s in satirlar if s])
    sayfalar = [p for p, s in satirlar if s and p is not None]
    return {
        "id": f"{belge['id']}#{tur}-{no}".replace(" ", "_"),
        "belge_id": belge["id"],
        "belge_adi": belge["ad"],
        "tur": tur,               # madde | bent | ek | kunye | giris | tablo_gorsel | bolum
        "no": no,
        "baslik": baslik,
        "bolum": bolum,
        "sayfa_bas": min(sayfalar) if sayfalar else None,
        "sayfa_bit": max(sayfalar) if sayfalar else None,
        "metin": metin,
        "ocr": ocr,
        "url": belge["url"],
        "yururluk": str(belge["yururluk"]) if belge["yururluk"] else None,
        "son_degisiklik": str(belge["son_degisiklik"]) if belge["son_degisiklik"] else None,
        "kapsam": belge.get("kapsam", "genel"),
        "indirme_tarihi": str(belge["indirme_tarihi"]) if belge.get("indirme_tarihi") else None,   # genel | fakulte:fen | program:istatistik
    }


def pdf_ayristir(belge):
    bicim = BICIM[belge["id"]]
    yol = KAYNAK_KLASORU / belge["dosya"]
    ocr = bicim == "ocr"
    if ocr:
        satirlar, resimli = ocr_satirlari(yol.with_suffix(".ocr.txt")), []
    else:
        satirlar, resimli = pdf_satirlari(yol)

    giris, maddeler, kuyruk = maddelere_ayir(satirlar, bicim)
    madde_turu = "madde" if bicim == "madde" else "bent"
    parcalar = []

    # başlık dışında giriş metni varsa (usul-esaslardaki ilk paragraf gibi) onu da tut
    giris_metni = [(p, s) for p, s in giris if not s.isupper()]
    if bicim != "madde" and sum(len(s) for _, s in giris_metni) > 80:
        parcalar.append(parca(belge, "giris", "0", "Giriş", None, giris_metni, ocr))

    for m in maddeler:
        parcalar.append(parca(belge, madde_turu, m["no"], m["baslik"], m["bolum"],
                              m["satirlar"], ocr))
    for i, blok in enumerate(kuyrugu_bol(kuyruk)):
        tur = "kunye" if blok["ad"] == "Kabul ve değişiklik bilgisi" else "ek"
        parcalar.append(parca(belge, tur, str(i + 1), blok["ad"], None, blok["satirlar"], ocr))

    # görüntü olarak eklenmiş tablolar okunamıyor, bunu açıkça kaydediyoruz
    for s in resimli:
        p = parca(belge, "tablo_gorsel", str(s), "Görüntü olarak eklenmiş tablo", None,
                  [(s, f"{s}. sayfadaki tablo görüntü olarak eklenmiş, metni okunamıyor. "
                       f"Bu tablodaki değerler için belgenin {s}. sayfasına bakılmalı.")])
        parcalar.append(p)
    return parcalar


def html_ayristir(belge):
    yol = KAYNAK_KLASORU / belge["dosya"]
    soup = BeautifulSoup(yol.read_text(encoding="utf-8"), "html.parser")
    parcalar = []

    if belge["id"].endswith("_ders_plani"):
        for h in soup.find_all("h2"):
            # sayfanın html'i bozuk: seçmeli ders başlıklarında tablo <h2>'nin içinde kalmış,
            # bu yüzden adı sadece ilk metin parçasından alıyoruz
            tablo = h.find("table") or h.find_next("table")
            satirlar = []
            for tr in [tr for tr in tablo.find_all("tr") if tr.find_parent("table") is tablo]:
                hucreler = [temizle(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
                hucreler = [x for x in hucreler if x]
                if hucreler:
                    satirlar.append((None, " | ".join(hucreler)))
            ad = temizle(h.find(string=True))
            parcalar.append(parca(belge, "bolum", ad, ad, "Dersler - AKTS Kredileri", satirlar))
    else:
        for h in soup.find_all("h4"):
            ad = temizle(h.get_text(strip=True))
            satirlar = []
            for kardes in h.find_next_siblings():
                if kardes.name == "h4":
                    break
                for s in kardes.get_text("\n", strip=True).split("\n"):
                    if temizle(s):
                        satirlar.append((None, temizle(s)))
            if not satirlar:   # bazı sayfalarda içerik başlığın kardeşi değil, bir sonraki div'de
                kap = h.find_parent()
                for s in kap.get_text("\n", strip=True).split("\n")[1:]:
                    if temizle(s):
                        satirlar.append((None, temizle(s)))
            # bazı bölüm sayfalarında aynı paragraf html'de iki kere geçiyor
            satirlar = list(dict.fromkeys(satirlar))
            parcalar.append(parca(belge, "bolum", ad, ad, "Program Hakkında", satirlar))
    return parcalar


def tum_belgeler():
    parcalar = []
    for belge in belgeleri_oku():
        if belge["durum"] != "aktif":
            continue
        if belge["dosya"].endswith(".html"):
            parcalar += html_ayristir(belge)
        else:
            parcalar += pdf_ayristir(belge)
    return parcalar


def main():
    parcalar = tum_belgeler()
    CIKTI.parent.mkdir(exist_ok=True)
    with open(CIKTI, "w", encoding="utf-8") as f:
        for p in parcalar:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    sayac = Counter((p["belge_id"], p["tur"]) for p in parcalar)
    for belge_id in dict.fromkeys(p["belge_id"] for p in parcalar):
        turler = ", ".join(f"{t}: {n}" for (b, t), n in sayac.items() if b == belge_id)
        print(f"{belge_id:20} {turler}")
    print(f"\n{len(parcalar)} parça -> {CIKTI.relative_to(KLASOR)}")


if __name__ == "__main__":
    sys.exit(main())
