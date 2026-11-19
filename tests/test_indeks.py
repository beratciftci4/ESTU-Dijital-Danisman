"""3. aşama testleri: BM25 kelime ayırma, embedding ve FAISS indeksi."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from indeks import (Gomucu, arama_metni, indeksi_yukle, kelimeler, parca_ozeti,
                    parcalari_oku, pencerelere_bol, turkce_kucuk)


@pytest.fixture(scope="module")
def indeks():
    return indeksi_yukle()


@pytest.fixture(scope="module")
def gomucu():
    return Gomucu()


def test_turkce_kucuk_harf():
    assert turkce_kucuk("IĞDIR İSTATİSTİK Işık") == "ığdır istatistik ışık"


def test_kelimeler():
    assert kelimeler("Öğrencinin 45 AKTS'lik derse kayıt yaptırabilir") == \
        ["öğren", "45", "akts", "lik", "derse", "kayıt", "yaptı"]
    # madde numaraları bozulmasın
    assert "20/a" in kelimeler("Madde 20/A")
    # aynı kökten kelimeler aynı terime düşsün
    assert kelimeler("öğrenciler")[0] == kelimeler("öğrencinin")[0]


def test_indeks_guncel():
    """Parçalar değiştiyse indeks de yeniden kurulmalı (python indeks.py)."""
    import json
    from indeks import INDEKS_KLASORU
    bilgi = json.loads((INDEKS_KLASORU / "bilgi.json").read_text(encoding="utf-8"))
    assert bilgi["parca_ozeti"] == parca_ozeti(parcalari_oku()), "indeks eski, python indeks.py çalıştır"


def test_her_parcanin_vektoru_var(indeks):
    parcalar, faiss_indeks, sahip = indeks
    assert set(sahip.tolist()) == set(range(len(parcalar)))
    assert faiss_indeks.ntotal == len(sahip)
    assert faiss_indeks.d == 384


def test_vektorler_birim_uzunlukta(indeks):
    _, faiss_indeks, _ = indeks
    v = faiss_indeks.reconstruct_n(0, faiss_indeks.ntotal)
    assert np.allclose(np.linalg.norm(v, axis=1), 1, atol=1e-3)


def test_pencereler_metin_kaybetmiyor(indeks):
    parcalar, _, _ = indeks
    for p in parcalar:
        pencereler = pencerelere_bol(p)
        birlesik = " ".join(pencereler)
        for kelime in p["metin"].split():
            assert kelime in birlesik, (p["id"], kelime)
        assert all(len(x) < 1400 for x in pencereler), p["id"]


def test_kayitli_vektor_yeniden_uretilebiliyor(indeks, gomucu):
    parcalar, faiss_indeks, sahip = indeks
    i = int(np.where(sahip == 0)[0][0])
    yeni = gomucu.vektor([pencerelere_bol(parcalar[0])[0]], "passage")[0]
    assert float(yeni @ faiss_indeks.reconstruct(i)) > 0.999


def test_anlamsal_arama_mantikli(indeks, gomucu):
    parcalar, faiss_indeks, sahip = indeks
    _, idx = faiss_indeks.search(gomucu.soru("Bir yarıyılda en çok kaç AKTS derse kayıt olabilirim?")[None], 20)
    bulunan = list(dict.fromkeys(parcalar[sahip[i]]["id"] for i in idx[0]))[:3]  # aynı parçanın pencereleri tek sayılır
    assert "yonetmelik#madde-10" in bulunan


def test_arama_metni_etiketli(indeks):
    parcalar, _, _ = indeks
    p = next(x for x in parcalar if x["id"] == "yonetmelik#madde-10")
    assert arama_metni(p).startswith(
        "Eskişehir Teknik Üniversitesi Ön Lisans ve Lisans Eğitim-Öğretim ve Sınav Yönetmeliği "
        "Madde 10 Kayıt yenileme ve ders kaydı.")


@pytest.mark.skipif(not (Path(__file__).parent.parent / "model" / "tokenizer.json").exists(),
                    reason="model/tokenizer.json yok (sadece dönüştürme kontrolü için gerekli)")
def test_sentencepiece_hf_tokenizer_ile_ayni(gomucu, indeks):
    """indeks/tokenizer.model, orijinal tokenizer.json ile birebir aynı id'leri vermeli."""
    import yaml
    from tokenizers import Tokenizer
    klasor = Path(__file__).parent
    hf = Tokenizer.from_file(str(klasor.parent / "model" / "tokenizer.json"))
    hf.enable_truncation(512)
    parcalar, _, _ = indeks
    metinler = ["passage: " + w for p in parcalar for w in pencerelere_bol(p)]
    for ad in ["soru_seti", "soru_seti_ayrik", "soru_seti_dogrulama"]:
        metinler += ["query: " + s["soru"] for s in yaml.safe_load((klasor / f"{ad}.yaml").read_text(encoding="utf-8"))]
    metinler += ["query: İIıi ÇĞÖŞÜ “tırnak” – ‒ … %80 3,50 20/A", "query: ＡＢＣ　😀 中文 ﬁ ½", "query: a\tb\nc  d"]
    for m in metinler:
        assert gomucu.token_idleri(m) == hf.encode(m).ids, m[:60]
