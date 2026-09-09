import os
import subprocess
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# AYARLAR
# ============================================================

load_dotenv()


def ortam_degiskeni_al(anahtar):
    deger = os.environ.get(anahtar)

    if not deger or not deger.strip():
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


# Instagram Graph API
API_SURUM = "v21.0"
API_TEMEL = (
    f"https://graph.facebook.com/{API_SURUM}"
)


# Story klasörü
STORY_KLASOR = Path("stories")

# Bekleme ayarları
ILK_BEKLEME = 10
KONTROL_ARALIGI = 5
MAKSIMUM_DENEME = 60


# ============================================================
# EN SON STORY DOSYASINI BUL
# ============================================================

def son_story_dosyasi():
    story_dosyalari = sorted(
        STORY_KLASOR.glob("*/story.png")
    )

    if not story_dosyalari:
        raise FileNotFoundError(
            "stories/ klasöründe story.png bulunamadı. "
            "Önce story_uret.py çalıştırın."
        )

    story_yolu = story_dosyalari[-1]

    if not story_yolu.exists():
        raise FileNotFoundError(
            f"Story dosyası bulunamadı: {story_yolu}"
        )

    if story_yolu.stat().st_size == 0:
        raise RuntimeError(
            f"Story dosyası boş: {story_yolu}"
        )

    return story_yolu


# ============================================================
# STORY'Yİ GITHUB'A GÖNDER
# ============================================================

def story_githuba_gonder(story_yolu):
    print("\nStory GitHub'a gönderiliyor...")

    try:
        subprocess.run(
            ["git", "fetch", "origin"],
            check=True
        )

        subprocess.run(
            [
                "git",
                "add",
                str(story_yolu)
            ],
            check=True
        )

        commit = subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "story: otomatik story yayini"
            ],
            capture_output=True,
            text=True
        )

        commit_ciktisi = (
            commit.stdout + commit.stderr
        ).lower()

        if commit.returncode == 0:
            print("✓ Story commit edildi.")

        elif "nothing to commit" in commit_ciktisi:
            print(
                "Yeni commit oluşturulmadı. "
                "Dosya zaten commit edilmiş olabilir."
            )

        else:
            print(commit.stdout)
            print(commit.stderr)
            raise RuntimeError(
                "Story commit işlemi başarısız oldu."
            )

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
            "✓ Story GitHub'a başarıyla gönderildi."
        )

    except subprocess.CalledProcessError as hata:
        raise RuntimeError(
            f"GitHub işlemi başarısız oldu: {hata}"
        ) from hata

    relative_path = story_yolu.as_posix()

    raw_url = (
        "https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"{GITHUB_BRANCH}/"
        f"{relative_path}"
    )

    print(f"\nStory Raw URL:\n{raw_url}")

    # Raw GitHub dosyasının erişilebilir olması için bekle
    time.sleep(15)

    return raw_url


# ============================================================
# STORY CONTAINER OLUŞTUR
# ============================================================

def story_container_olustur(image_url):
    print(
        "\nInstagram Story container oluşturuluyor..."
    )

    yanit = requests.post(
        f"{API_TEMEL}/{IG_USER_ID}/media",
        data={
            "media_type": "STORIES",
            "image_url": image_url,
            "access_token": ACCESS_TOKEN
        },
        timeout=60
    )

    if not yanit.ok:
        print("HATA DETAYI:")
        print(yanit.text)
        yanit.raise_for_status()

    veri = yanit.json()
    container_id = veri.get("id")

    if not container_id:
        raise RuntimeError(
            f"Instagram container ID döndürmedi: {veri}"
        )

    print(
        "✓ Story container oluşturuldu: "
        f"{container_id}"
    )

    return container_id


# ============================================================
# CONTAINER DURUMUNU KONTROL ET
# ============================================================

def container_durumunu_kontrol_et(container_id):
    print(
        "\nStory'nin hazırlanması bekleniyor..."
    )

    time.sleep(ILK_BEKLEME)

    for deneme in range(
        1,
        MAKSIMUM_DENEME + 1
    ):
        yanit = requests.get(
            f"{API_TEMEL}/{container_id}",
            params={
                "fields": "status_code,status",
                "access_token": ACCESS_TOKEN
            },
            timeout=60
        )

        if not yanit.ok:
            print("STATUS HATASI:")
            print(yanit.text)
            yanit.raise_for_status()

        veri = yanit.json()

        status_code = veri.get(
            "status_code"
        )

        status = veri.get(
            "status"
        )

        mevcut_durum = (
            status_code or status
        )

        print(
            f"Deneme {deneme}/{MAKSIMUM_DENEME} "
            f"→ status_code={status_code}, "
            f"status={status}"
        )

        if mevcut_durum == "FINISHED":
            print(
                "✓ Story yayınlanmaya hazır."
            )
            return True

        if mevcut_durum in (
            "ERROR",
            "EXPIRED"
        ):
            raise RuntimeError(
                "Instagram Story container hatası: "
                f"{veri}"
            )

        time.sleep(KONTROL_ARALIGI)

    raise TimeoutError(
        "Story container zamanında hazır olmadı."
    )


# ============================================================
# STORY'Yİ YAYINLA
# ============================================================

def story_yayinla(container_id):
    print(
        "\nInstagram Story yayınlanıyor..."
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
        print("YAYINLAMA HATASI:")
        print(yanit.text)
        yanit.raise_for_status()

    veri = yanit.json()
    post_id = veri.get("id")

    print(
        "\n========================================"
    )
    print(
        "✓ INSTAGRAM STORY YAYINLANDI!"
    )
    print(
        f"Post ID: {post_id}"
    )
    print(
        "========================================"
    )

    return veri


# ============================================================
# ANA İŞLEM
# ============================================================

def main():
    print(
        "========================================"
    )
    print(
        "INSTAGRAM STORY YAYINLAMA"
    )
    print(
        "========================================"
    )

    story_yolu = son_story_dosyasi()

    print(
        f"\nStory dosyası:\n{story_yolu}"
    )

    image_url = story_githuba_gonder(
        story_yolu
    )

    container_id = story_container_olustur(
        image_url
    )

    container_durumunu_kontrol_et(
        container_id
    )

    story_yayinla(
        container_id
    )

    print(
        "\n✓ Story işlemi başarıyla tamamlandı."
    )


if __name__ == "__main__":
    main()
