import os
import subprocess
import sys
from pathlib import Path

# Yerel bilgisayarda .env varsa yükler; GitHub Actions secret'larını etkilemez
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


SCRIPTLER = [
    ("1. Yeni içerik üret", "icerik_uret.py"),
    ("2. Carousel görsellerini üret", "gorsel_uret.py"),
    ("3. Carousel görsellerini GitHub'a gönder", "github_gorsel_yukle.py"),
    ("4. Reel üret ve Instagram'a yayınla", "reel_uret.py"),
    ("5. Story görselini üret", "story_uret.py"),
    ("6. Story'yi Instagram'a yayınla", "story_yayinla.py"),
    ("7. Carousel'i Instagram'a yayınla", "carousel_yayinla.py"),
]


def gerekli_dosyalar_kontrol_et():
    eksik_dosyalar = [
        dosya for _, dosya in SCRIPTLER
        if not Path(dosya).is_file()
    ]

    if eksik_dosyalar:
        raise FileNotFoundError(
            "Eksik Python dosyaları:\n- "
            + "\n- ".join(eksik_dosyalar)
        )


def azure_degiskenlerini_kontrol_et():
    eksik = []

    if not os.environ.get("AZURE_SPEECH_KEY"):
        eksik.append("AZURE_SPEECH_KEY")

    if not os.environ.get("AZURE_SPEECH_REGION"):
        eksik.append("AZURE_SPEECH_REGION")

    if eksik:
        raise EnvironmentError(
            "Azure değişkenleri eksik: "
            + ", ".join(eksik)
            + ". GitHub Actions workflow env bölümünü kontrol edin."
        )


def script_calistir(aciklama, script_adi):
    print()
    print("=" * 60)
    print(f"ÇALIŞTIRILIYOR: {aciklama}")
    print(f"DOSYA: {script_adi}")
    print("=" * 60)
    print()

    sonuc = subprocess.run(
        [sys.executable, "-u", script_adi],
        check=False
    )

    if sonuc.returncode != 0:
        print()
        print("=" * 60)
        print(f"HATA: {script_adi} başarısız oldu!")
        print(f"Çıkış kodu: {sonuc.returncode}")
        print("=" * 60)
        print()

        sys.exit(sonuc.returncode)

    print()
    print(f"✓ {script_adi} başarıyla tamamlandı.")


def main():
    print()
    print("=" * 60)
    print("ALMANYA'DA NASIL YAPILIR?")
    print("GÜNLÜK INSTAGRAM OTOMASYONU")
    print("=" * 60)
    print()

    gerekli_dosyalar_kontrol_et()
    azure_degiskenlerini_kontrol_et()

    for aciklama, script_adi in SCRIPTLER:
        script_calistir(aciklama, script_adi)

    print()
    print("=" * 60)
    print("✓✓✓ TÜM INSTAGRAM İÇERİKLERİ BAŞARIYLA YAYINLANDI ✓✓✓")
    print("=" * 60)
    print()
    print("✓ 1 Carousel")
    print("✓ 1 Reel")
    print("✓ 1 Story")
    print()
    print("Günlük otomasyon tamamlandı.")
    print()


if __name__ == "__main__":
    main()
