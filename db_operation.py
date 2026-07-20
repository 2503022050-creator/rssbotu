import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def baglanti_get():
    return psycopg2.connect(
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port="5432"
    )


def get_links():
    baglanti = baglanti_get()
    cursor = baglanti.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS kaynaklar (id SERIAL PRIMARY KEY, url TEXT NOT NULL);")
    cursor.execute("SELECT url FROM kaynaklar;")

    url_list = [satir[0] for satir in cursor.fetchall()]

    cursor.close()
    baglanti.close()

    return url_list


def add_link(url):
    """Kullanıcının gönderdiği yeni bir RSS linkini veritabanına kaydeder."""
    baglanti = baglanti_get()
    cursor = baglanti.cursor()

    # güvenli SQL ekleme sorgusu
    cursor.execute("INSERT INTO kaynaklar (url) VALUES (%s);", (url,))
    baglanti.commit()

    cursor.close()
    baglanti.close()


def delete_link(url):
    """Belirtilen RSS linkini veritabanından siler."""
    baglanti = baglanti_get()
    cursor = baglanti.cursor()

    # güvenli SQL silme sorgusu
    cursor.execute("DELETE FROM kaynaklar WHERE url = %s;", (url,))
    baglanti.commit()

    cursor.close()
    baglanti.close()