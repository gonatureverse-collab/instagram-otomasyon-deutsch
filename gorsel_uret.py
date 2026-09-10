import html
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")

BOYUT = 1080


KAPAK_HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap');

  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }}

  body {{
    width: {boyut}px;
    height: {boyut}px;
    background: radial-gradient(
      circle at 30% 20%,
      #1c1c1c 0%,
      #0a0a0a 70%
    );
    font-family: 'Montserrat', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }}

  .serit {{
    position: absolute;
    left: 0;
    width: 100%;
    height: 24px;
  }}

  .serit.siyah {{
    top: 0;
    background: #111111;
  }}

  .serit.kirmizi {{
    top: 24px;
    background: #DD0000;
  }}

  .serit.sari {{
    top: 48px;
    background: #FFCE00;
  }}

  .icerik {{
    padding: 60px 80px 100px 80px;
  }}

  .emoji-buyuk {{
    font-size: 140px;
    margin-bottom: 30px;
    filter: drop-shadow(0 8px 20px rgba(0, 0, 0, 0.5));
  }}

  .etiket {{
    color: #FFCE00;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 3px;
    margin-bottom: 30px;
  }}

  .baslik {{
    color: #ffffff;
    font-size: 64px;
    font-weight: 900;
    line-height: 1.25;
  }}

  .alt-cizgi {{
    width: 100px;
    height: 8px;
    background: #DD0000;
    margin-top: 40px;
  }}
</style>
</head>

<body>
  <div class="serit siyah"></div>
  <div class="serit kirmizi"></div>
  <div class="serit sari"></div>

  <div class="icerik">
    <div class="emoji-buyuk">{kapak_emoji}</div>

    <div class="etiket">WIE MACHT MAN DAS IN DEUTSCHLAND?</div>

    <div class="baslik">{baslik}</div>
    <div class="alt-cizgi"></div>
  </div>
</body>
</html>
"""


SLAYT_HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap');

  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }}

  body {{
    width: {boyut}px;
    height: {boyut}px;
    background: #ffffff;
    font-family: 'Montserrat', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }}

  .numara {{
    position: absolute;
    top: 60px;
    right: 70px;
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: #DD0000;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    font-size: 40px;
    font-weight: 900;
  }}

  .icerik {{
    padding: 80px 90px;
  }}

  .emoji-slayt {{
    font-size: 100px;
    margin-bottom: 40px;
  }}

  .metin {{
    color: #111111;
    font-size: 52px;
    font-weight: 700;
    line-height: 1.4;
  }}

  .alt-serit {{
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 30px;
    display: flex;
  }}

  .alt-serit div {{
    flex: 1;
  }}

  .alt-serit .s1 {{
    background: #111111;
  }}

  .alt-serit .s2 {{
    background: #DD0000;
  }}

  .alt-serit .s3 {{
    background: #FFCE00;
  }}
</style>
</head>

<body>
  <div class="numara">{numara}</div>

  <div class="icerik">
    <div class="emoji-slayt">{emoji}</div>
    <div class="metin">{metin}</div>
  </div>

  <div class="alt-serit">
    <div class="s1"></div>
    <div class="s2"></div>
    <div class="s3"></div>
  </div>
</body>
</html>
"""


def son_icerik_dosyasi():
    dosyalar = sorted(CIKTI_KLASOR.glob("icerik_*.json"))

    if not dosyalar:
        raise FileNotFoundError(
            "cikti/ klasöründe içerik dosyası bulunamadı. "
            "Önce icerik_uret.py çalıştırılmalı."
        )

    return dosyalar[-1]


def fontlari_bekle(sayfa):
    sayfa.evaluate(
        """
        async () => {
            if (document.fonts) {
                await document.fonts.ready;
            }
        }
        """
    )


def gorseller_uret(icerik_dosyasi: Path):
    icerik = json.loads(
        icerik_dosyasi.read_text(encoding="utf-8")
    )

    tarih = icerik["tarih"]

    hedef_klasor = GORSEL_KLASOR / tarih
    hedef_klasor.mkdir(parents=True, exist_ok=True)

    baslik = html.escape(
        str(
            icerik.get(
                "baslik",
                "Praktische Tipps für Deutschland"
            )
        )
    )

    kapak_emoji = html.escape(
        str(icerik.get("kapak_emoji", "🇩🇪"))
    )

    slaytlar = icerik.get("slaytlar", [])
    emojiler = icerik.get("emojiler", [])

    with sync_playwright() as p:
        tarayici = p.chromium.launch()

        sayfa = tarayici.new_page(
            viewport={
                "width": BOYUT,
                "height": BOYUT
            },
            device_scale_factor=1
        )

        # Kapak görseli
        kapak_html = KAPAK_HTML.format(
            boyut=BOYUT,
            baslik=baslik,
            kapak_emoji=kapak_emoji
        )

        sayfa.set_content(kapak_html)
        fontlari_bekle(sayfa)

        kapak_yolu = hedef_klasor / "01_kapak.png"

        sayfa.screenshot(
            path=str(kapak_yolu),
            full_page=False
        )

        # İçerik slaytları
        for i, slayt_metni in enumerate(slaytlar, start=1):
            if i - 1 < len(emojiler):
                emoji = emojiler[i - 1]
            else:
                emoji = "✅"

            slayt_html = SLAYT_HTML.format(
                boyut=BOYUT,
                metin=html.escape(str(slayt_metni)),
                numara=i,
                emoji=html.escape(str(emoji))
            )

            sayfa.set_content(slayt_html)
            fontlari_bekle(sayfa)

            slayt_yolu = hedef_klasor / f"{i + 1:02d}_slayt.png"

            sayfa.screenshot(
                path=str(slayt_yolu),
                full_page=False
            )

        tarayici.close()

    toplam_gorsel = len(slaytlar) + 1

    print(
        f"{toplam_gorsel} görsel üretildi: {hedef_klasor}"
    )

    return hedef_klasor


def main():
    icerik_dosyasi = son_icerik_dosyasi()

    print(f"Kullanılan içerik: {icerik_dosyasi}")

    gorseller_uret(icerik_dosyasi)


if __name__ == "__main__":
    main()
