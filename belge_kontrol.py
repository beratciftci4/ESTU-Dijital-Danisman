"""
belgeler.yaml'daki kayıtları kontrol eder, pdfler/ klasörüyle karşılaştırır.

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
PDF_KLASORU = KLASOR / "pdfler"

ALANLAR = ["id", "ad", "dosya", "url", "yayim", "yururluk", "son_degisiklik",
           "dayanak", "indirme_tarihi", "sha256", "durum", "not"]
TARIHLER = ["yayim", "yururluk", "son_degisiklik", "indirme_tarihi"]


def belgeleri_oku(yol=KLASOR / "belgeler.yaml"):
    with open(yol, encoding="utf-8") as f:
        return yaml.safe_load(f)


def hatalari_bul(belgeler):
    hatalar = []
    idler = set()
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
        if not re.fullmatch(r"[a-z0-9_]+\.pdf", b["dosya"]):
            hatalar.append(f"{bid}: dosya adı sadece a-z, 0-9, _ olmalı")

        if unicodedata.normalize("NFC", b["ad"]) != b["ad"]:
            hatalar.append(f"{bid}: ad NFC değil, türkçe karakterler bozuk olabilir")

        for alan in TARIHLER:
            deger = b[alan]
            if deger is not None and not isinstance(deger, date):
                hatalar.append(f"{bid}: {alan} YYYY-AA-GG olmalı ({deger})")

        if b["durum"] not in ("bekleniyor", "aktif"):
            hatalar.append(f"{bid}: durum bekleniyor ya da aktif olmalı")

        # aktif belgede tarih ve hash boş kalmasın
        if b["durum"] == "aktif":
            for alan in ["yururluk", "indirme_tarihi", "sha256"]:
                if not b[alan]:
                    hatalar.append(f"{bid}: aktif ama {alan} boş")
    return hatalar


def sha256(yol):
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def main():
    belgeler = belgeleri_oku()
    hatalar = hatalari_bul(belgeler)
    for h in hatalar:
        print("HATA:", h)

    print(f"\n{'id':20} {'pdf':5} {'yürürlük':12} {'son değişiklik':15} durum")
    for b in belgeler:
        yol = PDF_KLASORU / b["dosya"]
        var = "var" if yol.exists() else "yok"
        print(f"{b['id']:20} {var:5} {str(b['yururluk'] or '-'):12} "
              f"{str(b['son_degisiklik'] or '-'):15} {b['durum']}")
        if yol.exists():
            h = sha256(yol)
            if b["sha256"] and b["sha256"] != h:
                print("   ! pdf değişmiş, sha256 tutmuyor")
            elif not b["sha256"]:
                print(f"   sha256: {h}")

    kayitli = {b["dosya"] for b in belgeler}
    for pdf in PDF_KLASORU.glob("*.pdf"):
        if pdf.name not in kayitli:
            print("   ! listede olmayan pdf:", pdf.name)

    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
