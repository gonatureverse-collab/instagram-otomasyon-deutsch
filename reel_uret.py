import os
import json
import time
import subprocess
from pathlib import Path

import requests
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv


# ============================================================
# ORTAM DEĞİŞKENLERİ
# ============================================================

load_dotenv()


def ortam_degiskeni_al(anahtar):
    deger = os.environ.get(anahtar)

    if not deger:
        raise EnvironmentError(
            f"Eksik ortam değişkeni: {anahtar}"
        )

    return deger.strip()


# Instagram
ACCESS_TOKEN = ortam_degiskeni_al(
    "INSTAGRAM_ACCESS_TOKEN"
)

IG_USER_ID = ortam_degiskeni_al(
    "INSTAGRAM_BUSINESS_ACCOUNT_ID"
)


# GitHub
GITHUB_USERNAME = ortam_degiskeni_al(
    "GITHUB_USERNAME"
)

GITHUB_REPO = ortam_degiskeni_al(
    "GITHUB_REPO"
)

GITHUB_BRANCH = os.environ.get(
    "GITHUB_BRANCH",
    "main"
).strip()


# Azure Speech
AZURE_SPEECH_KEY = ortam_degiskeni_al(
    "AZURE_SPEECH_KEY"
)

AZURE_SPEECH_REGION = ortam_degiskeni_al(
    "AZURE_SPEECH_REGION"
)

AZURE_SPEECH_VOICE = "de-DE-ConradNeural"


# ============================================================
# INSTAGRAM API
# ============================================================

API_SURUM = "v21.0"

# Instagram Business hesabı için Facebook Graph API kullanılır
API_TEMEL = (
    f"https://graph.facebook.com/{API_SURUM}"
)


# ============================================================
# KLASÖRLER VE VİDEO AYARLARI
# ============================================================

CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")
REEL_KLASOR = Path("reels")
SES_KLASOR = REEL_KLASOR / "sesler"

SLAYT_MINIMUM_SURESI = 2.0
FPS = 24

ILK_BEKLEME = 15
KONTROL_ARALIGI = 10
MAKSIMUM_BEKLEME = 300


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def json_dosyasi_oku(dosya_yolu):
    return json.loads(
        dosya_yolu.read_text(
            encoding="utf-8"
        )
    )


def son_icerik_dosyasi():
    dosyalar = sorted(
        CIKTI_KLASOR.glob("icerik_*.json")
    )

    if not dosyalar:
        raise FileNotFoundError(
            "cikti klasöründe icerik_*.json dosyası bulunamadı."
        )

    return dosyalar[-1]


def gorsel_klasoru_bul(tarih):
    klasor = GORSEL_KLASOR / tarih

    if not klasor.exists():
        raise FileNotFoundError(
            f"Görsel klasörü bulunamadı: {klasor}"
        )

    return klasor


def png_dosyalarini_bul(gorsel_klasoru):
    dosyalar = sorted(
        gorsel_klasoru.glob("*.png")
    )

    if not dosyalar:
        raise FileNotFoundError(
            f"{gorsel_klasoru} içinde PNG görseli bulunamadı."
        )

    return dosyalar


# ============================================================
# REEL SES METNİ
# ============================================================

def reel_ses_metni_olustur(icerik):
    reel = icerik.get("reel")

    if not reel:
        raise ValueError(
            "JSON dosyasında 'reel' bölümü bulunamadı."
        )

    parcalar = []

    sahneler = reel.get(
        "sahneler",
        []
    )

    for sahne in sahneler:
        if sahne and str(sahne).strip():
            parcalar.append(
                str(sahne).strip()
            )

    cta = reel.get(
        "cta",
        ""
    )

    if cta and str(cta).strip():
        parcalar.append(
            str(cta).strip()
        )

    metin = " ".join(parcalar).strip()

    if not metin:
        raise ValueError(
            "Seslendirme için metin bulunamadı."
        )

    return metin


# ============================================================
# AZURE ALMANCA SESLENDİRME
# ============================================================

def ses_uret(icerik, tarih):
    SES_KLASOR.mkdir(
        parents=True,
        exist_ok=True
    )

    ses_yolu = (
        SES_KLASOR /
        f"azure_ses_{tarih}.mp3"
    )

    if (
        ses_yolu.exists()
        and ses_yolu.stat().st_size > 0
    ):
        print(
            f"✓ Ses dosyası zaten mevcut: {ses_yolu}"
        )
        return ses_yolu

    metin = reel_ses_metni_olustur(
        icerik
    )

    print()
    print(
        "Azure ile Almanca seslendirme oluşturuluyor..."
    )
    print(
        f"Ses: {AZURE_SPEECH_VOICE}"
    )
    print(
        f"Metin: {metin}"
    )

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )

    speech_config.speech_synthesis_voice_name = (
        AZURE_SPEECH_VOICE
    )

    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat
        .Audio16Khz128KBitRateMonoMp3
    )

    audio_config = (
        speechsdk.audio.AudioOutputConfig(
            filename=str(ses_yolu)
        )
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    sonuc = (
        synthesizer
        .speak_text_async(metin)
        .get()
    )

    if (
        sonuc.reason
        == speechsdk.ResultReason.SynthesizingAudioCompleted
    ):
        print(
            f"✓ Azure Almanca ses oluşturuldu: {ses_yolu}"
        )

    elif (
        sonuc.reason
        == speechsdk.ResultReason.Canceled
    ):
        ayrinti = sonuc.cancellation_details

        raise RuntimeError(
            "Azure seslendirme iptal edildi: "
            f"{ayrinti.reason}; "
            f"{ayrinti.error_details}"
        )

    else:
        raise RuntimeError(
            f"Azure seslendirme başarısız: "
            f"{sonuc.reason}"
        )

    if (
        not ses_yolu.exists()
        or ses_yolu.stat().st_size == 0
    ):
        raise RuntimeError(
            "Azure ses dosyası oluşturulamadı "
            "veya dosya boş."
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
    komut = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(ses_yolu)
    ]

    sonuc = subprocess.run(
        komut,
        capture_output=True,
        text=True,
        check=True
    )

    try:
        sure = float(
            sonuc.stdout.strip()
        )
    except ValueError:
        raise RuntimeError(
            "Ses süresi okunamadı."
        )

    if sure <= 0:
        raise RuntimeError(
            "Ses süresi geçersiz."
        )

    print(
        f"✓ Ses süresi: {sure:.2f} saniye"
    )

    return sure


# ============================================================
# CONCAT DOSYASI
# ============================================================

def concat_dosyasi_olustur(
    png_dosyalari,
    dosya_yolu,
    slayt_suresi
):
    with dosya_yolu.open(
        "w",
        encoding="utf-8"
    ) as dosya:

        for png_yolu in png_dosyalari:
            guvenli_yol = (
                str(png_yolu.resolve())
                .replace("'", "'\\''")
            )

            dosya.write(
                f"file '{guvenli_yol}'\n"
            )

            dosya.write(
                f"duration {slayt_suresi:.6f}\n"
            )

        # concat formatının son görseli göstermesi gerekir
        son_gorsel = (
            str(png_dosyalari[-1].resolve())
            .replace("'", "'\\''")
        )

        dosya.write(
            f"file '{son_gorsel}'\n"
        )


# ============================================================
# VİDEO ÜRETİMİ
# ============================================================

def video_uret(
    gorsel_klasoru,
    icerik_dosyasi,
    ses_yolu
):
    icerik = json_dosyasi_oku(
        icerik_dosyasi
    )

    tarih = icerik.get(
        "tarih"
    )

    if not tarih:
        raise ValueError(
            "JSON dosyasında tarih bulunamadı."
        )

    png_dosyalari = png_dosyalarini_bul(
        gorsel_klasoru
    )

    ses_suresi = ses_suresini_bul(
        ses_yolu
    )

    minimum_video_suresi = (
        len(png_dosyalari)
        * SLAYT_MINIMUM_SURESI
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
        f"Video süresi: {video_suresi:.2f} saniye"
    )

    print(
        f"Slayt süresi: {slayt_suresi:.2f} saniye"
    )

    REEL_KLASOR.mkdir(
        parents=True,
        exist_ok=True
    )

    reel_yolu = (
        REEL_KLASOR /
        f"reel_{tarih}.mp4"
    )

    files_txt = (
        REEL_KLASOR /
        f"files_{tarih}.txt"
    )

    concat_dosyasi_olustur(
        png_dosyalari,
        files_txt,
        slayt_suresi
    )

    print()
    print(
        "FFmpeg ile Reel oluşturuluyor..."
    )

    ffmpeg_komut = [
        "ffmpeg",
        "-y",

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
            "pad=1080:1350:"
            "(ow-iw)/2:(oh-ih)/2,"
            "format=yuv420p"
        ),

        "-r",
        str(FPS),

        "-t",
        f"{video_suresi:.3f}",

        "-c:v",
        "libx264",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-ar",
        "44100",

        "-ac",
        "2",

        "-shortest",

        "-movflags",
        "+faststart",

        str(reel_yolu)
    ]

    subprocess.run(
        ffmpeg_komut,
        check=True
    )

    if (
        not reel_yolu.exists()
        or reel_yolu.stat().st_size == 0
    ):
        raise RuntimeError(
            "Reel dosyası oluşturulamadı "
            "veya dosya boş."
        )

    print(
        f"✓ Reel oluşturuldu: {reel_yolu}"
    )

    print(
        f"✓ Video boyutu: "
        f"{reel_yolu.stat().st_size} byte"
    )

    return reel_yolu


# ============================================================
# GITHUB'A GÖNDERME
# ============================================================

def reel_githuba_gonder(video_yolu):
    print()
    print(
        "Reel GitHub'a yükleniyor..."
    )

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

    commit_ciktisi = (
        commit.stdout
        + commit.stderr
    ).lower()

    if commit.returncode == 0:
        print(
            "✓ Reel commit edildi."
        )

    elif "nothing to commit" in commit_ciktisi:
        print(
            "Yeni commit edilecek değişiklik yok."
        )

    else:
        print(commit.stdout)
        print(commit.stderr)

    subprocess.run(
        [
            "git",
            "push",
            "origin",
            GITHUB_BRANCH
        ],
        check=True
    )

    print(
        "✓ Reel GitHub'a yüklendi."
    )

    video_url = (
        "https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"{GITHUB_BRANCH}/"
        f"reels/{video_yolu.name}"
    )

    print(
        f"Instagram video URL'si:\n{video_url}"
    )

    # GitHub Raw CDN'nin dosyayı görmesi için bekleme
    time.sleep(20)

    return video_url


# ============================================================
# INSTAGRAM CAPTION
# ============================================================

def reel_caption_al(icerik_dosyasi):
    try:
        icerik = json_dosyasi_oku(
            icerik_dosyasi
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
                    str(x)
                    for x in hashtagler
                )
            )

        return caption

    except Exception:
        return "Reels Video 🎬"


# ============================================================
# INSTAGRAM CONTAINER
# ============================================================

def reel_container_olustur(
    video_url,
    caption
):
    print()
    print(
        "Instagram Reels container oluşturuluyor..."
    )

    yanit = requests.post(
        f"{API_TEMEL}/{IG_USER_ID}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": ACCESS_TOKEN
        },
        timeout=60
    )

    if not yanit.ok:
        print(
            "Instagram API hatası:"
        )
        print(
            yanit.text
        )

        yanit.raise_for_status()

    veri = yanit.json()
    container_id = veri.get("id")

    if not container_id:
        raise RuntimeError(
            f"Instagram container ID döndürmedi: {veri}"
        )

    print(
        "✓ Instagram container oluşturuldu: "
        f"{container_id}"
    )

    return container_id


# ============================================================
# CONTAINER DURUMU
# ============================================================

def container_durumunu_kontrol_et(
    container_id
):
    yanit = requests.get(
        f"{API_TEMEL}/{container_id}",
        params={
            "fields": "status_code,status",
            "access_token": ACCESS_TOKEN
        },
        timeout=30
    )

    if not yanit.ok:
        print(
            "Container durum hatası:"
        )
        print(
            yanit.text
        )
        return None

    veri = yanit.json()

    return (
        veri.get("status_code")
        or veri.get("status")
    )


def container_hazir_olmasini_bekle(
    container_id
):
    print()
    print(
        "Instagram videoyu işliyor..."
    )

    time.sleep(
        ILK_BEKLEME
    )

    baslangic = time.time()

    while True:
        gecen_sure = (
            time.time()
            - baslangic
        )

        if gecen_sure > MAKSIMUM_BEKLEME:
            raise TimeoutError(
                "Instagram container zamanında hazır olmadı."
            )

        durum = (
            container_durumunu_kontrol_et(
                container_id
            )
        )

        print(
            f"Instagram container durumu: {durum}"
        )

        if durum == "FINISHED":
            print(
                "✓ Instagram videosu hazır."
            )
            return

        if durum in (
            "ERROR",
            "EXPIRED"
        ):
            raise RuntimeError(
                "Instagram Reel videosu işlenirken hata oluştu."
            )

        time.sleep(
            KONTROL_ARALIGI
        )


# ============================================================
# INSTAGRAM'DA YAYINLAMA
# ============================================================

def reel_yayinla(video_yolu):
    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    caption = reel_caption_al(
        icerik_dosyasi
    )

    video_url = (
        reel_githuba_gonder(
            video_yolu
        )
    )

    container_id = (
        reel_container_olustur(
            video_url,
            caption
        )
    )

    container_hazir_olmasini_bekle(
        container_id
    )

    print()
    print(
        "Instagram Reels yayınlanıyor..."
    )

    yanit = requests.post(
        f"{API_TEMEL}/{IG_USER_ID}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN
        },
        timeout=60
    )

    if not yanit.ok:
        print(
            "Instagram yayınlama hatası:"
        )
        print(
            yanit.text
        )

        yanit.raise_for_status()

    veri = yanit.json()
    post_id = veri.get("id")

    print()
    print(
        "========================================"
    )
    print(
        "✓ ALMANCA REEL BAŞARIYLA YAYINLANDI"
    )
    print(
        f"Post ID: {post_id}"
    )
    print(
        "========================================"
    )

    return post_id


# ============================================================
# ANA PROGRAM
# ============================================================

def main():
    print(
        "========================================"
    )
    print(
        "Instagram Reels - Azure Almanca Ses"
    )
    print(
        "========================================"
    )

    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    icerik = json_dosyasi_oku(
        icerik_dosyasi
    )

    tarih = icerik.get(
        "tarih"
    )

    if not tarih:
        raise ValueError(
            "JSON dosyasında tarih bulunamadı."
        )

    gorsel_klasoru = (
        gorsel_klasoru_bul(
            tarih
        )
    )

    print(
        f"İçerik dosyası: {icerik_dosyasi}"
    )

    print(
        f"Görsel klasörü: {gorsel_klasoru}"
    )

    ses_yolu = (
        ses_uret(
            icerik,
            tarih
        )
    )

    video_yolu = (
        video_uret(
            gorsel_klasoru,
            icerik_dosyasi,
            ses_yolu
        )
    )

    reel_yayinla(
        video_yolu
    )

    print()
    print(
        "✓ Almanca seslendirmeli Reel başarıyla yayınlandı."
    )


if __name__ == "__main__":
    main()
