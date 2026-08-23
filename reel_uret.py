import os
import json
import requests
import subprocess
import time

from pathlib import Path
from dotenv import load_dotenv


# ============================================================
# AYARLAR
# ============================================================

load_dotenv()

# Instagram
ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_USER_ID = os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]

# GitHub
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPO = os.environ["GITHUB_REPO"]

# ElevenLabs
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]

# Almanca ses (Daniel)
ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

# Model
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

# MP3 formatı
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"

# Instagram API
API_SURUM = "v21.0"
API_TEMEL = f"https://graph.instagram.com/{API_SURUM}"

# Klasörler
CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")
REEL_KLASOR = Path("reels")

# Video ayarları
SLAYT_SURESI = 2.0
FPS = 24

# Instagram video işleme
ILK_BEKLEME = 5
KONTROL_ARALIGI = 5
MAKSIMUM_BEKLEME = 180


# ============================================================
# SON İÇERİK DOSYASINI BUL
# ============================================================

def son_icerik_dosyasi():

    dosyalar = sorted(
        CIKTI_KLASOR.glob("icerik_*.json")
    )

    if not dosyalar:
        raise FileNotFoundError(
            "cikti/ klasöründe içerik dosyası bulunamadı."
        )

    return dosyalar[-1]


# ============================================================
# İÇERİĞE AİT GÖRSEL KLASÖRÜNÜ BUL
# ============================================================

def gorsel_klasoru_bul(tarih):

    hedef_klasor = (
        GORSEL_KLASOR / tarih
    )

    if not hedef_klasor.exists():

        raise FileNotFoundError(
            f"İçerik için görsel klasörü bulunamadı: "
            f"{hedef_klasor}"
        )

    if not hedef_klasor.is_dir():

        raise NotADirectoryError(
            f"Görsel yolu klasör değil: "
            f"{hedef_klasor}"
        )

    return hedef_klasor


# ============================================================
# REEL SESLENDİRME METNİNİ HAZIRLA
# ============================================================

def reel_ses_metni_olustur(icerik):

    reel = icerik.get("reel")

    if not reel:
        raise ValueError(
            "İçerik JSON dosyasında 'reel' bölümü bulunamadı."
        )

    sahneler = reel.get(
        "sahneler",
        []
    )

    if not sahneler:
        raise ValueError(
            "Reel içerisinde 'sahneler' bulunamadı."
        )

    parcalar = []

    # Sahne metinleri
    for sahne in sahneler:

        if sahne and str(sahne).strip():

            parcalar.append(
                str(sahne).strip()
            )

    # CTA
    cta = reel.get(
        "cta",
        ""
    )

    if cta and str(cta).strip():

        parcalar.append(
            str(cta).strip()
        )

    metin = " ".join(
        parcalar
    )

    if not metin.strip():

        raise ValueError(
            "Seslendirme için kullanılabilecek metin bulunamadı."
        )

    return metin


# ============================================================
# ELEVENLABS ALMANCA SES ÜRET
# ============================================================

def ses_uret(icerik, tarih):

    ses_klasoru = (
        REEL_KLASOR / "sesler"
    )

    ses_klasoru.mkdir(
        parents=True,
        exist_ok=True
    )

    ses_yolu = (
        ses_klasoru
        / f"ses_{tarih}.mp3"
    )

    # Daha önce varsa tekrar üretme
    if ses_yolu.exists() and ses_yolu.stat().st_size > 0:

        print(
            f"✓ Ses dosyası zaten mevcut: {ses_yolu}"
        )

        return ses_yolu

    metin = reel_ses_metni_olustur(
        icerik
    )

    print()
    print(
        "ElevenLabs mit deutscher Sprachausgabe wird erstellt..."
    )

    print(
        f"Voice ID: {ELEVENLABS_VOICE_ID}"
    )

    print(
        f"Modell: {ELEVENLABS_MODEL_ID}"
    )

    print(
        f"Sprachtext: {metin}"
    )

    url = (
        "https://api.elevenlabs.io/v1/text-to-speech/"
        f"{ELEVENLABS_VOICE_ID}"
    )

    params = {
        "output_format": ELEVENLABS_OUTPUT_FORMAT
    }

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    data = {
        "text": metin,
        "model_id": ELEVENLABS_MODEL_ID,
    }

    try:

        yanit = requests.post(
            url,
            params=params,
            headers=headers,
            json=data,
            timeout=180
        )

    except requests.RequestException as hata:

        raise RuntimeError(
            f"ElevenLabs Verbindungsfehler: {hata}"
        )

    print(
        f"ElevenLabs HTTP-Status: {yanit.status_code}"
    )

    if not yanit.ok:

        print()
        print(
            "❌ ELEVENLABS FEHLER"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    if not yanit.content:

        raise RuntimeError(
            "ElevenLabs Erfolgreiche Antwort aber Audiodaten leer."
        )

    # MP3 speichern
    with open(
        ses_yolu,
        "wb"
    ) as dosya:

        dosya.write(
            yanit.content
        )

    # Datei prüfen
    if not ses_yolu.exists():

        raise FileNotFoundError(
            f"Audiodatei konnte nicht erstellt werden: {ses_yolu}"
        )

    dosya_boyutu = (
        ses_yolu.stat().st_size
    )

    if dosya_boyutu == 0:

        raise RuntimeError(
            "ElevenLabs Audiodatei mit 0 Byte erstellt."
        )

    print(
        f"✓ Deutsche Sprache erstellt: {ses_yolu}"
    )

    print(
        f"✓ Dateigröße: {dosya_boyutu} byte"
    )

    return ses_yolu


# ============================================================
# AUDIO-DAUER MESSEN
# ============================================================

def ses_suresini_bul(ses_yolu):

    try:

        sonuc = subprocess.run(

            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(ses_yolu),
            ],

            capture_output=True,
            text=True,

            check=True
        )

    except FileNotFoundError:

        raise RuntimeError(
            "ffprobe nicht gefunden. "
            "FFmpeg-Installation prüfen."
        )

    try:

        sure = float(
            sonuc.stdout.strip()
        )

    except ValueError:

        raise RuntimeError(
            f"Audiodauer konnte nicht gelesen werden: "
            f"{sonuc.stdout}"
        )

    if sure <= 0:

        raise RuntimeError(
            "Audiodauer 0 oder ungültig."
        )

    print(
        f"✓ Audiodauer: {sure:.2f} Sekunden"
    )

    return sure


# ============================================================
# VIDEO ERSTELLEN
# ============================================================

def video_uret(
    gorsel_klasoru,
    icerik_dosyasi,
    ses_yolu
):

    icerik = json.loads(
        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    tarih = icerik["tarih"]

    REEL_KLASOR.mkdir(
        exist_ok=True
    )

    # --------------------------------------------------------
    # PNG-Dateien
    # --------------------------------------------------------

    png_dosyalari = sorted(
        gorsel_klasoru.glob("*.png")
    )

    if not png_dosyalari:

        raise FileNotFoundError(
            f"PNG nicht gefunden in {gorsel_klasoru}."
        )

    print(
        f"{len(png_dosyalari)} PNG-Dateien gefunden."
    )

    # --------------------------------------------------------
    # Audiodauer
    # --------------------------------------------------------

    ses_suresi = (
        ses_suresini_bul(
            ses_yolu
        )
    )

    # --------------------------------------------------------
    # Dauer pro Folie
    # --------------------------------------------------------

    minimum_video_suresi = (
        len(png_dosyalari)
        * SLAYT_SURESI
    )

    video_suresi = max(
        ses_suresi,
        minimum_video_suresi
    )

    slayt_suresi = (
        video_suresi
        / len(png_dosyalari)
    )

    print(
        f"Video-Zieldauer: {video_suresi:.2f} Sekunden"
    )

    print(
        f"Dauer pro Folie: {slayt_suresi:.2f} Sekunden"
    )

    # --------------------------------------------------------
    # Videopfad
    # --------------------------------------------------------

    reel_yolu = (
        REEL_KLASOR
        / f"reel_{tarih}.mp4"
    )

    # --------------------------------------------------------
    # FFmpeg concat-Datei
    # --------------------------------------------------------

    files_txt = (
        REEL_KLASOR
        / f"files_{tarih}.txt"
    )

    with open(
        files_txt,
        "w",
        encoding="utf-8"
    ) as f:

        for png_yolu in png_dosyalari:

            dosya = (
                png_yolu.resolve()
            )

            f.write(
                f"file '{dosya}'\n"
            )

            f.write(
                f"duration {slayt_suresi}\n"
            )

        # Letzte Folie erneut hinzufügen
        son_png = (
            png_dosyalari[-1].resolve()
        )

        f.write(
            f"file '{son_png}'\n"
        )

    # --------------------------------------------------------
    # FFmpeg-Prüfung
    # --------------------------------------------------------

    try:

        ffmpeg_kontrol = subprocess.run(
            [
                "ffmpeg",
                "-version"
            ],

            capture_output=True,
            text=True
        )

    except FileNotFoundError:

        raise RuntimeError(
            "FFmpeg nicht gefunden."
        )

    if ffmpeg_kontrol.returncode != 0:

        raise RuntimeError(
            "FFmpeg konnte nicht ausgeführt werden."
        )

    # --------------------------------------------------------
    # Video erstellen
    # --------------------------------------------------------

    print()
    print(
        "FFmpeg erstellt Reel mit Sprachausgabe..."
    )

    ffmpeg_komut = [

        "ffmpeg",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(files_txt),

        "-i",
        str(ses_yolu),

        "-vf",
        (
            "scale=1080:1350:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1350:(ow-iw)/2:(oh-ih)/2"
        ),

        "-r",
        str(FPS),

        "-c:v",
        "libx264",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-af",
        "apad",

        "-shortest",

        "-movflags",
        "+faststart",

        "-y",

        str(reel_yolu)
    ]

    subprocess.run(
        ffmpeg_komut,
        check=True
    )

    # --------------------------------------------------------
    # Abschließende Prüfung
    # --------------------------------------------------------

    if not reel_yolu.exists():

        raise FileNotFoundError(
            f"FFmpeg Video konnte nicht erstellt werden: "
            f"{reel_yolu}"
        )

    video_boyutu = (
        reel_yolu.stat().st_size
    )

    if video_boyutu == 0:

        raise RuntimeError(
            "Videodatei mit 0 Byte erstellt."
        )

    print(
        f"✓ Deutsches Reel bereit: {reel_yolu}"
    )

    print(
        f"✓ Videogröße: {video_boyutu} byte"
    )

    return reel_yolu


# ============================================================
# REEL ZU GITHUB HOCHLADEN
# ============================================================

def reel_github_ye_gonder(video_yolu):

    print(
        "\nVideo wird zu GitHub hochgeladen..."
    )

    try:

        subprocess.run(
            [
                "git",
                "fetch",
                "origin"
            ],

            check=True
        )

        subprocess.run(
            [
                "git",
                "add",
                "reels/"
            ],

            check=True
        )

        commit_sonucu = subprocess.run(

            [
                "git",
                "commit",
                "-m",
                "reel: Deutsches Video mit Sprachausgabe"
            ],

            capture_output=True,
            text=True
        )

        if commit_sonucu.returncode != 0:

            cikti = (
                commit_sonucu.stdout
                + commit_sonucu.stderr
            ).lower()

            if "nothing to commit" in cikti:

                print(
                    "Keine Änderungen zum Commit für neues Reel gefunden."
                )

            else:

                print(
                    "Git Commit-Warnung:"
                )

                print(
                    commit_sonucu.stdout
                )

                print(
                    commit_sonucu.stderr
                )

        else:

            print(
                "✓ Reel gecommitet."
            )

        subprocess.run(
            [
                "git",
                "push",
                "origin",
                "main"
            ],

            check=True
        )

        print(
            "✓ Deutsches Reel zu GitHub hochgeladen."
        )

    except subprocess.CalledProcessError as hata:

        raise RuntimeError(
            f"GitHub Reel-Upload fehlgeschlagen: "
            f"{hata}"
        )

    raw_url = (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"main/reels/"
        f"{video_yolu.name}"
    )

    print(
        f"Instagram Video-URL:\n{raw_url}"
    )

    return raw_url


# ============================================================
# REEL CONTAINER ERSTELLEN
# ============================================================

def reel_container_olustur(video_url):

    print(
        "\nInstagram Reels Container wird erstellt..."
    )

    # Reel-Beschreibung
    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    try:

        icerik = json.loads(
            icerik_dosyasi.read_text(
                encoding="utf-8"
            )
        )

        reel = icerik.get(
            "reel",
            {}
        )

        caption = reel.get(
            "baslik",
            "Reels Video 🎬"
        )

        hashtagler = icerik.get(
            "hashtagler",
            []
        )

        if hashtagler:

            caption += (
                "\n\n"
                + " ".join(
                    hashtagler
                )
            )

    except Exception:

        caption = (
            "Reels Video 🎬"
        )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media",

        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        print(
            "FEHLER - Reels Container konnte nicht erstellt werden:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = (
        yanit.json()["id"]
    )

    print(
        f"✓ Reels Container erstellt: "
        f"{container_id}"
    )

    return container_id


# ============================================================
# CONTAINER STATUS
# ============================================================

def container_durumunu_kontrol_et(container_id):

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

        veri = yanit.json()

        status_code = veri.get(
            "status_code"
        )

        status = veri.get(
            "status"
        )

        print(
            f"Instagram Container Status: "
            f"{status_code or status}"
        )

        return status_code or status

    except requests.RequestException as hata:

        print(
            f"Fehler bei Statusprüfung: {hata}"
        )

        return None


# ============================================================
# AUF REEL-FERTIGSTELLUNG WARTEN
# ============================================================

def container_hazir_olmasini_bekle(container_id):

    print(
        "\nInstagram verarbeitet das Video..."
    )

    print(
        f"Warte {ILK_BEKLEME} Sekunden..."
    )

    time.sleep(
        ILK_BEKLEME
    )

    baslangic_zamani = time.time()

    while True:

        gecen_sure = (
            time.time()
            - baslangic_zamani
        )

        if gecen_sure > MAKSIMUM_BEKLEME:

            raise TimeoutError(
                "Instagram Video war nicht "
                f"innerhalb von {MAKSIMUM_BEKLEME} Sekunden bereit."
            )

        durum = (
            container_durumunu_kontrol_et(
                container_id
            )
        )

        if durum == "FINISHED":

            print(
                "✓ Instagram Video ist bereit."
            )

            return True

        if durum in (
            "IN_PROGRESS",
            "PROCESSING"
        ):

            print(
                f"Video wird noch verarbeitet... "
                f"{int(gecen_sure)} Sekunden vergangen."
            )

            time.sleep(
                KONTROL_ARALIGI
            )

            continue

        if durum == "ERROR":

            raise RuntimeError(
                "Beim Verarbeiten des Reels "
                "ist ein Fehler aufgetreten."
            )

        print(
            f"Unerwarteter Container-Status: {durum}"
        )

        time.sleep(
            KONTROL_ARALIGI
        )


# ============================================================
# REEL VERÖFFENTLICHEN
# ============================================================

def reel_yayinla(video_yolu):

    # --------------------------------------------------------
    # GitHub
    # --------------------------------------------------------

    video_url = (
        reel_github_ye_gonder(
            video_yolu
        )
    )

    # --------------------------------------------------------
    # Container
    # --------------------------------------------------------

    container_id = (
        reel_container_olustur(
            video_url
        )
    )

    # --------------------------------------------------------
    # Auf Fertigstellung warten
    # --------------------------------------------------------

    container_hazir_olmasini_bekle(
        container_id
    )

    # --------------------------------------------------------
    # Veröffentlichen
    # --------------------------------------------------------

    print(
        "\nInstagram Reels wird veröffentlicht..."
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
            "FEHLER - Reel konnte nicht veröffentlicht werden:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    post_id = (
        yanit.json().get("id")
    )

    print(
        "\n========================================"
    )

    print(
        "✓ DEUTSCHES REELS ERFOLGREICH VERÖFFENTLICHT!"
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
        "Instagram Reels mit deutscher Sprachausgabe"
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

    # --------------------------------------------------------
    # 2. Inhalt lesen
    # --------------------------------------------------------

    icerik = json.loads(
        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------------
    # 3. Datum
    # --------------------------------------------------------

    tarih = icerik.get(
        "tarih"
    )

    if not tarih:

        raise ValueError(
            "'tarih' nicht im JSON gefunden."
        )

    # --------------------------------------------------------
    # 4. Bildordner für diesen Inhalt
    # --------------------------------------------------------

    gorsel_klasoru = (
        gorsel_klasoru_bul(
            tarih
        )
    )

    print(
        f"\nInhalt: {icerik_dosyasi.name}"
    )

    print(
        f"Bilder: {gorsel_klasoru}"
    )

    # --------------------------------------------------------
    # 5. ElevenLabs Sprache erstellen
    # --------------------------------------------------------

    ses_yolu = (
        ses_uret(
            icerik,
            tarih
        )
    )

    # --------------------------------------------------------
    # 6. Video erstellen
    # --------------------------------------------------------

    video_yolu = (
        video_uret(
            gorsel_klasoru,
            icerik_dosyasi,
            ses_yolu
        )
    )

    # --------------------------------------------------------
    # 7. Reel veröffentlichen
    # --------------------------------------------------------

    reel_yayinla(
        video_yolu
    )

    print(
        "\n✓ Deutsches Reel erfolgreich veröffentlicht!"
    )


# ============================================================
# PROGRAMM AUSFÜHREN
# ============================================================

if __name__ == "__main__":
    main()