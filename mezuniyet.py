"""
"Mezun olmak için neyim eksik?" kontrolü.

Öğrencinin girdiği bilgileri (tamamlanan AKTS, GNO, kalan notlar, staj günü) sadece
kaynak belgelerdeki mezuniyet kurallarıyla karşılaştırır. Her satırda kuralın geçtiği madde var.

Kurallar:
  - Yönetmelik md. 25/1: önlisansta en az 120, lisansta en az 240 AKTS, ÇK/DZ/EK/FF/YZ notu yok, GNO en az 2,00
  - Fakültenin staj yönergesi: zorunlu staj süresi (programlar.yaml'da bölüm bölüm yazılı;
    Fen Fakültesi'nde Biyoloji, Fizik, İstatistik 20 iş günü, Kimya ve Matematik isteğe bağlı)
  - Tek Ders Sınavı Esasları 1. madde: tek dersten FF/YZ kalan, mezun olabilecek durumdaki öğrenci
"""

GEREKEN_AKTS = {"lisans": 240, "onlisans": 120}
GEREKEN_GNO = 2.00
ENGEL_NOTLAR = ["FF", "YZ", "DZ", "EK", "ÇK"]   # md. 25'te sayılan, mezuniyete engel notlar

KAYNAK_MEZUNIYET = "yonetmelik#madde-25"
KAYNAK_TEK_DERS = "tek_ders#bent-1"


def staj_kurali(program):
    """(gereken gün, None ya da "belirsiz", kaynak parça id). Birim için staj_birimi().
    None: staj isteğe bağlı. "belirsiz": staj zorunlu ama süresi belgelerde yazmıyor.
    "sor": belgeler stajın zorunlu olup olmadığını netleştirmiyor (Spor Bilimleri)."""
    from belge_kontrol import programlari_oku
    fakulteler, programlar = programlari_oku()
    p = next(x for x in programlar if x["id"] == program)
    if p.get("staj_durumu_belirsiz"):
        return "sor", p.get("staj_kaynagi") or fakulteler[p["fakulte"]]["staj_listesi"]
    if p.get("staj_suresi_belirsiz"):
        return "belirsiz", p.get("staj_kaynagi") or fakulteler[p["fakulte"]]["staj_listesi"]
    if p["staj_gunu"] is None:
        return None, p.get("staj_kaynagi") or fakulteler[p["fakulte"]]["staj_listesi"]
    return p["staj_gunu"], p.get("staj_kaynagi") or fakulteler[p["fakulte"]]["staj_maddesi"]


def staj_birimi(program):
    from belge_kontrol import programlari_oku
    fakulteler, programlar = programlari_oku()
    p = next(x for x in programlar if x["id"] == program)
    return p.get("staj_birimi") or fakulteler[p["fakulte"]]["staj_birimi"]


def duzey(program):
    """"lisans" ya da "onlisans" (meslek yüksekokulları). Fakülteden geliyor, programda da yazılabilir."""
    from belge_kontrol import programlari_oku
    fakulteler, programlar = programlari_oku()
    p = next(x for x in programlar if x["id"] == program)
    return p.get("duzey") or fakulteler[p["fakulte"]].get("duzey", "lisans")


def kontrol(akts, gno, notlar, staj_gunu, program="istatistik"):
    """notlar: {"FF": 1, "YZ": 0, ...} -> kalan ders sayıları.
    Dönen liste: [{"ad", "tamam", "aciklama", "kaynak"}, ...] ve varsa "oneriler"."""
    satirlar = []

    gereken_akts = GEREKEN_AKTS[duzey(program)]
    eksik_akts = max(0, gereken_akts - akts)
    satirlar.append({
        "ad": f"En az {gereken_akts} AKTS",
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
    if gereken_staj == "sor":
        # belgeler çelişkili: mezuniyeti engellemiyoruz ama "tamam" da demiyoruz
        satirlar.append({
            "ad": "Staj (belgelerde net değil)",
            "tamam": True,
            "belirsiz": True,
            "aciklama": "Fakülte staj yönergesi bu bölümde en az 40 gün staj öngörüyor, ama güncel ders "
                        "planında staj dersi görünmüyor. Staj yapman gerekip gerekmediğini bölümüne sor.",
            "kaynak": staj_kaynagi,
        })
        gereken_staj = 0
    elif gereken_staj == "belirsiz":
        satirlar.append({
            "ad": "Zorunlu staj (süresi belgelerde yok)",
            "tamam": staj_gunu > 0,
            "aciklama": "Ders planında zorunlu staj dersleri var ama süresi yönergede ve Bologna sayfasında "
                        "yazmıyor; ne kadar staj yapman gerektiğini bölümüne sor.",
            "kaynak": staj_kaynagi,
        })
        gereken_staj = 1
    elif gereken_staj is None:
        satirlar.append({
            "ad": "Zorunlu staj yok",
            "tamam": True,
            "aciklama": "Bu bölümde staj mezuniyet için şart değil.",
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


# Yönetmelik md. 18/4: harf notları ve katsayıları. md. 8: ders kredileri AKTS kredisidir.
HARF_KATSAYI = {"AA": 4.00, "AB": 3.70, "BA": 3.30, "BB": 3.00, "BC": 2.70, "CB": 2.30,
                "CC": 2.00, "CD": 1.70, "DC": 1.30, "DD": 1.00, "FF": 0.00,
                "DZ": 0.00}   # md. 18/5-c: DZ, FF ile eş değer
KAYNAK_KATSAYI = "yonetmelik#madde-18"
KAYNAK_ORTALAMA = "yonetmelik#madde-19"


def not_ortalamasi(dersler, onceki_gno=None, onceki_akts=0.0):
    """md. 19/1: ortalama = sum(AKTS x katsayı) / sum(AKTS).
    dersler: [{"akts", "not", "eski_not"(isteğe bağlı)}]. Katsayısı olmayan notlar (YT, YZ, EK...)
    ortalamaya girmez. eski_not: tekrar edilen dersin önceki notu; md. 19/3'e göre GNO'da
    son not esas alındığı için eskisi çıkarılır.
    Dönen: {"dno", "donem_akts", "gno", "toplam_akts"}; hesaplanamayan değer None."""
    pay, payda = 0.0, 0.0
    for d in dersler:
        if d.get("not") in HARF_KATSAYI and d.get("akts"):
            pay += d["akts"] * HARF_KATSAYI[d["not"]]
            payda += d["akts"]
    dno = round(pay / payda, 2) if payda else None

    gno = None
    if onceki_gno is not None and onceki_akts:
        g_pay = onceki_gno * onceki_akts + pay
        g_payda = onceki_akts + payda
        for d in dersler:
            if d.get("eski_not") in HARF_KATSAYI and d.get("akts") and d.get("not") in HARF_KATSAYI:
                g_pay -= d["akts"] * HARF_KATSAYI[d["eski_not"]]
                g_payda -= d["akts"]
        gno = round(g_pay / g_payda, 2) if g_payda > 0 else None
        toplam = g_payda
    else:
        gno, toplam = dno, payda
    return {"dno": dno, "donem_akts": payda, "gno": gno, "toplam_akts": toplam}
