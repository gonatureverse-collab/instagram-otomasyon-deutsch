import json
from pathlib import Path
from playwright.sync_api import sync_playwright


# ============================================================
# KLASSEUR
# ============================================================

CIKTI_KLASOR = Path("cikti")
STORY_KLASOR = Path("stories")

# Instagram Story Größe
GENISLIK = 1080
YUKSEKLIK = 1920


# ============================================================
# STORY HTML DESIGN
# ============================================================

STORY_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>

@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&display=swap');

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    width: {genislik}px;
    height: {yukseklik}px;

    font-family: 'Montserrat', sans-serif;

    background:
        radial-gradient(
            circle at 50% 20%,
            #292929 0%,
            #111111 45%,
            #050505 100%
        );

    color: white;

    position: relative;

    overflow: hidden;
}}


/* ========================================================
   DEUTSCHES FLAGGENBAND OBEN
   ======================================================== */

.ust-serit {{
    position: absolute;

    top: 0;
    left: 0;

    width: 100%;
    height: 30px;

    display: flex;
}}

.ust-serit .siyah {{
    flex: 1;
    background: #111111;
}}

.ust-serit .kirmizi {{
    flex: 1;
    background: #DD0000;
}}

.ust-serit .sari {{
    flex: 1;
    background: #FFCE00;
}}


/* ========================================================
   DEUTSCHES FLAGGENBAND UNTEN
   ======================================================== */

.alt-serit {{
    position: absolute;

    bottom: 0;
    left: 0;

    width: 100%;
    height: 30px;

    display: flex;
}}

.alt-serit .siyah {{
    flex: 1;
    background: #111111;
}}

.alt-serit .kirmizi {{
    flex: 1;
    background: #DD0000;
}}

.alt-serit .sari {{
    flex: 1;
    background: #FFCE00;
}}


/* ========================================================
   OBERE ÜBERSCHRIFT
   ======================================================== */

.logo {{
    position: absolute;

    top: 100px;
    left: 70px;
    right: 70px;

    text-align: center;

    color: #FFCE00;

    font-size: 32px;

    font-weight: 800;

    letter-spacing: 3px;
}}


/* ========================================================
   STORY ICON
   ======================================================== */

.ikon {{
    position: absolute;

    top: 250px;

    left: 0;
    right: 0;

    text-align: center;

    font-size: 150px;
}}


/* ========================================================
   TITEL
   ======================================================== */

.baslik {{
    position: absolute;

    top: 480px;

    left: 70px;
    right: 70px;

    text-align: center;

    color: white;

    font-size: 58px;

    line-height: 1.2;

    font-weight: 900;
}}


/* ========================================================
   FRAGE BOX
   ======================================================== */

.soru-kutusu {{
    position: absolute;

    top: 760px;

    left: 70px;
    right: 70px;

    padding: 60px 45px;

    background: white;

    border-radius: 35px;

    box-shadow:
        0 15px 50px rgba(0,0,0,0.45);

    text-align: center;
}}

.soru {{
    color: #111111;

    font-size: 46px;

    line-height: 1.3;

    font-weight: 800;
}}


/* ========================================================
   ABSTIMMUNG
   ======================================================== */

.anket {{
    position: absolute;

    top: 1190px;

    left: 70px;
    right: 70px;

    display: flex;

    gap: 30px;
}}

.secenek {{
    flex: 1;

    min-height: 220px;

    background: #ffffff;

    border-radius: 35px;

    display: flex;

    align-items: center;

    justify-content: center;

    text-align: center;

    padding: 35px;

    color: #111111;

    font-size: 34px;

    font-weight: 800;

    box-shadow:
        0 15px 40px rgba(0,0,0,0.35);
}}

.secenek:first-child {{
    border-top: 15px solid #DD0000;
}}

.secenek:last-child {{
    border-top: 15px solid #FFCE00;
}}


/* ========================================================
   CTA
   ======================================================== */

.cta {{
    position: absolute;

    bottom: 140px;

    left: 70px;
    right: 70px;

    text-align: center;

    color: #ffffff;

    font-size: 30px;

    font-weight: 600;

    line-height: 1.4;
}}

.cta span {{
    color: #FFCE00;

    font-weight: 900;
}}

</style>

</head>


<body>


<!-- OBERES BAND -->

<div class="ust-serit">

    <div class="siyah"></div>

    <div class="kirmizi"></div>

    <div class="sari"></div>

</div>


<!-- UNTERES BAND -->

<div class="alt-serit">

    <div class="siyah"></div>

    <div class="kirmizi"></div>

    <div class="sari"></div>

</div>


<!-- KONTONAME -->

<div class="logo">

    WIE MACHT MAN DAS IN DEUTSCHLAND?

</div>


<!-- ICON -->

<div class="ikon">

    📊

</div>


<!-- STORY TITEL -->

<div class="baslik">

    {baslik}

</div>


<!-- FRAGE -->

<div class="soru-kutusu">

    <div class="soru">

        {metin}

    </div>

</div>


<!-- ABSTIMMUNG -->

<div class="anket">

    <div class="secenek">

        {secenek1}

    </div>

    <div class="secenek">

        {secenek2}

    </div>

</div>


<!-- CTA -->

<div class="cta">

    <span>Nutze die Abstimmung 👆</span><br>

    Was ist deine Antwort?

</div>


</body>

</html>
"""


# ============================================================
# LETZTEN INHALT FINDE
# ============================================================

def son_icerik_dosyasi():

    dosyalar = sorted(
        CIKTI_KLASOR.glob("icerik_*.json")
    )

    if not dosyalar:

        raise FileNotFoundError(
            "Keine Inhaltsdatei in cikti/ gefunden. "
            "Führe zuerst icerik_uret.py aus."
        )

    return dosyalar[-1]


# ============================================================
# STORY ERSTELLEN
# ============================================================

def story_uret(icerik_dosyasi: Path):

    # --------------------------------------------------------
    # JSON lesen
    # --------------------------------------------------------

    icerik = json.loads(
        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------------
    # Story-Prüfung
    # --------------------------------------------------------

    if "story" not in icerik:

        raise ValueError(
            "'story' Bereich im JSON nicht gefunden."
        )

    story = icerik["story"]

    # --------------------------------------------------------
    # Datum
    # --------------------------------------------------------

    tarih = icerik.get(
        "tarih",
        "story"
    )

    # --------------------------------------------------------
    # Story-Klasseur
    # --------------------------------------------------------

    hedef_klasor = (
        STORY_KLASOR
        / tarih
    )

    hedef_klasor.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Story-Informationen
    # --------------------------------------------------------

    baslik = story.get(
        "baslik",
        "Was denkst du?"
    )

    metin = story.get(
        "metin",
        "Was denkst du zu diesem Thema?"
    )

    anket = story.get(
        "anket",
        []
    )

    # --------------------------------------------------------
    # Abstimmungsprüfung
    # --------------------------------------------------------

    if len(anket) < 2:

        anket = [
            "Ja 👍",
            "Nein 👎"
        ]

    secenek1 = anket[0]
    secenek2 = anket[1]

    # --------------------------------------------------------
    # HTML erstellen
    # --------------------------------------------------------

    html = STORY_HTML.format(

        genislik=GENISLIK,

        yukseklik=YUKSEKLIK,

        baslik=baslik,

        metin=metin,

        secenek1=secenek1,

        secenek2=secenek2
    )

    # --------------------------------------------------------
    # Playwright
    # --------------------------------------------------------

    print(
        "\nInstagram Story wird erstellt..."
    )

    with sync_playwright() as p:

        tarayici = p.chromium.launch()

        sayfa = tarayici.new_page(

            viewport={
                "width": GENISLIK,
                "height": YUKSEKLIK
            },

            device_scale_factor=1
        )

        # HTML laden
        sayfa.set_content(
            html,
            wait_until="networkidle"
        )

        # Auf Schriftarten warten
        sayfa.wait_for_timeout(
            1000
        )

        # ----------------------------------------------------
        # PNG
        # ----------------------------------------------------

        story_yolu = (
            hedef_klasor
            / "story.png"
        )

        sayfa.screenshot(

            path=str(story_yolu),

            full_page=True
        )

        tarayici.close()

    # --------------------------------------------------------
    # Ergebnis
    # --------------------------------------------------------

    print(
        f"✓ Story erstellt: {story_yolu}"
    )

    return story_yolu


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():

    print(
        "========================================"
    )

    print(
        "INSTAGRAM STORY-GENERATOR"
    )

    print(
        "========================================"
    )

    # Letzten JSON
    icerik_dosyasi = son_icerik_dosyasi()

    print(
        f"\nVerwendeter Inhalt:"
        f"\n{icerik_dosyasi}"
    )

    # Story erstellen
    story_yolu = story_uret(
        icerik_dosyasi
    )

    print(
        "\n========================================"
    )

    print(
        "✓ STORY ERFOLGREICH ERSTELLT"
    )

    print(
        "========================================"
    )

    print(
        f"\nDatei:"
        f"\n{story_yolu}"
    )


# ============================================================
# AUSFÜHREN
# ============================================================

if __name__ == "__main__":

    main()