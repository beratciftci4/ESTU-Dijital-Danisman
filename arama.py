"""
4. aşama: hibrit arama.

BM25 (kelime) ve e5 (anlam) sıralamalarını Reciprocal Rank Fusion ile birleştiriyoruz:
    skor(parça) = 1 / (60 + BM25 sırası) + 1 / (60 + e5 sırası)
Böylece iki yöntemin skor ölçeklerini birbirine benzetmekle uğraşmıyoruz, sadece sıralar önemli.

    python arama.py "Kaç AKTS üst sınırım var?"
"""
import sys

import numpy as np
from rank_bm25 import BM25Okapi

from indeks import Gomucu, arama_metni, indeksi_yukle, kelimeler, soru_kelimeleri

RRF_K = 60


class Arayici:
    def __init__(self, gomucu=None):
        self.parcalar, self.faiss, self.sahip = indeksi_yukle()
        self.bm25 = BM25Okapi([kelimeler(arama_metni(p)) for p in self.parcalar])
        self._gomucu = gomucu

    @property
    def gomucu(self):
        if self._gomucu is None:          # model ilk soruda yükleniyor
            self._gomucu = Gomucu()
        return self._gomucu

    def bm25_skorlari(self, soru):
        return self.bm25.get_scores(soru_kelimeleri(soru))

    def soru_vektoru(self, soru):
        """Aynı soru için vektörü bir kez hesaplıyoruz (kısa cevap da kullanıyor)."""
        if getattr(self, "_son_soru", None) != soru:
            self._son_soru, self._son_vektor = soru, self.gomucu.soru(soru)
        return self._son_vektor

    def e5_skorlari(self, soru):
        """Her parça için en benzer penceresinin kosinüs benzerliği."""
        benzerlik, idx = self.faiss.search(self.soru_vektoru(soru)[None], self.faiss.ntotal)
        skor = np.full(len(self.parcalar), -1.0)
        for b, i in zip(benzerlik[0], idx[0]):
            j = self.sahip[i]
            skor[j] = max(skor[j], b)
        return skor

    def ara(self, soru, k=5, yontem="hibrit"):
        """[(parça, bilgi), ...] en iyiden kötüye. bilgi: skorlar ve sıralar."""
        bm = self.bm25_skorlari(soru) if yontem in ("hibrit", "bm25") else None
        e5 = self.e5_skorlari(soru) if yontem in ("hibrit", "e5") else None

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
            sira = np.argsort(-rrf)

        sonuc = []
        for i in sira[:k]:
            bilgi = {}
            if bm is not None:
                bilgi["bm25"] = float(bm[i])
            if e5 is not None:
                bilgi["e5"] = float(e5[i])
            sonuc.append((self.parcalar[i], bilgi))
        return sonuc


if __name__ == "__main__":
    a = Arayici()
    for p, b in a.ara(" ".join(sys.argv[1:]) or "Kaç AKTS üst sınırım var?"):
        print(f"{p['id']:40} s.{p['sayfa_bas']}  {b}")
