"""
Hugging Face tokenizer.json (Unigram) -> SentencePiece modeli.

e5-small'un tokenizer.json'ı belleğe yüklenince ~300 MB yer kaplıyor. Aynı sözlüğü
SentencePiece formatına çevirince ~70 MB. Ücretsiz Streamlit sunucusunun bellek sınırı
düşük olduğu için uygulama bu küçük dosyayı (indeks/tokenizer.model) kullanıyor.

Çıktının tokenizer.json ile birebir aynı token id'lerini verdiği tests/test_indeks.py'de
kontrol ediliyor (model/tokenizer.json varsa).

    python tokenizer_donustur.py model/tokenizer.json indeks/tokenizer.model
"""
import base64
import json
import sys

from sentencepiece import sentencepiece_model_pb2 as pb


def donustur(json_yolu, cikti_yolu):
    t = json.load(open(json_yolu, encoding="utf-8"))
    m = pb.ModelProto()
    for i, (parca, skor) in enumerate(t["model"]["vocab"]):
        p = m.pieces.add()
        p.piece, p.score = parca, skor
        if i == t["model"]["unk_id"]:
            p.type = pb.ModelProto.SentencePiece.UNKNOWN
        elif parca in ("<s>", "<pad>", "</s>", "<mask>"):
            p.type = pb.ModelProto.SentencePiece.CONTROL
        else:
            p.type = pb.ModelProto.SentencePiece.NORMAL
    # id'ler Hugging Face'teki sırayla aynı kalsın: <s>=0, <pad>=1, </s>=2, <unk>=3
    ts = m.trainer_spec
    ts.model_type = pb.TrainerSpec.UNIGRAM
    ts.vocab_size = len(t["model"]["vocab"])
    ts.unk_id, ts.bos_id, ts.eos_id, ts.pad_id = 3, 0, 2, 1
    ts.unk_piece, ts.bos_piece, ts.eos_piece, ts.pad_piece = "<unk>", "<s>", "</s>", "<pad>"
    # tokenizer.json'daki normalizer: Precompiled (nmt_nfkc) + çoklu boşlukları teke indirme,
    # pre_tokenizer: Metaspace (▁, başa boşluk ekle)
    ns = m.normalizer_spec
    ns.name = "nmt_nfkc"
    ns.precompiled_charsmap = base64.b64decode(t["normalizer"]["normalizers"][0]["precompiled_charsmap"])
    ns.add_dummy_prefix = True
    ns.remove_extra_whitespaces = True
    ns.escape_whitespaces = True
    open(cikti_yolu, "wb").write(m.SerializeToString())


if __name__ == "__main__":
    donustur(sys.argv[1], sys.argv[2])
