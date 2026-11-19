"""
6. aşama: Streamlit arayüzü.

    streamlit run app.py

Hiçbir ücretli API kullanmıyor. Cevaplar resmi metinlerin kendisi.
"""
import html

import streamlit as st
import yaml

from arama import Arayici
from belge_kontrol import KLASOR
from cevap import cevapla, tarih

st.set_page_config(page_title="ESTÜ Dijital Danışman", page_icon="📘", layout="centered")

ORNEK_SORULAR = [
    "Bir dönemde en fazla kaç AKTS alabilirim?",
    "Mezuniyet şartları neler?",
    "Tek ders sınavına kimler girebilir?",
    "Mazeret sınavına nasıl başvurulur?",
    "Kaç iş günü staj yapmalıyım?",
    "Derslere devam zorunluluğu yüzde kaç?",
]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@400;500&display=swap');

:root {
  --kagit: #F6F7F9; --murekkep: #1D2433; --bordo: #8A1C2B; --cizgi: #D8DCE4; --soluk: #5B6272;
  --yesil: #2E6B5B; --amber: #9A6400;
}
html, body, [class*="css"], .stMarkdown, .stTextInput input, button {
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}
.block-container { max-width: 760px; padding-top: 2.5rem; }

div.baslik { font-size: 2.1rem; line-height: 1.15; font-weight: 700; color: var(--murekkep); letter-spacing: -0.01em; margin: 0; }
.baslik span { color: var(--bordo); }
div.altbaslik { color: var(--soluk); font-size: 1rem; line-height: 1.5; margin: .35rem 0 1.5rem; max-width: 60ch; }

.durum { border-left: 4px solid var(--soluk); padding: .55rem .9rem; margin: 1.25rem 0 .5rem;
         background: #fff; color: var(--murekkep); font-size: .98rem; }
.durum.bulundu { border-color: var(--yesil); }
.durum.belirsiz { border-color: var(--amber); }

.kaynak { padding: 1.1rem 0 .4rem; border-top: 1px solid var(--cizgi); }
div.kaynak-belge { color: var(--soluk); font-size: .85rem; margin: 0; }
div.kaynak-madde { color: var(--bordo); font-size: 1.35rem; font-weight: 600; margin: .1rem 0 0; line-height: 1.3; }
.kaynak-madde small { color: var(--murekkep); font-size: 1rem; font-weight: 500; }
.alinti { font-family: 'IBM Plex Serif', Georgia, serif; font-size: 1.02rem; line-height: 1.65;
          color: var(--murekkep); border-left: 2px solid var(--cizgi); padding: .1rem 0 .1rem 1rem; margin: .7rem 0; }
.alinti p { margin: 0 0 .55rem; }
div.kunye { color: var(--soluk); font-size: .85rem; margin: .2rem 0 .3rem; }
.kunye a { color: var(--bordo); }
div.ocr { color: var(--amber); font-size: .85rem; }

section[data-testid="stSidebar"] { background: #fff; border-right: 1px solid var(--cizgi); }
.belge-satir { font-size: .88rem; line-height: 1.4; margin: 0 0 .7rem; color: var(--murekkep); }
.belge-satir span { color: var(--soluk); display: block; font-size: .8rem; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
"""


@st.cache_resource(show_spinner="Arama indeksi yükleniyor (ilk açılışta model indirilebilir)...")
def arayici_yukle():
    a = Arayici()
    _ = a.gomucu  # modeli şimdi yükle, ilk soruda beklemesin (tek başına yazınca streamlit ekrana basıyor)
    return a


@st.cache_data
def belgeler():
    return yaml.safe_load((KLASOR / "belgeler.yaml").read_text(encoding="utf-8"))


def kenar_cubugu():
    with st.sidebar:
        st.markdown("#### Kaynak belgeler")
        st.caption("Cevaplar yalnızca bu belgelerden geliyor.")
        for b in belgeler():
            if b["durum"] != "aktif":
                continue
            if b["yururluk"]:
                bilgi = f"Yürürlük {tarih(str(b['yururluk']))}"
                if b["son_degisiklik"]:
                    bilgi += f", son değişiklik {tarih(str(b['son_degisiklik']))}"
            else:
                bilgi = f"Web sayfası, erişim {tarih(str(b['indirme_tarihi']))}"
            st.markdown(f'<p class="belge-satir"><a href="{html.escape(b["url"])}" target="_blank">'
                        f'{html.escape(b["ad"])}</a><span>{bilgi}</span></p>', unsafe_allow_html=True)
        st.markdown("#### Nasıl çalışır")
        st.caption(
            "Sorunuz hem kelime eşleşmesiyle (BM25) hem anlam benzerliğiyle (e5) aranır. "
            "En uygun maddeler, ilgili fıkraları seçilerek gösterilir. Metin üretilmez, "
            "gördüğünüz her cümle resmi belgeden alınmıştır.")
        st.caption("Bu araç resmi görüş değildir. Kesin bilgi için Öğrenci İşleri'ne "
                   "ya da akademik danışmanınıza başvurun.")


def kaynak_goster(k):
    madde_html = html.escape(k["konum"])
    if k["baslik"]:
        madde_html += f' <small>{html.escape(k["baslik"])}</small>'
    alinti = "".join(f"<p>{html.escape(a)}</p>" for a in k["alinti"])
    sayfa_html = f'Sayfa {html.escape(k["sayfa"])}. ' if k["sayfa"] else ""
    ocr = ('<div class="ocr">Bu belge taranmış PDF, metin OCR ile okundu. '
           'Önemli kararlar için asıl belgeye bakın.</div>') if k["ocr"] else ""
    st.markdown(
        f'<div class="kaynak"><div class="kaynak-belge">{html.escape(k["belge"])}</div>'
        f'<div class="kaynak-madde">{madde_html}</div>'
        f'<div class="alinti">{alinti}</div>'
        f'<div class="kunye">{sayfa_html}{html.escape(k["gecerlilik"])}. '
        f'<a href="{html.escape(k["url"])}" target="_blank">Belgeyi aç</a></div>{ocr}</div>',
        unsafe_allow_html=True)
    with st.expander("Maddenin tamamını göster"):
        st.text(k["tam_metin"])


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    kenar_cubugu()
    st.markdown('<div class="baslik">ESTÜ <span>Dijital Danışman</span></div>'
                '<div class="altbaslik">Eğitim-öğretim yönetmeliği, staj yönergesi ve İstatistik bölümü '
                'ders planı hakkındaki sorularınızı resmi metinden, madde ve sayfa numarasıyla yanıtlar.</div>',
                unsafe_allow_html=True)

    if "soru" not in st.session_state:
        st.session_state.soru = ""
    secilen = st.pills("Örnek sorular", ORNEK_SORULAR, label_visibility="collapsed", key="ornek")
    if secilen and secilen != st.session_state.get("son_ornek"):
        st.session_state.soru = secilen
        st.session_state.son_ornek = secilen

    with st.form("soru_formu", border=False):
        soru = st.text_input("Sorunuz", key="soru", placeholder="Örn. Yaz okulunda en fazla kaç AKTS alabilirim?")
        sor = st.form_submit_button("Sor", type="primary")

    if not (sor or secilen) or not soru.strip():
        return

    arayici = arayici_yukle()
    with st.spinner("Belgelerde aranıyor..."):
        c = cevapla(soru, arayici)

    st.markdown(f'<div class="durum {c["durum"]}">{html.escape(c["mesaj"])}</div>', unsafe_allow_html=True)
    for k in c["kaynaklar"]:
        kaynak_goster(k)


main()
