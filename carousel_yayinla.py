import os
import json
import time
import requests

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

# ============================================================
# WICHTIG:
# Facebook Login / Page Access Token kullanıldığı için
# graph.facebook.com kullanıyoruz.
# ============================================================

API_VERSION = "v21.0"
API_BASE = f"https://graph.facebook.com/{API_VERSION}"

CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")

KONTROL_ARALIGI = 5
MAKSIMUM_BEKLEME = 180


# ============================================================
# API HATA YARDIMCISI
# ============================================================

def api_hatasi_yazdir(yanit, islem):

    print()
    print("=" * 60)
    print(f"❌ API HATASI: {islem}")
    print("=" * 60)

    print(f"HTTP Status: {yanit.status_code}")

    try:
        hata = yanit.json()

        print(
            json.dumps(
                hata,
                ensure_ascii=False,
                indent=2
            )
        )

    except Exception:

        print(yanit.text)

    print("=" * 60)


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
# GITHUB RAW URL
# ============================================================

def github_raw_url(dosya_yolu):

    relative_path = dosya_yolu.as_posix()

    return (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"main/"
        f"{relative_path}"
    )


# ============================================================
# TOKEN KONTROLÜ
# ============================================================

def token_kontrol():

    print()
    print("Instagram API bağlantısı kontrol ediliyor...")

    yanit = requests.get(

        f"{API_BASE}/{IG_USER_ID}",

        params={
            "fields": "id,username",
            "access_token": ACCESS_TOKEN,
        },

        timeout=30
    )

    if not yanit.ok:

        api_hatasi_yazdir(
            yanit,
            "Instagram Business Account kontrolü"
        )

        yanit.raise_for_status()

    veri = yanit.json()

    print()
    print("✓ Instagram hesabı API tarafından bulundu.")
    print(f"Instagram ID: {veri.get('id')}")
    print(f"Instagram Username: @{veri.get('username')}")

    return veri


# ============================================================
# CONTAINER STATUS
# ============================================================

def container_durumu(container_id):

    yanit = requests.get(

        f"{API_BASE}/{container_id}",

        params={
            "fields": "status_code,status",
            "access_token": ACCESS_TOKEN,
        },

        timeout=30
    )

    if not yanit.ok:

        api_hatasi_yazdir(
            yanit,
            "Container Status"
        )

        yanit.raise_for_status()

    veri = yanit.json()

    return veri


# ============================================================
# AUF CONTAINER-VERARBEITUNG WARTEN
# ============================================================

def container_bekle(container_id):

    print()
    print(
        f"Container wird verarbeitet: {container_id}"
    )

    baslangic = time.time()

    while True:

        durum = container_durumu(
            container_id
        )

        status_code = durum.get(
            "status_code"
        )

        status = durum.get(
            "status"
        )

        print(
            f"Status: {status_code or status}"
        )

        # ====================================================
        # FERTIG
        # ====================================================

        if status_code == "FINISHED":

            print(
                "✓ Container ist bereit."
            )

            return True

        # ====================================================
        # FEHLER
        # ====================================================

        if status_code in [
            "ERROR",
            "EXPIRED"
        ]:

            raise RuntimeError(
                f"Instagram Container-Fehler: {durum}"
            )

        # ====================================================
        # TIMEOUT
        # ====================================================

        gecen_sure = (
            time.time()
            - baslangic
        )

        if gecen_sure > MAKSIMUM_BEKLEME:

            raise TimeoutError(
                f"Container war nicht innerhalb von "
                f"{MAKSIMUM_BEKLEME} Sekunden bereit: "
                f"{container_id}"
            )

        time.sleep(
            KONTROL_ARALIGI
        )


# ============================================================
# CHILD CONTAINER
# ============================================================

def child_container_olustur(gorsel_url):

    print()
    print(
        "Child-Container wird erstellt:"
    )

    print(
        gorsel_url
    )

    yanit = requests.post(

        f"{API_BASE}/{IG_USER_ID}/media",

        data={
            "image_url": gorsel_url,
            "is_carousel_item": "true",
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        api_hatasi_yazdir(
            yanit,
            "Child-Container erstellen"
        )

        yanit.raise_for_status()

    veri = yanit.json()

    container_id = veri.get(
        "id"
    )

    if not container_id:

        raise RuntimeError(
            f"Instagram hat keine Container-ID zurückgegeben: "
            f"{veri}"
        )

    print(
        f"✓ Child-Container: {container_id}"
    )

    return container_id


# ============================================================
# CAROUSEL CONTAINER
# ============================================================

def carousel_container_olustur(
    child_ids,
    caption
):

    print()
    print(
        "Carousel-Container wird erstellt..."
    )

    yanit = requests.post(

        f"{API_BASE}/{IG_USER_ID}/media",

        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        api_hatasi_yazdir(
            yanit,
            "Carousel-Container erstellen"
        )

        yanit.raise_for_status()

    veri = yanit.json()

    container_id = veri.get(
        "id"
    )

    if not container_id:

        raise RuntimeError(
            f"Instagram hat keine Carousel-ID zurückgegeben: "
            f"{veri}"
        )

    print(
        f"✓ Carousel-Container: {container_id}"
    )

    return container_id


# ============================================================
# CAROUSEL VERÖFFENTLICHEN
# ============================================================

def carousel_yayinla():

    print()
    print("=" * 60)
    print("DEUTSCHES INSTAGRAM CAROUSEL")
    print("=" * 60)

    # --------------------------------------------------------
    # 0. API / TOKEN TEST
    # --------------------------------------------------------

    token_kontrol()

    # --------------------------------------------------------
    # 1. Inhaltsdatei
    # --------------------------------------------------------

    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    print()
    print(
        f"Inhalt: {icerik_dosyasi}"
    )

    icerik = json.loads(

        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------------
    # 2. Datum
    # --------------------------------------------------------

    tarih = icerik.get(
        "tarih"
    )

    if not tarih:

        raise ValueError(
            "Feld 'tarih' im JSON nicht gefunden."
        )

    # --------------------------------------------------------
    # 3. Bildordner
    # --------------------------------------------------------

    gorsel_klasoru = (
        gorsel_klasoru_bul(
            tarih
        )
    )

    print(
        f"Bilder: {gorsel_klasoru}"
    )

    # --------------------------------------------------------
    # 4. PNG-Dateien
    # --------------------------------------------------------

    png_dosyalari = sorted(
        gorsel_klasoru.glob("*.png")
    )

    if not png_dosyalari:

        raise FileNotFoundError(
            f"Keine PNG-Dateien in "
            f"{gorsel_klasoru} gefunden."
        )

    print()
    print(
        f"{len(png_dosyalari)} Bilder gefunden."
    )

    # Instagram Carousel maksimum 10 öğe
    if len(png_dosyalari) > 10:

        raise ValueError(
            f"Instagram Carousel unterstützt maximal "
            f"10 Elemente. Gefunden: {len(png_dosyalari)}"
        )

    # --------------------------------------------------------
    # 5. CHILD CONTAINERS
    # --------------------------------------------------------

    child_ids = []

    for sira, png_dosyasi in enumerate(
        png_dosyalari,
        start=1
    ):

        print()
        print(
            f"[{sira}/{len(png_dosyalari)}"
            f"]"
        )

        # ----------------------------------------------------
        # Lokaler Pfad
        # ----------------------------------------------------

        gorsel_yolu = (
            png_dosyasi.as_posix()
        )

        # ----------------------------------------------------
        # GitHub Raw URL
        # ----------------------------------------------------

        gorsel_url = github_raw_url(
            Path(gorsel_yolu)
        )

        print(
            f"URL: {gorsel_url}"
        )

        # ----------------------------------------------------
        # Child Container erstellen
        # ----------------------------------------------------

        child_id = (
            child_container_olustur(
                gorsel_url
            )
        )

        # ----------------------------------------------------
        # Verarbeitung abwarten
        # ----------------------------------------------------

        container_bekle(
            child_id
        )

        child_ids.append(
            child_id
        )

    # --------------------------------------------------------
    # 6. Caption & Hashtags
    # --------------------------------------------------------

    caption = icerik.get(
        "caption",
        ""
    )

    hashtagler = icerik.get(
        "hashtagler",
        []
    )

    if hashtagler:

        caption = (
            caption
            + "\n\n"
            + " ".join(hashtagler)
        )

    # --------------------------------------------------------
    # 7. CAROUSEL CONTAINER
    # --------------------------------------------------------

    carousel_id = (
        carousel_container_olustur(
            child_ids,
            caption
        )
    )

    # --------------------------------------------------------
    # 8. CAROUSEL VERARBEITUNG ABWARTEN
    # --------------------------------------------------------

    container_bekle(
        carousel_id
    )

    # --------------------------------------------------------
    # 9. VERÖFFENTLICHEN
    # --------------------------------------------------------

    print()
    print(
        "Carousel wird auf Instagram veröffentlicht..."
    )

    yanit = requests.post(

        f"{API_BASE}/{IG_USER_ID}/media_publish",

        data={
            "creation_id": carousel_id,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        api_hatasi_yazdir(
            yanit,
            "Carousel veröffentlichen"
        )

        yanit.raise_for_status()

    # --------------------------------------------------------
    # 10. ERFOLG
    # --------------------------------------------------------

    veri = yanit.json()

    post_id = veri.get(
        "id"
    )

    print()
    print("=" * 60)
    print(
        "✓ DEUTSCHES CAROUSEL ERFOLGREICH VERÖFFENTLICHT!"
    )
    print("=" * 60)

    print()
    print(
        f"Instagram Post ID: {post_id}"
    )

    print()


# ============================================================
# HAUPTPROGRAMM
# ============================================================

if __name__ == "__main__":

    try:

        carousel_yayinla()

    except Exception as hata:

        print()
        print("=" * 60)
        print("❌ CAROUSEL-FEHLER")
        print("=" * 60)

        print()
        print(
            hata
        )

        raise
