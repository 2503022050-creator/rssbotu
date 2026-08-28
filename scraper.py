import time
from email.utils import parsedate_tz, mktime_tz #tarih/saat hesabı
import requests
from bs4 import BeautifulSoup


def rss_tara(url_list):
    haberler = []

    for url in url_list:
        try:
            cevap = requests.get(url, timeout=5)
            xml_icerik = BeautifulSoup(cevap.text, features="xml")
            haber_kutulari = xml_icerik.find_all("item")

            for haber in haber_kutulari:
                title = haber.title.text if haber.title else "Başlık yok"
                link = haber.link.text if haber.link else "Link yok"
                #24 saat filtresi
                #farklı RSS formatlarını destekleyen esnek arama:
                pub_date = haber.find("pubDate") or haber.find("published") or haber.find("dc:date")
                if pub_date:
                    parsed_date = parsedate_tz(pub_date.text)
                    if parsed_date:
                        item_ts = mktime_tz(parsed_date)
                        now_ts = time.time()

                        if (now_ts - item_ts) > 86400:
                            continue

                haberler.append({
                    "link": link,
                    "title": title,
                    "kaynak_url": url,
                    "pub_date": pub_date.text if pub_date else None#!!!!!
                })
        except Exception as e:
            print(f"Hata {url} adresinden veri çekilemedi: {e}")

    return haberler