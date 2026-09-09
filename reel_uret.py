import os
import json
import time
import subprocess
from pathlib import Path

import requests
import azure.cognitiveservices.speech as speechsdk
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
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

# Microsoft Azure Speech
AZURE_SPEECH_KEY = os.environ["AZURE_SPEECH_KEY"]
AZURE_SPEECH_REGION = os.environ["AZURE_SPEECH_REGION"]
AZURE_SPEECH_VOICE = "de-DE-ConradNeural"

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

# Instagram işlem ayarları
ILK_BEKLEME = 10
KONTROL_ARALIGI = 10
MAKSIMUM_BEKLEME = 300


# ============================================================
# İÇERİK VE GÖRSEL BULMA
# ============================================================

def son_icerik_dosyasi():
    dosyalar = sorted(CIKTI_KLASOR.glob("icerik_*.json"))

    if not dosyalar:
        raise FileNotFoundError(
            "cikti/ klasöründe icerik_*.json dosyası bulunamadı."
        )

    return dosyalar[-1]


def gorsel_klasoru_bul(tarih):
    klasor = GORSEL_KLASOR / tarih

    if not klasor.exists():
        raise FileNotFoundError(
            f"Görsel klasörü bulunamadı: {klasor}"
        )

    if not klasor.is_dir():
        raise NotADirectoryError(
            f"Görsel yolu klasör değil: {klasor}"
        )

    return klasor


def reel_ses_metni_olustur(icerik):
    reel = icerik.get("reel")

    if not reel:
        raise ValueError(
            "İçerik JSON dosyasında 'reel' bölümü bulunamadı."
        )

    sahneler = reel.get("sahneler", [])
    parcalar = []

    for sahne in sahneler:
        if sahne and str(sahne).strip():
            parcalar.append(str(sahne).strip())

    cta = reel.get("cta", "")

    if cta and str(cta).strip():
        parcalar.append(str(cta).strip())

    metin = " ".join(parcalar).strip()

    if not metin:
        raise ValueError(
            "Seslendirme için kullanılabilecek Almanca metin bulunamadı."
        )

    return metin


# ============================================================
# AZURE ALMANCA SESLENDİRME
# ============================================================

def ses_uret(icerik, tarih):
    ses_klasoru = REEL_KLASOR / "sesler"
    ses_klasoru.mkdir(parents=True, exist_ok=True)

    ses_yolu = ses_klasoru / f"ses_{tarih}.mp3"

    if ses_yolu.exists() and ses_yolu.stat().st_size > 0:
        print(f"✓ Azure ses dosyası zaten mevcut: {ses_yolu}")
        return ses_yolu

    metin = reel_ses_metni_olustur(icerik)

    print("\nAzure ile Almanca seslendirme oluşturuluyor...")
    print(f"Ses: {AZURE_SPEECH_VOICE}")
    print(f"Metin: {metin}")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )

    speech_config.speech_synthesis_voice_name = AZURE_SPEECH_VOICE

    # MP3 çıktı formatı
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=str(ses_yolu)
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    result = synthesizer.speak_text_async(metin).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"✓ Azure Almanca ses oluşturuldu: {ses_yolu}")

    elif result.reason == speechsdk.ResultReason.Canceled:
        ayrinti = result.cancellation_details

        raise RuntimeError(
            "Azure seslendirme iptal edildi: "
            f"{ayrinti.reason}; {ayrinti.error_details}"
        )

    else:
        raise RuntimeError(
            f"Azure seslendirme başarısız: {result.reason}"
        )

    if not ses_yolu.exists() or ses_yolu.stat().st_size == 0:
        raise RuntimeError(
            f"Ses dosyası oluşturulamadı veya boş: {ses_yolu}"
        )

    print(
        f"✓ Ses dosyası boyutu: "
        f"{ses_yolu.stat().st_size} byte"
    )

    return ses_yolu


# ============================================================
# SES SÜRESİ
# ============================================================

def ses_suresini_bul(ses_yolu):
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

    try:
        sure = float(sonuc.stdout.strip())
    except ValueError:
        raise RuntimeError(
            f"Ses süresi okunamadı: {sonuc.stdout}"
        )

    if sure <= 0:
        raise RuntimeError("Ses süresi geçersiz.")

    print(f"✓ Ses süresi: {sure:.2f} saniye")
    return sure


# ============================================================
# REEL VİDEOSU OLUŞTURMA
# ============================================================

def video_uret(gorsel_klasoru, icerik_dosyasi, ses_yolu):
    icerik = json.loads(
        icerik_dosyasi.read_text(encoding="utf-8")
    )

    tarih = icerik["tarih"]
    REEL_KLASOR.mkdir(parents=True, exist_ok=True)

    png_dosyalari = sorted(gorsel_klasoru.glob("*.png"))

    if not png_dosyalari:
        raise FileNotFoundError(
            f"{gorsel_klasoru} içinde PNG bulunamadı."
        )

    ses_suresi = ses_suresini_bul(ses_yolu)

    minimum_video_suresi = len(png_dosyalari) * SLAYT_SURESI
    video_suresi = max(ses_suresi, minimum_video_suresi)
    slayt_suresi = video_suresi / len(png_dosyalari)

    print(f"Video süresi: {video_suresi:.2f} saniye")
    print(f"Slayt süresi: {slayt_suresi:.2f} saniye")

    reel_yolu = REEL_KLASOR / f"reel_{tarih}.mp4"
    files_txt = REEL_KLASOR / f"files_{tarih}.txt"

    with files_txt.open("w", encoding="utf-8") as dosya:
        for png_yolu in png_dosyalari:
            dosya.write(f"file '{png_yolu.resolve()}'\n")
            dosya.write(f"duration {slayt_suresi}\n")

        # Son görüntüyü tekrar ekle
        dosya.write(
            f"file '{png_dosyalari[-1].resolve()}'\n"
        )

    print("\nFFmpeg ile seslendirmeli Reel oluşturuluyor...")

    ffmpeg_komut = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(files_txt),
        "-i", str(ses_yolu),

        # Instagram Reels için 1080x1350 dikey format
        "-vf",
        (
            "scale=1080:1350:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1350:(ow-iw)/2:(oh-ih)/2"
        ),

        "-r", str(FPS),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-af", "apad",
        "-shortest",
        "-movflags", "+faststart",
        str(reel_yolu),
    ]

    subprocess.run(ffmpeg_komut, check=True)

    if not reel_yolu.exists() or reel_yolu.stat().st_size == 0:
        raise RuntimeError(
            f"Reel dosyası oluşturulamadı: {reel_yolu}"
        )

    print(f"✓ Reel oluşturuldu: {reel_yolu}")
    print(f"✓ Video boyutu: {reel_yolu.stat().st_size} byte")

    return reel_yolu


# ============================================================
# GITHUB'A YÜKLEME
# ============================================================

def reel_githuba_gonder(video_yolu):
    print("\nReel GitHub'a yükleniyor...")

    subprocess.run(
        ["git", "fetch", "origin"],
        check=True
    )

    subprocess.run(
        ["git", "add", "reels/"],
        check=True
    )

    commit = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "reel: Azure Almanca seslendirme"
        ],
        capture_output=True,
        text=True
    )

    if commit.returncode == 0:
        print("✓ Reel commit edildi.")
    else:
        cikti = (
            commit.stdout + commit.stderr
        ).lower()

        if "nothing to commit" in cikti:
            print("Yeni commit edilecek değişiklik yok.")
        else:
            print(commit.stdout)
            print(commit.stderr)

    subprocess.run(
        ["git", "push", "origin", GITHUB_BRANCH],
        check=True
    )

    print("✓ Reel GitHub'a yüklendi.")

    video_url = (
        "https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"{GITHUB_BRANCH}/"
        f"reels/{video_yolu.name}"
    )

    print(f"Instagram video URL'si:\n{video_url}")

    # raw.githubusercontent.com önbelleğinin güncellenmesi için bekleme
    time.sleep(15)

    return video_url


# ============================================================
# INSTAGRAM CONTAINER
# ============================================================

def reel_container_olustur(video_url):
    icerik_dosyasi = son_icerik_dosyasi()

    try:
        icerik = json.loads(
            icerik_dosyasi.read_text(encoding="utf-8")
        )

        reel = icerik.get("reel", {})
        caption = reel.get("baslik", "Reels Video 🎬")

        hashtagler = icerik.get("hashtagler", [])

        if hashtagler:
            caption += "\n\n" + " ".join(hashtagler)

    except Exception:
        caption = "Reels Video 🎬"

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
        print(yanit.text)
        yanit.raise_for_status()

    container_id = yanit.json()["id"]

    print(f"✓ Instagram Reels container oluşturuldu: {container_id}")

    return container_id


# ============================================================
# CONTAINER DURUMU
# ============================================================

def container_durumunu_kontrol_et(container_id):
    yanit = requests.get(
        f"{API_TEMEL}/{container_id}",
        params={
            "fields": "status_code,status",
            "access_token": ACCESS_TOKEN,
        },
        timeout=30
    )

    if not yanit.ok:
        print(yanit.text)
        return None

    veri = yanit.json()

    return veri.get("status_code") or veri.get("status")


def container_hazir_olmasini_bekle(container_id):
    print("\nInstagram videoyu işliyor...")
    time.sleep(ILK_BEKLEME)

    baslangic = time.time()

    while True:
        gecen = time.time() - baslangic

        if gecen > MAKSIMUM_BEKLEME:
            raise TimeoutError(
                "Instagram container zamanında hazır olmadı."
            )

        durum = container_durumunu_kontrol_et(container_id)

        print(f"Instagram container durumu: {durum}")

        if durum == "FINISHED":
            print("✓ Instagram videosu hazır.")
            return

        if durum == "ERROR":
            raise RuntimeError(
                "Instagram Reel videosunu işlerken hata oluştu."
            )

        time.sleep(KONTROL_ARALIGI)


# ============================================================
# REEL YAYINLAMA
# ============================================================

def reel_yayinla(video_yolu):
    video_url = reel_githuba_gonder(video_yolu)
    container_id = reel_container_olustur(video_url)

    container_hazir_olmasini_bekle(container_id)

    print("\nInstagram Reels yayınlanıyor...")

    yanit = requests.post(
        f"{API_TEMEL}/{IG_USER_ID}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },
        timeout=60
    )

    if not yanit.ok:
        print(yanit.text)
        yanit.raise_for_status()

    post_id = yanit.json().get("id")

    print("\n========================================")
    print("✓ ALMANCA REEL BAŞARIYLA YAYINLANDI")
    print(f"Post ID: {post_id}")
    print("========================================")

    return post_id


# ============================================================
# ANA PROGRAM
# ============================================================

def main():
    print("========================================")
    print("Instagram Reels - Azure Almanca Seslendirme")
    print("========================================")

    icerik_dosyasi = son_icerik_dosyasi()

    icerik = json.loads(
        icerik_dosyasi.read_text(encoding="utf-8")
    )

    tarih = icerik.get("tarih")

    if not tarih:
        raise ValueError(
            "İçerik JSON dosyasında 'tarih' bulunamadı."
        )

    gorsel_klasoru = gorsel_klasoru_bul(tarih)

    print(f"İçerik dosyası: {icerik_dosyasi}")
    print(f"Görsel klasörü: {gorsel_klasoru}")

    ses_yolu = ses_uret(icerik, tarih)

    video_yolu = video_uret(
        gorsel_klasoru,
        icerik_dosyasi,
        ses_yolu
    )

    reel_yayinla(video_yolu)

    print("\n✓ Almanca seslendirmeli Reel başarıyla yayınlandı.")


if __name__ == "__main__":
    main()
