import os
import json
import random
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic


# ============================================================
# AYARLAR
# ============================================================

load_dotenv()

client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"]
)

KONULAR_DOSYA = Path("konular.json")
KULLANILAN_DOSYA = Path("kullanilan_konular.json")
CIKTI_KLASOR = Path("cikti")


# ============================================================
# KONU SEÇ
# ============================================================

def konu_sec():

    konular = json.loads(
        KONULAR_DOSYA.read_text(
            encoding="utf-8"
        )
    )

    if KULLANILAN_DOSYA.exists():

        kullanilan = json.loads(
            KULLANILAN_DOSYA.read_text(
                encoding="utf-8"
            )
        )

    else:

        kullanilan = []

    kalan = [
        konu for konu in konular
        if konu not in kullanilan
    ]

    if not kalan:

        print(
            "Tüm konular kullanıldı. "
            "Konu listesi yeniden başlatılıyor."
        )

        kalan = konular
        kullanilan = []

    secilen = random.choice(kalan)

    kullanilan.append(secilen)

    KULLANILAN_DOSYA.write_text(
        json.dumps(
            kullanilan,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return secilen


# ============================================================
# AI İÇERİK ÜRET
# ============================================================

def icerik_uret(konu):

    prompt = f"""
Du bist ein professioneller Content-Assistent für
den Instagram-Account "wiemachtmandasindeutschland"
(Wie macht man das in Deutschland).

THEMA:
"{konu}"

Erstelle gleichzeitig:

1. Instagram Carousel
2. Instagram Reel
3. Instagram Story
4. Instagram Caption
5. Hashtags

Ziel:
Erstelle hilfreiche, praktische und zuverlässige Inhalte
für Menschen, die in Deutschland leben oder neu nach Deutschland
gekommen sind.

Der gesamte Inhalt muss auf Deutsch sein und einfach
verständlich sein.

============================================================
SEHR WICHTIG: KORREKTHEIT
============================================================

- Schreibe keine Informationen als Tatsachen, wenn du dir
  nicht sicher bist.
- Erfinde keine Zahlen.
- Erfinde keine Geldbeträge.
- Erfinde keine Gebühren.
- Erfinde keine Fristen.
- Erfinde keine rechtlichen Bedingungen.
- Bei veränderlichen Informationen deutlich darauf hinweisen.
- Keine erfundenen URLs.
- Keine erfundenen Behördennamen.
- Keine Aussagen wie "garantiert" oder "jeder kann".
- Bei offiziellen Themen immer empfehlen, die aktuellen
  Informationen bei der zuständigen Behörde zu prüfen.

============================================================
CAROUSEL
============================================================

Erstelle genau:

1 Titelfolie + 5 Inhaltsfolien.

Regeln:

- Titel kurz und auffällig.
- Jede Inhaltsfolie maximal 2 kurze Sätze.
- Einfaches Deutsch.
- Praktische Informationen.
- Genau 1 Emoji pro Inhaltsfolie.

============================================================
REEL
============================================================

Erstelle ein 15-20 Sekunden Reel.

- Genau 6 kurze Szenen.
- Szene 1 muss Aufmerksamkeit erzeugen.
- Nicht wortwörtlich das Carousel wiederholen.
- Schneller und natürlicher Stil.
- Am Ende kurzer CTA.

============================================================
STORY
============================================================

Erstelle genau eine kurze interaktive Story.

Die Story MUSS IMMER enthalten:

- "baslik"
- "metin"
- "anket"

"anket" MUSS immer ein Array mit GENAU 2 kurzen
Antwortmöglichkeiten sein.

Beispiel:

"anket": [
  "Ja, wusste ich",
  "Nein, wusste ich nicht"
]

Wenn das Thema keine konkrete Abstimmung erlaubt,
verwende trotzdem eine einfache Wissensfrage zum Thema.

============================================================
CAPTION
============================================================

- 2-4 kurze Sätze.
- Freundlich.
- Informativ.
- Kurzer Call-to-Action.
- Nutzer zum Speichern, Teilen oder Kommentieren motivieren.

============================================================
HASHTAGS
============================================================

Maximal 10 relevante Hashtags.

============================================================
JSON
============================================================

Antworte AUSSCHLIESSLICH mit gültigem JSON.

Keine Erklärungen.
Keine Markdown-Codeblöcke.
Kein Text außerhalb des JSON.

Das JSON MUSS exakt diese Struktur haben:

{{
  "baslik": "Carousel-Titelfolientitel",

  "kapak_emoji": "🇩🇪",

  "slaytlar": [
    "Folie 1 Text",
    "Folie 2 Text",
    "Folie 3 Text",
    "Folie 4 Text",
    "Folie 5 Text"
  ],

  "emojiler": [
    "📄",
    "🏠",
    "📅",
    "💶",
    "✅"
  ],

  "reel": {{
    "baslik": "Reel-Titel",
    "sahneler": [
      "Szene 1",
      "Szene 2",
      "Szene 3",
      "Szene 4",
      "Szene 5",
      "Szene 6"
    ],
    "cta": "Reel Call-to-Action Text"
  }},

  "story": {{
    "baslik": "Story-Titel",
    "metin": "Kurze Frage zum Thema",
    "anket": [
      "Ja",
      "Nein"
    ]
  }},

  "caption": "Instagram Caption Text",

  "hashtagler": [
    "#deutschland",
    "#wiemachtman",
    "#deutschlandtipp"
  ]
}}
"""

    print(
        "Claude erstellt Carousel + Reel + Story Inhalte..."
    )

    yanit = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2500,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    metin = yanit.content[0].text.strip()

    # ========================================================
    # MARKDOWN JSON TEMİZLE
    # ========================================================

    if metin.startswith("```"):

        parcalar = metin.split("```")

        if len(parcalar) >= 2:

            metin = parcalar[1]

            if metin.startswith("json"):
                metin = metin[4:]

    metin = metin.strip()

    # ========================================================
    # JSON OKU
    # ========================================================

    try:

        icerik = json.loads(metin)

    except json.JSONDecodeError as hata:

        print(
            "AI hat keinen gültigen JSON erzeugt."
        )

        print()
        print("AI-ANTWORT:")
        print(metin)

        raise hata

    # ========================================================
    # TEMEL ALAN KONTROLÜ
    # ========================================================

    gerekli_alanlar = [
        "baslik",
        "kapak_emoji",
        "slaytlar",
        "emojiler",
        "reel",
        "story",
        "caption",
        "hashtagler"
    ]

    for alan in gerekli_alanlar:

        if alan not in icerik:

            raise ValueError(
                f"'{alan}' Feld in der AI-Ausgabe nicht gefunden."
            )

    # ========================================================
    # CAROUSEL KONTROLÜ
    # ========================================================

    if not isinstance(
        icerik["slaytlar"],
        list
    ):

        raise ValueError(
            "'slaytlar' muss eine Liste sein."
        )

    if len(icerik["slaytlar"]) < 5:

        raise ValueError(
            "Carousel benötigt mindestens 5 Inhaltsfolien."
        )

    if not isinstance(
        icerik["emojiler"],
        list
    ):

        raise ValueError(
            "'emojiler' muss eine Liste sein."
        )

    if len(icerik["emojiler"]) < 5:

        raise ValueError(
            "Carousel benötigt mindestens 5 Emojis."
        )

    # ========================================================
    # REEL KONTROLÜ
    # ========================================================

    if not isinstance(
        icerik["reel"],
        dict
    ):

        raise ValueError(
            "'reel' muss ein Objekt sein."
        )

    if "sahneler" not in icerik["reel"]:

        raise ValueError(
            "'sahneler' nicht im Reel-Inhalt gefunden."
        )

    if not isinstance(
        icerik["reel"]["sahneler"],
        list
    ):

        raise ValueError(
            "'sahneler' muss eine Liste sein."
        )

    if len(icerik["reel"]["sahneler"]) < 5:

        raise ValueError(
            "Reel benötigt mindestens 5 Szenen."
        )

    # ========================================================
    # STORY KONTROLÜ
    # ========================================================

    if not isinstance(
        icerik["story"],
        dict
    ):

        print(
            "⚠️ Story-Objekt fehlt oder ist ungültig."
        )

        icerik["story"] = {
            "baslik": "Was denkst du?",
            "metin": f"Kennst du dich mit diesem Thema aus: {konu}?",
            "anket": [
                "Ja",
                "Nein"
            ]
        }

    story = icerik["story"]

    # --------------------------------------------------------
    # Story Titel
    # --------------------------------------------------------

    if not story.get("baslik"):

        story["baslik"] = (
            "Wusstest du das?"
        )

    # --------------------------------------------------------
    # Story Text
    # --------------------------------------------------------

    if not story.get("metin"):

        story["metin"] = (
            f"Kennst du dich mit diesem Thema aus: {konu}?"
        )

    # --------------------------------------------------------
    # ANKET
    # --------------------------------------------------------

    if (
        "anket" not in story
        or not isinstance(story["anket"], list)
        or len(story["anket"]) < 2
    ):

        print()
        print(
            "⚠️ Claude hat keine gültige Story-Umfrage "
            "erstellt."
        )

        print(
            "→ Standard-Umfrage wird automatisch erstellt."
        )

        story["anket"] = [
            "Ja, wusste ich",
            "Nein, wusste ich nicht"
        ]

    else:

        # Nur die ersten zwei Optionen verwenden
        story["anket"] = story["anket"][:2]

    # ========================================================
    # CAPTION KONTROLLE
    # ========================================================

    if not isinstance(
        icerik["caption"],
        str
    ):

        icerik["caption"] = (
            f"Interessantes zum Thema {konu}. "
            "Speichere den Beitrag für später!"
        )

    # ========================================================
    # HASHTAGS KONTROLLE
    # ========================================================

    if not isinstance(
        icerik["hashtagler"],
        list
    ):

        icerik["hashtagler"] = [
            "#deutschland",
            "#lebenindeutschland",
            "#deutschlandtipps"
        ]

    # Maximal 10 Hashtags
    icerik["hashtagler"] = (
        icerik["hashtagler"][:10]
    )

    # ========================================================
    # STORY SONDERKONTROLLE
    # ========================================================

    if len(story["anket"]) != 2:

        story["anket"] = [
            "Ja",
            "Nein"
        ]

    return icerik


# ============================================================
# ANA PROGRAM
# ============================================================

def main():

    CIKTI_KLASOR.mkdir(
        exist_ok=True
    )

    print()
    print("=" * 60)
    print("WIE MACHT MAN DAS IN DEUTSCHLAND?")
    print("TÄGLICHE INHALTSERSTELLUNG")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Konu seç
    # --------------------------------------------------------

    konu = konu_sec()

    print(
        f"Gewähltes Thema: {konu}"
    )

    # --------------------------------------------------------
    # İçerik üret
    # --------------------------------------------------------

    icerik = icerik_uret(
        konu
    )

    # --------------------------------------------------------
    # Meta bilgiler
    # --------------------------------------------------------

    icerik["konu"] = konu

    icerik["tarih"] = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    # --------------------------------------------------------
    # JSON kaydet
    # --------------------------------------------------------

    dosya_adi = (
        CIKTI_KLASOR
        / f"icerik_{icerik['tarih']}.json"
    )

    dosya_adi.write_text(
        json.dumps(
            icerik,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # Sonuç
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("✓ INHALTE ERFOLGREICH ERSTELLT")
    print("=" * 60)
    print()

    print(
        f"JSON: {dosya_adi}"
    )

    print()
    print("Erstellte Inhalte:")
    print("✓ 1 Carousel")
    print("✓ 1 Reel")
    print("✓ 1 Story")

    print()
    print(
        json.dumps(
            icerik,
            ensure_ascii=False,
            indent=2
        )
    )


# ============================================================
# ÇALIŞTIR
# ============================================================

if __name__ == "__main__":

    main()
