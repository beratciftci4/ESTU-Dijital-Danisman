"""
4. aşama: hibrit arama.

BM25 (kelime) ve e5 (anlam) sıralamalarını Reciprocal Rank Fusion ile birleştiriyoruz:
    skor(parça) = 1 / (60 + BM25 sırası) + 1 / (60 + e5 sırası)
Böylece iki yöntemin skor ölçeklerini birbirine benzetmekle uğraşmıyoruz, sadece sıralar önemli.

Bölüm seçilince sadece o bölüme uyan parçalarda aranıyor: genel belgeler + bölümün fakültesinin
staj yönergesi + bölümün kendi Bologna sayfaları. BM25 her bölüm için kendi parçalarıyla ayrı
kuruluyor, böylece başka bölümlerin ders planları kelime ağırlıklarını (idf) etkilemiyor.

    python arama.py "Kaç AKTS üst sınırım var?"
"""
import re
import sys

import numpy as np
from rank_bm25 import BM25Okapi

from belge_kontrol import bolum_ve_yil, ders_plani_mi, programlari_oku
from indeks import Gomucu, arama_metni, indeksi_yukle, kelimeler, soru_kelimeleri, turkce_kucuk

RRF_K = 60
OZET_SIRALAMASI = True   # elle yazılmış özetlerle benzerlik de üçüncü sıralama olarak ekleniyor
OZET_AGIRLIGI = 1.0


class Arayici:
    def __init__(self, gomucu=None):
        self.parcalar, self.faiss, self.sahip = indeksi_yukle()
        _, programlar = programlari_oku()
        self.fakulte = {p["id"]: p["fakulte"] for p in programlar}
        self.program_adi = {p["id"]: p["ad"] for p in programlar}
        self._kelimeler = [kelimeler(arama_metni(p)) for p in self.parcalar]
        self._alt = {}            # program -> (parça sıraları, BM25)
        self._gomucu = gomucu

    def izinli_mi(self, p, program):
        """program None: hepsi, "genel": sadece genel belgeler, yoksa o bölümün belgeleri.
        "istatistik@2024" gibi yıllı anahtarda ders planı olarak sadece o yılın planı kullanılır,
        yılsızda sadece Bologna'daki güncel plan (aynı yarıyıl üç kez çıkmasın diye)."""
        plan = ders_plani_mi(p["belge_id"])
        program, yil = bolum_ve_yil(program)
        if plan and program not in (None, "genel") and plan[1] != yil:
            return False
        if program is None or p.get("kapsam", "genel") == "genel":
            return True
        if program == "genel":
            return False
        return p["kapsam"] in (f"program:{program}", f"fakulte:{self.fakulte[program]}")

    def temiz_soru(self, soru, program):
        """Seçili bölümün adını sorudan çıkarır: "Kimya bölümünde staj zorunlu mu?" -> "staj zorunlu mu?".
        Bölüm zaten seçili; ad kalırsa o bölümün adıyla dolu ders planı sayfaları öne çıkıyor."""
        program = bolum_ve_yil(program)[0]
        if program in (None, "genel"):
            return soru
        ad = turkce_kucuk(self.program_adi[program])
        kucuk = turkce_kucuk(soru)          # turkce_kucuk harf sayısını değiştirmiyor, konumlar aynı
        # adın kendisi + hal ekleri ("biyolojide", "fiziğin" değil ama "fizikte"); "istatistiksel" eşleşmez
        ekler = "nin|nın|nun|nün|in|ın|un|ün|deki|daki|de|da|te|ta|den|dan|ten|tan|ye|ya|yi|yı|e|a|i|ı"
        desen = rf"\b{re.escape(ad)}(?:'?(?:{ekler}))?\b(\s+(bölüm|programı?|öğrenci)\w*)?"
        temiz = soru
        for m in reversed(list(re.finditer(desen, kucuk))):
            temiz = temiz[:m.start()] + temiz[m.end():]
        temiz = re.sub(r"\s+", " ", temiz).strip()
        return temiz if len(temiz) >= 5 else soru

    def alt_kume(self, program=None):
        if program not in self._alt:
            idx = np.array([i for i, p in enumerate(self.parcalar) if self.izinli_mi(p, program)])
            self._alt[program] = (idx, BM25Okapi([self._kelimeler[i] for i in idx]))
        return self._alt[program]

    def bm25_icin(self, program=None):
        return self.alt_kume(program)[1]

    @property
    def bm25(self):
        return self.bm25_icin(None)

    @property
    def gomucu(self):
        if self._gomucu is None:          # model ilk soruda yükleniyor
            self._gomucu = Gomucu()
        return self._gomucu

    def bm25_skorlari(self, soru, program=None):
        return self.bm25_icin(program).get_scores(soru_kelimeleri(soru))

    def soru_vektoru(self, soru):
        """Aynı soru için vektörü bir kez hesaplıyoruz (kısa cevap da kullanıyor)."""
        if getattr(self, "_son_soru", None) != soru:
            self._son_soru, self._son_vektor = soru, self.gomucu.soru(soru)
        return self._son_vektor

    def e5_skorlari(self, soru, program=None):
        """Her parça için en benzer penceresinin kosinüs benzerliği (programın parçaları)."""
        benzerlik, idx = self.faiss.search(self.soru_vektoru(soru)[None], self.faiss.ntotal)
        skor = np.full(len(self.parcalar), -1.0)
        for b, i in zip(benzerlik[0], idx[0]):
            j = self.sahip[i]
            skor[j] = max(skor[j], b)
        return skor[self.alt_kume(program)[0]]

    def ozet_skorlari(self, soru, program=None):
        """Her parça için elle yazılmış özet cümlelerinden soruya en yakın olanın benzerliği."""
        from cevap import cumle_gecerli_mi, ozet_bolumleri, ozet_cumleleri, ozet_vektorleri
        if not hasattr(self, "_ozet_sahibi"):
            sira = {p["id"]: i for i, p in enumerate(self.parcalar)}
            self._ozet_sahibi = np.array([sira[pid] for pid, _, _ in ozet_cumleleri()])
            self._ozet_bolumu = ozet_bolumleri()
        benzerlik = ozet_vektorleri(self.gomucu) @ self.soru_vektoru(soru)
        # başka bölüme ait cümleler (ör. Kimya seçiliyken "Fizik bölümünde staj zorunludur") sayılmasın
        benzerlik = np.where([cumle_gecerli_mi(b, program) for b in self._ozet_bolumu], benzerlik, -1.0)
        skor = np.full(len(self.parcalar), -1.0)
        np.maximum.at(skor, self._ozet_sahibi, benzerlik)
        return skor[self.alt_kume(program)[0]]

    def ara(self, soru, k=5, yontem="hibrit", program=None):
        """[(parça, bilgi), ...] en iyiden kötüye. bilgi: skorlar ve sıralar.
        program: "istatistik" gibi bölüm id'si (programlar.yaml); None ise bütün parçalar."""
        idx = self.alt_kume(program)[0]
        bm = self.bm25_skorlari(soru, program) if yontem in ("hibrit", "bm25") else None
        e5 = self.e5_skorlari(soru, program) if yontem in ("hibrit", "e5") else None

        if yontem == "bm25":
            sira = np.argsort(-bm)
        elif yontem == "e5":
            sira = np.argsort(-e5)
        else:
            bm_sira = np.empty(len(bm), int)
            bm_sira[np.argsort(-bm)] = np.arange(1, len(bm) + 1)
            e5_sira = np.empty(len(e5), int)
            e5_sira[np.argsort(-e5)] = np.arange(1, len(e5) + 1)
            # BM25'te hiç ortak kelimesi olmayan parça o listeden puan almasın
            rrf = 1 / (RRF_K + e5_sira) + np.where(bm > 0, 1 / (RRF_K + bm_sira), 0)
            if OZET_SIRALAMASI:
                oz = self.ozet_skorlari(soru, program)
                oz_sira = np.empty(len(oz), int)
                oz_sira[np.argsort(-oz)] = np.arange(1, len(oz) + 1)
                rrf += OZET_AGIRLIGI / (RRF_K + oz_sira)
            sira = np.argsort(-rrf)

        sonuc = []
        for i in sira[:k]:
            bilgi = {}
            if bm is not None:
                bilgi["bm25"] = float(bm[i])
            if e5 is not None:
                bilgi["e5"] = float(e5[i])
            sonuc.append((self.parcalar[idx[i]], bilgi))
        return sonuc


if __name__ == "__main__":
    a = Arayici()
    for p, b in a.ara(" ".join(sys.argv[1:]) or "Kaç AKTS üst sınırım var?", program="istatistik"):
        print(f"{p['id']:40} s.{p['sayfa_bas']}  {b}")
