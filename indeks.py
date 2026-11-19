"""
3. aşama: arama indeksi.

    python indeks.py        -> indeks/ klasörünü (yeniden) oluşturur

İki tür indeks var:
  - BM25 (kelime eşleşmesi): hızlı kurulduğu için dosyaya yazmıyoruz, açılışta kuruluyor
  - e5-small embedding + FAISS (anlam benzerliği): vektörler indeks/ altına kaydediliyor

Model: intfloat/multilingual-e5-small'un ONNX + int8 hali (Xenova/multilingual-e5-small).
~118 MB, CPU'da çalışıyor, hiçbir ücretli servise bağlanmıyor. model/ klasöründe yoksa
Hugging Face'ten (ücretsiz) indiriliyor.
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import faiss
import numpy as np
import onnxruntime as ort
import sentencepiece as spm

from belge_kontrol import KLASOR

INDEKS_KLASORU = KLASOR / "indeks"
PARCA_DOSYASI = KLASOR / "cikti" / "parcalar.jsonl"
MODEL_KLASORU = Path(os.environ.get("DANISMAN_MODEL_KLASORU", KLASOR / "model"))
MODEL_REPO = "Xenova/multilingual-e5-small"
MODEL_DOSYALARI = {"onnx/model_quantized.onnx": "model_quantized.onnx"}
# tokenizer.json yerine onun SentencePiece hali (aynı token id'leri, ~230 MB daha az bellek),
# bkz. tokenizer_donustur.py
TOKENIZER = INDEKS_KLASORU / "tokenizer.model"
MAKS_TOKEN = 512

# embedding için parçaları en fazla bu kadar karakterlik pencerelere bölüyoruz.
# e5 en fazla 512 token alıyor, uzun maddelerin sonu kesilmesin diye.
PENCERE = 900


# ---------- Türkçe kelime ayırma (BM25 için) ----------

def turkce_kucuk(s):
    # Python'un lower()'ı "I"yı "i" yapıyor, Türkçede "ı" olmalı
    return s.replace("I", "ı").replace("İ", "i").lower()


ETKISIZ = set("""ve veya ile bu bir da de için olan olarak ise gibi ki mi mı mu mü ne
ya ancak her daha üzere tarafından göre kadar sonra önce ilgili""".split())
# "en çok", "en az" yönetmelikte anlamlı olduğu için etkisiz sayılmıyor
# soru kalıpları: belgede geçmedikleri için BM25'te sadece gürültü yapıyorlar
SORU_KELIMELERI = set("""kaç nedir nasıl hangi hangisi kimler kim var yok miyim mıyım misin
mısın mıdır midir mudur müdür olmalı olur gerekir gerekiyor gerekli lazım ben benim bana
acaba istiyorum alabilirim yapabilirim""".split())

# öğrencinin kullandığı kelime ile yönetmelikteki kelime farklı olabiliyor
ESANLAMLI = {
    "üst sınır": "en çok", "en fazla": "en çok", "maksimum": "en çok",
    "dondur": "kayıt hakkı saklı izinli",
    "kredi": "akts",
    "ortalama": "gno not ortalaması",
    "mezun": "mezuniyet diploma",
    "harç": "katkı payı",
    "devamsızlık": "devam",
}
# "bütünleme"yi "ek sınav"a eşlemiyoruz: ikisi aynı şey değil, yeni yönetmelikte bütünleme yok


def soru_kelimeleri(soru):
    """Sorudaki kelimeler: soru kalıpları atılır, eş anlamlılar eklenir."""
    kucuk = turkce_kucuk(soru)
    ekler = [karsilik for ifade, karsilik in ESANLAMLI.items() if ifade in kucuk]
    temiz = [k for k in re.findall(r"\S+", kucuk) if re.sub(r"\W", "", k) not in SORU_KELIMELERI]
    return kelimeler(" ".join(temiz + ekler))


def kelimeler(metin, kok_uzunlugu=5):
    """BM25 için kelimeler. Türkçe eklemeli olduğu için kelimenin ilk 5 harfini alıyoruz
    ("öğrencinin", "öğrenciler" -> "öğren"). Sayılar olduğu gibi kalıyor (45, 20/A gibi)."""
    metin = turkce_kucuk(metin)
    sonuc = []
    for k in re.findall(r"\d+(?:/[a-zçğıöşü])?|[a-zçğıöşüâîû]+", metin):
        if k in ETKISIZ or (len(k) < 2 and not k.isdigit()):
            continue
        sonuc.append(k if k[0].isdigit() else k[:kok_uzunlugu])
    return sonuc


def arama_metni(p):
    """Bir parçanın aranacak metni: belge adı + madde başlığı + metin."""
    etiket = p["belge_adi"]
    if p["tur"] in ("madde", "bent"):
        etiket += f" Madde {p['no']}"
    if p["baslik"]:
        etiket += f" {p['baslik']}"
    return f"{etiket}. {p['metin']}"


# ---------- embedding modeli ----------

def modeli_hazirla():
    """Model dosyaları yoksa Hugging Face'ten indirir (ücretsiz, hesap gerekmiyor)."""
    eksik = [k for k, v in MODEL_DOSYALARI.items() if not (MODEL_KLASORU / v).exists()]
    if not eksik:
        return
    from huggingface_hub import hf_hub_download
    MODEL_KLASORU.mkdir(parents=True, exist_ok=True)
    for kaynak in eksik:
        yol = hf_hub_download(MODEL_REPO, kaynak)
        (MODEL_KLASORU / MODEL_DOSYALARI[kaynak]).write_bytes(Path(yol).read_bytes())


class Gomucu:
    """Metni 384 boyutlu, birim uzunlukta vektöre çevirir (e5: mean pooling + normalize)."""

    def __init__(self):
        modeli_hazirla()
        self.sp = spm.SentencePieceProcessor(model_file=str(TOKENIZER))
        ayar = ort.SessionOptions()
        ayar.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
        ayar.enable_cpu_mem_arena = False   # tek tek vektörlediğimiz için büyük bellek havuzuna gerek yok
        # Not: ORT_ENABLE_BASIC ~45 MB daha az bellek kullanıyor ama int8 modelde vektörleri biraz
        # değiştiriyor (~1e-3), eşikler varsayılan seviyeyle ayarlandığı için varsayılanda kalıyoruz.
        self.oturum = ort.InferenceSession(str(MODEL_KLASORU / "model_quantized.onnx"), ayar,
                                           providers=["CPUExecutionProvider"])

    def token_idleri(self, metin):
        """<s> + metin + </s>, en fazla 512 token (Hugging Face tokenizer'ıyla aynı sonuç)."""
        return [0] + self.sp.encode(metin)[:MAKS_TOKEN - 2] + [2]

    def vektor(self, metinler, onek):
        # int8 model ölçekleri tüm grup üzerinden hesaplıyor, yani aynı metnin vektörü yanındaki
        # metinlere göre biraz değişiyor. Tekrarlanabilir olsun diye metinleri tek tek veriyoruz.
        sonuc = []
        for m in metinler:
            ids = np.array([self.token_idleri(f"{onek}: {m}")], dtype=np.int64)
            maske = np.ones_like(ids)
            cikti = self.oturum.run(None, {"input_ids": ids, "attention_mask": maske,
                                           "token_type_ids": np.zeros_like(ids)})[0]
            v = cikti.mean(axis=1)
            sonuc.append(v / np.linalg.norm(v, axis=1, keepdims=True))
        return np.vstack(sonuc).astype("float32")

    def soru(self, metin):
        return self.vektor([metin], "query")[0]


def pencerelere_bol(p):
    """Uzun parçayı fıkra sınırlarından bölüp her pencerenin başına etiketi koyar."""
    metin = arama_metni(p)
    if len(metin) <= PENCERE:
        return [metin]
    etiket = metin[: len(metin) - len(p["metin"])]
    pencereler, mevcut = [], ""
    for satir in p["metin"].split("\n"):
        while len(satir) > PENCERE:           # tek satır çok uzunsa cümle cümle böl
            kes = satir.rfind(". ", 0, PENCERE)
            kes = kes + 1 if kes > 0 else PENCERE
            pencereler.append(satir[:kes])
            satir = satir[kes:].strip()
        if mevcut and len(mevcut) + len(satir) > PENCERE:
            pencereler.append(mevcut)
            mevcut = ""
        mevcut = (mevcut + "\n" + satir).strip()
    if mevcut:
        pencereler.append(mevcut)
    return [etiket + p_ for p_ in pencereler]


# ---------- indeks kurma / yükleme ----------

def parcalari_oku():
    if not PARCA_DOSYASI.exists():
        # PDF okuma kütüphaneleri ağır, sadece gerektiğinde yükleniyor (uygulama bunlara ihtiyaç duymuyor)
        from ayristir import tum_belgeler
        parcalar = tum_belgeler()
    else:
        parcalar = [json.loads(s) for s in PARCA_DOSYASI.read_text(encoding="utf-8").splitlines()]
    return parcalar


def parca_ozeti(parcalar):
    return hashlib.sha256(json.dumps(parcalar, ensure_ascii=False, sort_keys=True)
                          .encode()).hexdigest()[:16]


def indeks_olustur(parcalar=None, gomucu=None):
    parcalar = parcalar or parcalari_oku()
    gomucu = gomucu or Gomucu()
    pencere_metinleri, pencere_sahibi = [], []
    for i, p in enumerate(parcalar):
        for m in pencerelere_bol(p):
            pencere_metinleri.append(m)
            pencere_sahibi.append(i)

    bas = time.time()
    vektorler = gomucu.vektor(pencere_metinleri, "passage")
    sure = time.time() - bas

    faiss_indeks = faiss.IndexFlatIP(vektorler.shape[1])   # birim vektörlerde iç çarpım = kosinüs
    faiss_indeks.add(vektorler)

    INDEKS_KLASORU.mkdir(exist_ok=True)
    faiss.write_index(faiss_indeks, str(INDEKS_KLASORU / "vektorler.faiss"))
    (INDEKS_KLASORU / "parcalar.json").write_text(
        json.dumps(parcalar, ensure_ascii=False, indent=0), encoding="utf-8")
    (INDEKS_KLASORU / "bilgi.json").write_text(json.dumps({
        "model": MODEL_REPO + " (onnx/model_quantized.onnx)",
        "parca_sayisi": len(parcalar),
        "pencere_sayisi": len(pencere_metinleri),
        "pencere_sahibi": pencere_sahibi,
        "parca_ozeti": parca_ozeti(parcalar),
        "olusturma_suresi_sn": round(sure, 1),
    }, ensure_ascii=False), encoding="utf-8")
    return len(parcalar), len(pencere_metinleri), sure


def indeksi_yukle():
    """(parcalar, faiss indeksi, pencere_sahibi) döndürür."""
    parcalar = json.loads((INDEKS_KLASORU / "parcalar.json").read_text(encoding="utf-8"))
    bilgi = json.loads((INDEKS_KLASORU / "bilgi.json").read_text(encoding="utf-8"))
    faiss_indeks = faiss.read_index(str(INDEKS_KLASORU / "vektorler.faiss"))
    assert faiss_indeks.ntotal == len(bilgi["pencere_sahibi"])
    return parcalar, faiss_indeks, np.array(bilgi["pencere_sahibi"])


def main():
    parca, pencere, sure = indeks_olustur()
    print(f"{parca} parça, {pencere} pencere, embedding {sure:.1f} sn -> {INDEKS_KLASORU.name}/")


if __name__ == "__main__":
    sys.exit(main())
