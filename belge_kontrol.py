"""
belgeler.yaml'daki kayıtları kontrol eder, kaynaklar/ klasörüyle karşılaştırır.

    python belge_kontrol.py
"""
import hashlib
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import yaml

KLASOR = Path(__file__).parent
KAYNAK_KLASORU = KLASOR / "kaynaklar"

ALANLAR = ["id", "ad", "dosya", "url", "yayim", "yururluk", "son_degisiklik",
           "dayanak", "indirme_tarihi", "sha256", "kapsam", "durum", "not"]
TARIHLER = ["yayim", "yururluk", "son_degisiklik", "indirme_tarihi"]


def belgeleri_oku(yol=KLASOR / "belgeler.yaml"):
    with open(yol, encoding="utf-8") as f:
        return yaml.safe_load(f)


def programlari_oku(yol=KLASOR / "programlar.yaml"):
    """(fakulteler sözlüğü, programlar listesi)"""
    with open(yol, encoding="utf-8") as f:
        veri = yaml.safe_load(f)
    return veri["fakulteler"], veri["programlar"]


PLAN_DESENI = re.compile(r"^(.+)_ders_plani(?:_(\d{4}))?$")


def ders_plani_mi(belge_id):
    """istatistik_ders_plani (Bologna, güncel) ve istatistik_ders_plani_2024 (bölüm sitesindeki
    2024-2025 öğretim yılı planı) için (bölüm, yıl ya da None); ders planı değilse None."""
    m = PLAN_DESENI.match(belge_id)
    return (m[1], int(m[2]) if m[2] else None) if m else None


def bolum_ve_yil(program):
    """Arama anahtarı "istatistik@2024" -> ("istatistik", 2024); "istatistik" -> ("istatistik", None).
    Yıl, hangi öğretim yılının ders planına bakılacağını seçiyor; yoksa Bologna'daki güncel plan."""
    if program is None or "@" not in program:
        return program, None
    bolum, yil = program.split("@")
    return bolum, int(yil)


def gecerli_kapsamlar():
    fakulteler, programlar = programlari_oku()
    return ({"genel", "duzey:lisans", "duzey:onlisans"} | {f"fakulte:{f}" for f in fakulteler}
            | {f"program:{p['id']}" for p in programlar})


def program_kapsamlari(program, fakulteler, programlar):
    """Bir bölüm için geçerli kapsamlar: kendi programı, fakültesi ve düzeyi (lisans/önlisans).
    "duzey:onlisans" bütün meslek yüksekokullarının ortak belgeleri için (MYO staj yönergesi)."""
    p = next(x for x in programlar if x["id"] == program)
    duzey = p.get("duzey") or fakulteler[p["fakulte"]].get("duzey", "lisans")
    return {f"program:{program}", f"fakulte:{p['fakulte']}", f"duzey:{duzey}"}


def hatalari_bul(belgeler):
    hatalar = []
    idler = set()
    kapsamlar = gecerli_kapsamlar()
    for b in belgeler:
        bid = b.get("id", "?")

        eksik = [a for a in ALANLAR if a not in b]
        if eksik:
            hatalar.append(f"{bid}: eksik alan {eksik}")
            continue

        if bid in idler:
            hatalar.append(f"{bid}: aynı id iki kere var")
        idler.add(bid)

        # dosya adında türkçe karakter olmasın (mac'te NFD sorunu çıkarıyor)
        if not re.fullmatch(r"[a-z0-9_]+\.(pdf|html)", b["dosya"]):
            hatalar.append(f"{bid}: dosya adı sadece a-z, 0-9, _ olmalı (.pdf ya da .html)")

        if unicodedata.normalize("NFC", b["ad"]) != b["ad"]:
            hatalar.append(f"{bid}: ad NFC değil, türkçe karakterler bozuk olabilir")

        for alan in TARIHLER:
            deger = b[alan]
            if deger is not None and not isinstance(deger, date):
                hatalar.append(f"{bid}: {alan} YYYY-AA-GG olmalı ({deger})")

        if b["kapsam"] not in kapsamlar:
            hatalar.append(f"{bid}: kapsam genel, duzey:<lisans|onlisans>, fakulte:<ad> ya da program:<ad> olmalı ({b['kapsam']})")

        if b["durum"] not in ("bekleniyor", "aktif"):
            hatalar.append(f"{bid}: durum bekleniyor ya da aktif olmalı")

        # aktif belgede tarih ve hash boş kalmasın
        # bologna sayfalarının yürürlük tarihi yok, onlarda erişim tarihi yeterli; bölüm sitesindeki
        # yıllık ders planlarında da yürürlük yazmıyor, hangi öğretim yılının planı olduğu yazıyor
        if b["durum"] == "aktif":
            gerekli = ["indirme_tarihi", "sha256"]
            if b["dosya"].endswith(".pdf"):
                gerekli.append("ogretim_yili" if ders_plani_mi(bid) else "yururluk")
            for alan in gerekli:
                if not b.get(alan):
                    hatalar.append(f"{bid}: aktif ama {alan} boş")
    return hatalar


def sha256(yol):
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def main():
    belgeler = belgeleri_oku()
    hatalar = hatalari_bul(belgeler)
    for h in hatalar:
        print("HATA:", h)

    print(f"\n{'id':20} {'dosya':5} {'yürürlük':12} {'son değişiklik':15} durum")
    for b in belgeler:
        yol = KAYNAK_KLASORU / b["dosya"]
        var = "var" if yol.exists() else "yok"
        print(f"{b['id']:20} {var:5} {str(b['yururluk'] or '-'):12} "
              f"{str(b['son_degisiklik'] or '-'):15} {b['durum']}")
        if yol.exists():
            h = sha256(yol)
            if b["sha256"] and b["sha256"] != h:
                print("   ! dosya değişmiş, sha256 tutmuyor")
                hatalar.append(f"{b['id']}: sha256 tutmuyor")
            elif not b["sha256"]:
                print(f"   sha256: {h}")
        elif b["durum"] == "aktif":
            hatalar.append(f"{b['id']}: aktif ama dosya yok")

    kayitli = {b["dosya"] for b in belgeler}
    for f in KAYNAK_KLASORU.iterdir():
        if f.suffix in (".pdf", ".html") and f.name not in kayitli:
            print("   ! listede olmayan dosya:", f.name)

    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
