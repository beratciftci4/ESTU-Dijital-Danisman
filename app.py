"""
6. aşama: Streamlit arayüzü.

    streamlit run app.py

Hiçbir ücretli API kullanmıyor. Kısa cevaplar elle yazılmış özetlerden, alıntılar resmi metnin aynısı.
"""
import hashlib
import html

import streamlit as st
import yaml

import json

from arama import Arayici
from belge_kontrol import KLASOR, programlari_oku
from cevap import atif, cevapla, gecerlilik, tarih
from mezuniyet import ENGEL_NOTLAR, kontrol

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

div.cevap { background: #fff; border: 1px solid var(--cizgi); border-top: 3px solid var(--bordo);
            padding: 1.1rem 1.25rem .9rem; margin: 1.25rem 0 .4rem; }
div.cevap.belirsiz { border-top-color: var(--amber); }
div.cevap .uyari { color: var(--amber); font-size: .88rem; font-weight: 500; margin: 0 0 .5rem; }
div.cevap p.metin { font-size: 1.12rem; line-height: 1.6; color: var(--murekkep); margin: 0 0 .7rem; }
div.cevap .dayanak { color: var(--soluk); font-size: .84rem; line-height: 1.45; }
div.ara-baslik { color: var(--soluk); font-size: .9rem; font-weight: 600; margin: 1.6rem 0 0; }

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

div.kural { display: grid; grid-template-columns: 4.2rem 1fr; gap: .2rem .9rem; padding: .8rem 0;
            border-top: 1px solid var(--cizgi); color: var(--murekkep); }
div.kural .etiket { font-weight: 600; font-size: .85rem; padding-top: .1rem; }
div.kural .etiket.tamam { color: var(--yesil); }
div.kural .etiket.eksik { color: var(--bordo); }
div.kural .ad { font-weight: 600; }
div.kural .kaynakca { color: var(--soluk); font-size: .82rem; grid-column: 2; }

section[data-testid="stSidebar"] { background: #fff; border-right: 1px solid var(--cizgi); }
.belge-satir { font-size: .88rem; line-height: 1.4; margin: 0 0 .7rem; color: var(--murekkep); }
.belge-satir span { color: var(--soluk); display: block; font-size: .8rem; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
"""


@st.cache_resource(max_entries=1, show_spinner="Arama indeksi yükleniyor (ilk açılışta model indirilebilir)...")
def arayici_yukle(kod_surumu):
    """kod_surumu: arama.py ve indeks.py değişince önbellek yenilensin diye (yoksa Streamlit Cloud
    yeni kodla eski Arayici nesnesini kullanmaya devam ediyor)."""
    a = Arayici()
    _ = a.gomucu  # modeli şimdi yükle, ilk soruda beklemesin (tek başına yazınca streamlit ekrana basıyor)
    return a


def surum(*dosyalar):
    """Dosyaların içeriğinden kısa bir özet. Önbelleğe alınan fonksiyonlara argüman olarak veriliyor,
    dosya değişince Streamlit Cloud eski sonucu kullanmaya devam etmesin diye."""
    return hashlib.sha256(b"".join((KLASOR / f).read_bytes() for f in dosyalar)).hexdigest()[:16]


def kod_surumu():
    return surum("arama.py", "indeks.py", "cevap.py", "ozetler.yaml", "programlar.yaml", "indeks/parcalar.json")


@st.cache_data
def parca_sozlugu(dosya_surumu):
    parcalar = json.loads((KLASOR / "indeks" / "parcalar.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in parcalar}


@st.cache_data
def belgeler(dosya_surumu):
    return yaml.safe_load((KLASOR / "belgeler.yaml").read_text(encoding="utf-8"))


@st.cache_data
def programlar(dosya_surumu):
    fakulteler, liste = programlari_oku()
    return fakulteler, {p["id"]: p for p in liste}


def gecerli_mi(belge, program):
    """Belge seçilen bölüm için geçerli mi (arama.py'deki izinli_mi ile aynı kural)."""
    if belge.get("kapsam", "genel") == "genel":
        return True
    if program is None:
        return False
    fakulte = programlar(surum("programlar.yaml"))[1][program]["fakulte"]
    return belge["kapsam"] in (f"program:{program}", f"fakulte:{fakulte}")


def bolum_sec():
    """Bölüm seçimi. Adres çubuğunda ?bolum=fizik olarak kalıyor, link paylaşılabiliyor."""
    fakulteler, liste = programlar(surum("programlar.yaml"))
    varsayilan = st.query_params.get("bolum")
    secenekler = list(liste)
    secim = st.selectbox(
        "Bölümün", secenekler, index=secenekler.index(varsayilan) if varsayilan in liste else None,
        format_func=lambda p: f"{liste[p]['ad']} ({fakulteler[liste[p]['fakulte']]['ad']})",
        placeholder="Bölümünü seç", key="bolum")
    if secim:
        st.query_params["bolum"] = secim
    else:
        st.query_params.pop("bolum", None)
        st.caption("Bölüm seçmezsen sadece herkes için ortak olan yönetmelik ve yönergelerde aranır; "
                   "staj ve ders planı soruları için bölümünü seç.")
    return secim


def kenar_cubugu(program):
    with st.sidebar:
        st.markdown("#### Kaynak belgeler")
        st.caption("Cevaplar yalnızca bu belgelerden geliyor.")
        for b in belgeler(surum("belgeler.yaml")):
            if b["durum"] != "aktif" or not gecerli_mi(b, program):
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
            "Kısa cevap, her madde için önceden elle yazılmış sade özet cümlelerinden seçilir; "
            "yapay zekâ ile anlık metin üretilmez. Altındaki alıntılar resmi metnin aynısıdır.")
        st.caption("Şu an Fen Fakültesi bölümleri var, diğer fakülteler sırayla ekleniyor. Yönetmelik ve "
                   "usul-esaslar bütün lisans öğrencileri için ortak; staj yönergesi fakülteye, ders "
                   "planı ve mezuniyet koşulları bölüme özel.")
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


def soru_sekmesi(program):
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

    arayici = arayici_yukle(kod_surumu())
    with st.spinner("Belgelerde aranıyor..."):
        c = cevapla(soru, arayici, program=program or "genel")

    if not c.get("ozet"):
        st.markdown(f'<div class="durum {c["durum"]}">{html.escape(c["mesaj"])}</div>', unsafe_allow_html=True)
        return

    uyari = ""
    if c["durum"] == "belirsiz":
        uyari = ('<div class="uyari">Belgelerde bu soruya birebir uyan bir hüküm bulamadım. '
                 'En yakın bilgi aşağıda, maddeleri kontrol edin.</div>')
    st.markdown(
        f'<div class="cevap {c["durum"]}">{uyari}<p class="metin">{html.escape(c["ozet"]["metin"])}</p>'
        f'<div class="dayanak">Dayanak: {html.escape("; ".join(c["ozet"]["dayanak"]))}. '
        'Bu özet resmi metnin sade anlatımıdır; bağlayıcı olan aşağıdaki madde metinleridir.</div></div>',
        unsafe_allow_html=True)
    st.markdown('<div class="ara-baslik">Resmi metin, okumak isteyenler için</div>', unsafe_allow_html=True)
    for k in c["kaynaklar"]:
        kaynak_goster(k)


def mezuniyet_sekmesi(program):
    if not program:
        st.info("Mezuniyet kontrolü için önce yukarıdan bölümünü seç; staj şartı bölüme göre değişiyor.")
        return
    st.caption("Transkriptinizdeki bilgileri girin. Sonuç yalnızca yönetmelik ve staj yönergesindeki "
               "mezuniyet kurallarına göre hesaplanır, bilgiler hiçbir yere kaydedilmez.")
    with st.form("mezuniyet_formu", border=False):
        sol, sag = st.columns(2)
        akts = sol.number_input("Başarıyla tamamlanan AKTS", 0.0, 400.0, 0.0, 0.5, key="akts")
        gno = sag.number_input("GNO", 0.0, 4.0, 0.0, 0.01, format="%.2f", key="gno")
        staj = sol.number_input("Tamamlanan staj (iş günü)", 0, 120, 0, 1, key="staj")
        st.markdown("**Kalan notlar** (o notla duran ders sayısı)")
        kolonlar = st.columns(len(ENGEL_NOTLAR))
        notlar = {n: k.number_input(n, 0, 30, 0, 1, key=f"not_{n}") for n, k in zip(ENGEL_NOTLAR, kolonlar)}
        hesapla = st.form_submit_button("Kontrol et", type="primary")
    if not hesapla:
        return

    sonuc = kontrol(akts, gno, notlar, staj, program=program)
    parcalar = parca_sozlugu(surum("indeks/parcalar.json"))
    if sonuc["mezun_olabilir"]:
        st.markdown('<div class="durum bulundu">Girdiğiniz bilgilere göre belgelerdeki mezuniyet '
                    'koşullarının hepsi sağlanıyor. Kesin durum için Öğrenci İşleri onayı gerekir.</div>',
                    unsafe_allow_html=True)
    else:
        eksik = sum(not s["tamam"] for s in sonuc["satirlar"])
        st.markdown(f'<div class="durum belirsiz">{eksik} koşul henüz sağlanmıyor.</div>',
                    unsafe_allow_html=True)
    for s in sonuc["satirlar"]:
        p = parcalar[s["kaynak"]]
        etiket = '<span class="etiket tamam">Tamam</span>' if s["tamam"] else '<span class="etiket eksik">Eksik</span>'
        st.markdown(f'<div class="kural">{etiket}<div><div class="ad">{html.escape(s["ad"])}</div>'
                    f'{html.escape(s["aciklama"])}</div>'
                    f'<div class="kaynakca">{html.escape(atif(p))}. {html.escape(gecerlilik(p))}.</div></div>',
                    unsafe_allow_html=True)
    for o in sonuc["oneriler"]:
        p = parcalar[o["kaynak"]]
        st.info(f'{o["metin"]}\n\nKaynak: {atif(p)}')
    ozel = parcalar.get(f"{program}_program_bilgileri#bolum-Mezuniyet_Koşulları")
    standart = parcalar["istatistik_program_bilgileri#bolum-Mezuniyet_Koşulları"]
    if ozel and ozel["metin"] != standart["metin"]:
        # bazı bölümlerin Bologna sayfasında ek koşul var (ör. Kimya: 72 AKTS İngilizce ders)
        st.info(f'Bölümünün Bologna sayfasında ek mezuniyet koşulları var:\n\n'
                f'{ozel["metin"].replace(standart["metin"], "").strip()}\n\nKaynak: {atif(ozel)}')
    st.caption("Bölümün zorunlu/seçmeli ders dağılımı gibi programa özel şartlar burada kontrol edilmez; "
               "bunun için akademik danışmanınızla transkriptinizi birlikte inceleyin.")


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<div class="baslik">ESTÜ <span>Dijital Danışman</span></div>'
                '<div class="altbaslik">ESTÜ lisans öğrencileri için. Yönetmelik, staj ve ders planı '
                'sorularına kısa bir cevap verir; dayandığı resmi maddeyi sayfa numarasıyla altında '
                'gösterir.</div>',
                unsafe_allow_html=True)
    program = bolum_sec()
    kenar_cubugu(program)
    soru_tab, mezuniyet_tab = st.tabs(["Soru sor", "Mezuniyet kontrolü"])
    with soru_tab:
        soru_sekmesi(program)
    with mezuniyet_tab:
        mezuniyet_sekmesi(program)

main()
