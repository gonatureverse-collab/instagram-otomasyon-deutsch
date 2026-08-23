import os
import json
import time
import requests
import subprocess

from pathlib import Path
from dotenv import load_dotenv


# ============================================================
# EINSTELLUNGEN
# ============================================================

load_dotenv()

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_USER_ID = os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]

GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPO = os.environ["GITHUB_REPO"]

API_SURUM = "v21.0"
API_TEMEL = f"https://graph.instagram.com/{API_SURUM}"

CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")

KONTROL_ARALIGI = 5
MAKSIMUM_BEKLEME = 180


# ============================================================
# LETZTE INHALTSDATEI FINDEN
# ============================================================

def son_icerik_dosyasi():

    dosyalar = sorted(
        CIKTI_KLASOR.glob("icerik_*.json")
    )

    if not dosyalar:

        raise FileNotFoundError(
            "Keine icerik_*.json in cikti/ gefunden."
        )

    return dosyalar[-1]


# ============================================================
# BILDORDNER FÜR DIESEN INHALT FINDEN
# ============================================================

def gorsel_klasoru_bul(tarih):

    hedef_klasor = (
        GORSEL_KLASOR / tarih
    )

    if not hedef_klasor.exists():

        raise FileNotFoundError(
            f"Bildordner für Inhalt nicht gefunden: "
            f"{hedef_klasor}"
        )

    if not hedef_klasor.is_dir():

        raise NotADirectoryError(
            f"Bildpfad ist kein Ordner: "
            f"{hedef_klasor}"
        )

    return hedef_klasor


# ============================================================
# ALLE BILDER FÜR CAROUSEL
# ============================================================

def bilder_liste(gorsel_klasoru):

    bilder = sorted(
        gorsel_klasoru.glob("*.png")
    )

    if not bilder:

        raise FileNotFoundError(
            f"Keine PNG-Bilder in {gorsel_klasoru} gefunden."
        )

    return bilder


# ============================================================
# BILDER-URLS VON GITHUB
# ============================================================

def github_roh_url_olustur(bild_adı):

    url = (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"main/gorseller/"
        f"{bild_adı}"
    )

    return url


# ============================================================
# BILDER ZU GITHUB HOCHLADEN
# ============================================================

def bilder_github_ye_gonder():

    print(
        "\nBilder werden zu GitHub hochgeladen..."
    )

    try:

        subprocess.run(
            ["git", "fetch", "origin"],
            check=True
        )

        subprocess.run(
            ["git", "add", "gorseller/"],
            check=True
        )

        commit_result = subprocess.run(

            [
                "git",
                "commit",
                "-m",
                "carousel: Deutsche Bilder hochgeladen"
            ],

            capture_output=True,
            text=True
        )

        if commit_result.returncode != 0:

            output = (
                commit_result.stdout
                + commit_result.stderr
            ).lower()

            if "nothing to commit" in output:

                print(
                    "Keine neuen Bilder zum Commit."
                )

            else:

                print(
                    "Git Commit-Warnung:"
                )

                print(
                    commit_result.stderr
                )

        else:

            print(
                "✓ Bilder committed."
            )

        subprocess.run(
            ["git", "push", "origin", "main"],
            check=True
        )

        print(
            "✓ Bilder zu GitHub hochgeladen."
        )

        # GitHub Verarbeitungszeit
        print(
            "Warte 10 Sekunden auf GitHub-Verarbeitung..."
        )

        time.sleep(10)

    except subprocess.CalledProcessError as error:

        raise RuntimeError(
            f"GitHub Bilder-Upload fehlgeschlagen: {error}"
        )


# ============================================================
# MEDIA CONTAINER OLUŞTUR (CAROUSEL)
# ============================================================

def media_container_olustur(bild_urls, caption, hashtags):

    print(
        "\nInstagram Carousel Container wird erstellt..."
    )

    if not bild_urls:

        raise ValueError(
            "Keine Bild-URLs vorhanden."
        )

    # --------------------------------------------------------
    # Einzelne Items für jedes Bild
    # --------------------------------------------------------

    items = []

    for i, bild_url in enumerate(bild_urls):

        item = {
            "media_type": "IMAGE",
            "image_url": bild_url,
        }

        items.append(item)

    # --------------------------------------------------------
    # Carousel-Container erstellen
    # --------------------------------------------------------

    container_daten = {
        "media_type": "CAROUSEL",
        "children": items,
        "caption": caption,
        "access_token": ACCESS_TOKEN,
    }

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media",

        data=container_daten,

        timeout=60
    )

    if not yanit.ok:

        print(
            "❌ FEHLER - Carousel Container konnte nicht erstellt werden:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = yanit.json()["id"]

    print(
        f"✓ Carousel Container erstellt: {container_id}"
    )

    return container_id


# ============================================================
# CONTAINER STATUS PRÜFEN
# ============================================================

def container_status_prufen(container_id):

    try:

        yanit = requests.get(

            f"{API_TEMEL}/{container_id}",

            params={
                "fields": "status_code,status",
                "access_token": ACCESS_TOKEN,
            },

            timeout=30
        )

        if not yanit.ok:

            print(
                "Container-Statusprüfung fehlgeschlagen:"
            )

            print(
                yanit.text
            )

            return None

        daten = yanit.json()

        status_code = daten.get(
            "status_code"
        )

        status = daten.get(
            "status"
        )

        print(
            f"Container Status: "
            f"{status_code or status}"
        )

        return status_code or status

    except requests.RequestException as hata:

        print(
            f"Fehler bei Statusprüfung: {hata}"
        )

        return None


# ============================================================
# AUF CAROUSEL-VERARBEITUNG WARTEN
# ============================================================

def container_hazir_olmasini_bekle(container_id):

    print(
        "\nInstagram verarbeitet das Carousel..."
    )

    print(
        "Warte 5 Sekunden..."
    )

    time.sleep(5)

    baslangic_zamani = time.time()

    while True:

        gecen_sure = (
            time.time()
            - baslangic_zamani
        )

        if gecen_sure > MAKSIMUM_BEKLEME:

            raise TimeoutError(
                f"Carousel war nicht innerhalb von "
                f"{MAKSIMUM_BEKLEME} Sekunden bereit."
            )

        durum = (
            container_status_prufen(
                container_id
            )
        )

        if durum == "FINISHED":

            print(
                "✓ Instagram Carousel ist bereit."
            )

            return True

        if durum in (
            "IN_PROGRESS",
            "PROCESSING"
        ):

            print(
                f"Carousel wird verarbeitet... "
                f"{int(gecen_sure)} Sekunden vergangen."
            )

            time.sleep(
                KONTROL_ARALIGI
            )

            continue

        if durum == "ERROR":

            raise RuntimeError(
                "Fehler beim Verarbeiten des Carousel."
            )

        print(
            f"Unerwarteter Container-Status: {durum}"
        )

        time.sleep(
            KONTROL_ARALIGI
        )


# ============================================================
# CAROUSEL VERÖFFENTLICHEN
# ============================================================

def carousel_yayinla(container_id):

    print(
        "\nInstagram Carousel wird veröffentlicht..."
    )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media_publish",

        data={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        print(
            "❌ FEHLER - Carousel konnte nicht veröffentlicht werden:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    post_id = yanit.json().get("id")

    print(
        "\n========================================"
    )

    print(
        "✓ DEUTSCHES CAROUSEL ERFOLGREICH VERÖFFENTLICHT!"
    )

    print(
        f"Post-ID: {post_id}"
    )

    print(
        "========================================"
    )

    return post_id


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():

    print(
        "========================================"
    )

    print(
        "DEUTSCHES INSTAGRAM CAROUSEL"
    )

    print(
        "========================================"
    )

    # --------------------------------------------------------
    # 1. Inhaltsdatei suchen
    # --------------------------------------------------------

    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    print(
        f"\nInhalt: {icerik_dosyasi.name}"
    )

    # --------------------------------------------------------
    # 2. Inhalt lesen
    # --------------------------------------------------------

    icerik = json.loads(
        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------------
    # 3. Bildordner
    # --------------------------------------------------------

    tarih = icerik.get("tarih")

    if not tarih:

        raise ValueError(
            "'tarih' nicht im JSON gefunden."
        )

    gorsel_klasoru = (
        gorsel_klasoru_bul(
            tarih
        )
    )

    print(
        f"Bilder: {gorsel_klasoru}"
    )

    # --------------------------------------------------------
    # 4. Bildliste
    # --------------------------------------------------------

    bilder = bilder_liste(
        gorsel_klasoru
    )

    print(
        f"{len(bilder)} PNG-Bilder gefunden."
    )

    for i, bild in enumerate(bilder):

        print(
            f"  {i+1}. {bild.name}"
        )

    # --------------------------------------------------------
    # 5. BILDER ZU GITHUB HOCHLADEN (NEU!)
    # --------------------------------------------------------

    bilder_github_ye_gonder()

    # --------------------------------------------------------
    # 6. GitHub URLs
    # --------------------------------------------------------

    bild_urls = []

    for i, bild in enumerate(bilder):

        url = (
            f"https://raw.githubusercontent.com/"
            f"{GITHUB_USERNAME}/"
            f"{GITHUB_REPO}/"
            f"main/gorseller/"
            f"{tarih}/"
            f"{bild.name}"
        )

        bild_urls.append(url)

    # --------------------------------------------------------
    # 7. Caption & Hashtags
    # --------------------------------------------------------

    caption = icerik.get(
        "caption",
        "Deutsches Carousel 🇩🇪"
    )

    hashtagler = icerik.get(
        "hashtagler",
        []
    )

    if hashtagler:

        caption += (
            "\n\n"
            + " ".join(hashtagler)
        )

    print(
        f"\nCaption: {caption[:100]}..."
    )

    # --------------------------------------------------------
    # 8. Carousel Container erstellen
    # --------------------------------------------------------

    container_id = (
        media_container_olustur(
            bild_urls,
            caption,
            hashtagler
        )
    )

    # --------------------------------------------------------
    # 9. Auf Verarbeitung warten
    # --------------------------------------------------------

    container_hazir_olmasini_bekle(
        container_id
    )

    # --------------------------------------------------------
    # 10. Veröffentlichen
    # --------------------------------------------------------

    post_id = carousel_yayinla(
        container_id
    )

    print(
        "\n✓ Deutsches Carousel erfolgreich veröffentlicht!"
    )


# ============================================================
# PROGRAMM AUSFÜHREN
# ============================================================

if __name__ == "__main__":
    main()
