import os
import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
def get_link():

    load_dotenv()

    baglanti = psycopg2.connect(
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port="5432",
    )
    cursor = baglanti.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS kaynaklar (id SERIAL PRIMARY KEY, url TEXT NOT NULL);")
    cursor.execute("SELECT url FROM kaynaklar;")

    url_list = [satir[0] for satir in cursor.fetchall()]
    cursor.close()
    baglanti.close()
    return url_list
print(" Linkler veritabanından çekildi \n")
url_list = get_link()
for url in url_list:
    print(f"=== {url} taranıyor ===")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, features="xml")
    makale_listesi = soup.find_all("item")

    for makale in makale_listesi:
        baslik = makale.title.text if makale.title else "Başlık Yok"
        link = makale.link.text if makale.link else "Link Yok"

        print("Başlık:", baslik)
        print("Link:", link)
        print("-" * 15)
