"""
"Mezun olmak için neyim eksik?" kontrolü.

Öğrencinin girdiği bilgileri (tamamlanan AKTS, GNO, kalan notlar, staj günü) sadece
kaynak belgelerdeki mezuniyet kurallarıyla karşılaştırır. Her satırda kuralın geçtiği madde var.

Kurallar:
  - Yönetmelik md. 25/1: lisansta en az 240 AKTS, ÇK/DZ/EK/FF/YZ notu yok, GNO en az 2,00
  - Fakültenin staj yönergesi: zorunlu staj süresi (programlar.yaml'da bölüm bölüm yazılı;
    Fen Fakültesi'nde Biyoloji, Fizik, İstatistik 20 iş günü, Kimya ve Matematik isteğe bağlı)
  - Tek Ders Sınavı Esasları 1. madde: tek dersten FF/YZ kalan, mezun olabilecek durumdaki öğrenci
"""

GEREKEN_AKTS = 240
GEREKEN_GNO = 2.00
ENGEL_NOTLAR = ["FF", "YZ", "DZ", "EK", "ÇK"]   # md. 25'te sayılan, mezuniyete engel notlar

KAYNAK_MEZUNIYET = "yonetmelik#madde-25"
KAYNAK_TEK_DERS = "tek_ders#bent-1"


def staj_kurali(program):
    """(gereken gün ya da None, kaynak parça id). Birim için staj_birimi()."""
    from belge_kontrol import programlari_oku
    fakulteler, programlar = programlari_oku()
    p = next(x for x in programlar if x["id"] == program)
    if p["staj_gunu"] is None:
        return None, fakulteler[p["fakulte"]]["staj_listesi"]
    return p["staj_gunu"], p.get("staj_kaynagi") or fakulteler[p["fakulte"]]["staj_maddesi"]


def staj_birimi(program):
    from belge_kontrol import programlari_oku
    fakulteler, programlar = programlari_oku()
    p = next(x for x in programlar if x["id"] == program)
    return p.get("staj_birimi") or fakulteler[p["fakulte"]]["staj_birimi"]


def kontrol(akts, gno, notlar, staj_gunu, program="istatistik"):
    """notlar: {"FF": 1, "YZ": 0, ...} -> kalan ders sayıları.
    Dönen liste: [{"ad", "tamam", "aciklama", "kaynak"}, ...] ve varsa "oneriler"."""
    satirlar = []

    eksik_akts = max(0, GEREKEN_AKTS - akts)
    satirlar.append({
        "ad": "En az 240 AKTS",
        "tamam": eksik_akts == 0,
        "aciklama": f"{akts:g} AKTS tamamlanmış." + (f" {eksik_akts:g} AKTS eksik." if eksik_akts else ""),
        "kaynak": KAYNAK_MEZUNIYET,
    })

    satirlar.append({
        "ad": "GNO en az 2,00",
        "tamam": gno >= GEREKEN_GNO,
        "aciklama": f"GNO {gno:.2f}".replace(".", ",") + ("." if gno >= GEREKEN_GNO else ", 2,00'ın altında."),
        "kaynak": KAYNAK_MEZUNIYET,
    })

    kalan = {n: s for n, s in notlar.items() if n in ENGEL_NOTLAR and s > 0}
    satirlar.append({
        "ad": "ÇK, DZ, EK, FF ve YZ notu olmaması",
        "tamam": not kalan,
        "aciklama": ("Bu notlardan ders yok." if not kalan else
                     "Kalan: " + ", ".join(f"{s} ders {n}" for n, s in kalan.items()) + "."),
        "kaynak": KAYNAK_MEZUNIYET,
    })

    gereken_staj, staj_kaynagi = staj_kurali(program)
    if gereken_staj is None:
        satirlar.append({
            "ad": "Zorunlu staj yok",
            "tamam": True,
            "aciklama": "Bu bölümde staj isteğe bağlı, mezuniyet için şart değil.",
            "kaynak": staj_kaynagi,
        })
        gereken_staj = 0
    else:
        birim = staj_birimi(program)
        satirlar.append({
            "ad": f"En az {gereken_staj} {birim} staj",
            "tamam": staj_gunu >= gereken_staj,
            "aciklama": f"{staj_gunu} {birim} staj." +
                        (f" {gereken_staj - staj_gunu} {birim} eksik." if staj_gunu < gereken_staj else ""),
            "kaynak": staj_kaynagi,
        })

    oneriler = []
    ff_yz = kalan.get("FF", 0) + kalan.get("YZ", 0)
    diger_engel = sum(s for n, s in kalan.items() if n not in ("FF", "YZ"))
    # tek ders sınavı: sadece tek dersten FF/YZ kalmış, mezun olabilecek durumdaki öğrenci
    if ff_yz == 1 and diger_engel == 0 and staj_gunu >= gereken_staj:
        oneriler.append({
            "metin": "Tek dersten FF/YZ kalmış görünüyorsunuz. O derste devam koşulunu sağladıysanız ve "
                     "o ders dışında mezuniyet için eksiğiniz yoksa (eksik AKTS'niz sadece bu dersten "
                     "geliyorsa) tek ders sınavına girebilirsiniz.",
            "kaynak": KAYNAK_TEK_DERS,
        })

    return {"mezun_olabilir": all(s["tamam"] for s in satirlar), "satirlar": satirlar, "oneriler": oneriler}
