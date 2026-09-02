import time
import requests
from bs4 import BeautifulSoup
from email.utils import parsedate_tz, mktime_tz


def haberin_icine_gir(link):
    """
    RSS'te içeriği bulunmayan haberlerin web sitesine girip
    <p> etiketleri arasındaki gerçek metni toplayan yardımcı fonksiyon.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        }
        cevap = requests.get(link, headers=headers, timeout=3)
        if cevap.status_code == 200:
            soup = BeautifulSoup(cevap.text, "html.parser")
            paragraflar = soup.find_all("p")

            temiz_paragraflar = []
            for p in paragraflar:
                if p.text:
                    temiz_paragraflar.append(p.text.strip())

            return " ".join(temiz_paragraflar)
    except Exception:
        pass
    return ""


def rss_tara(url_list):
    """
    RSS adreslerini gezerek yeni haberleri toplayan,
    özetlerini Gemini ile oluşturan ana fonksiyon.
    """
    haberler = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
    }

    for url in url_list:
        try:
            cevap = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(cevap.content, "xml")
            haber_kutulari = soup.find_all("item")

            for haber in haber_kutulari:
                title = haber.title.text if haber.title else "Başlık yok"
                link = haber.link.text if haber.link else "Link yok"

                # 1. Filtre: 24 Saatlik Zaman Kontrolü
                pub_date = haber.find("pubDate") or haber.find("published") or haber.find("dc:date")
                if pub_date:
                    parsed_date = parsedate_tz(pub_date.text)
                    if parsed_date:
                        item_ts = mktime_tz(parsed_date)
                        now_ts = time.time()
                        if (now_ts - item_ts) > 86400:
                            continue  # 24 saatten eski haberleri atla

                # Temiz veriyi listeye ekleme
                haberler.append({
                    "link": link,
                    "title": title,
                    "kaynak_url": url,
                    "pub_date": pub_date.text if pub_date else None,
                })

        except Exception as e:
            print(f"Hata {url} adresinden veri çekilemedi: {e}")

    return haberler