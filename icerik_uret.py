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
gekommen sind. Der Inhalt soll auf Deutsch sein und einfach
verständlich sein.

============================================================
SEHR WICHTIG: KORREKTHEIT DER INFORMATIONEN
============================================================

- Schreibe keine Informationen als Tatsachen, wenn du dir nicht sicher bist.
- Erfinde keine Zahlen.
- Erfinde keine Geldbeträge.
- Erfinde keine Gebühren oder Antragskosten.
- Erfinde keine Daten oder Antragsfristen.
- Erfinde keine rechtlichen Bedingungen.
- Gebe keine sicheren Aussagen zu Gerichten, Aufenthalten,
  Staatsbürgerschaft, Steuern, Sozialleistungen, Stipendien
  oder offiziellen Anträgen, wenn du dir nicht sicher bist.
- Wenn eine Information sich ändern kann, mache das deutlich.
- Du kannst eine Warnung hinzufügen wie:
  "Aktuelle Informationen immer bei den zuständigen
  behörden überprüfen."
- Verwechsle verschiedene behörden oder Antragsysteme nicht.
- Erfinde keine URLs oder Namen von behördenwebseiten oder
  Antragsystemen, wenn du dir nicht sicher bist.
- Verwende keine Ausdrücke wie "definitiv", "garantiert",
  "jeder kann" oder ähnliches.
- Der Inhalt soll hilfreich sein, aber vorsichtig.

============================================================
CAROUSEL
============================================================

Erstelle 1 Titelfolie + 5 Inhaltsfolien.

Regeln:

- Der Titel auf der Titelfolie soll kurz und auffällig sein.
- Jede Inhaltsfolie sollte maximal 2 kurze Sätze haben.
- Verwende einfaches Deutsch.
- Gebe praktische Informationen.
- Wähle genau 1 Emoji pro Folie.

============================================================
REEL
============================================================

Erstelle Inhalte für ein 15-20 Sekunden Reel.

- 5-6 kurze Szenen.
- Die erste Szene sollte eine starke, aufmerksamkeitserregende Einleitung sein.
- Wiederhole das Carousel nicht wort-für-wort.
- Das Reel sollte schneller und umgangssprachlicher sein.
- Endet mit einem kurzen Call-to-Action.
- Jede Szene sollte kurz sein.

============================================================
STORY
============================================================

Erstelle eine Story.

- Kurz und interaktiv.
- Enthalte eine Frage.
- 2 Abstimmungsoptionen.

============================================================
CAPTION
============================================================

- 2-4 kurze Sätze.
- Freundlich und informativ.
- Endet mit einem kurzen Call-to-Action.
- Ermutige die Nutzer, zu speichern, zu teilen oder zu kommentieren.

============================================================
HASHTAGS
============================================================

Erstelle maximal 10 relevante Hashtags.

============================================================
JSON
============================================================

Antworte NUR im folgenden JSON-Format.

Schreibe keine Erklärungen außerhalb des JSON.

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
    "metin": "Story-Frage Text",
    "anket": [
      "Option 1",
      "Option 2"
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

        print("AI hat keinen JSON erzeugt oder JSON ist fehlerhaft.")

        print()
        print("AI-ANTWORT:")
        print(metin)

        raise hata

    # ========================================================
    # ALAN KONTROLÜ
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

    # Reel kontrol
    if "sahneler" not in icerik["reel"]:
        raise ValueError(
            "'sahneler' nicht im Reel-Inhalt gefunden."
        )

    # Story kontrol
    if "anket" not in icerik["story"]:
        raise ValueError(
            "'anket' nicht im Story-Inhalt gefunden."
        )

    if len(icerik["story"]["anket"]) < 2:
        raise ValueError(
            "Story-Abstimmung erfordert mindestens 2 Optionen."
        )

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