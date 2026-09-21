import os
import psycopg2
from telegram_notifier import telegrama_haber_gonder
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


def add_link(url, added_by):
    baglanti = baglanti_get()
    cursor = baglanti.cursor()

    cursor.execute("""
        INSERT INTO kaynaklar (url, added_by)
        VALUES (%s, %s);
    """, (url, added_by))

    baglanti.commit()
    cursor.close()
    baglanti.close()



def delete_link(url):
    baglanti = baglanti_get()
    cursor = baglanti.cursor()

    # güvenli SQL silme sorgusu
    cursor.execute("DELETE FROM kaynaklar WHERE url = %s;", (url,))
    baglanti.commit()

    cursor.close()
    baglanti.close()

def haberleri_kaydet(haberler, gonderilecek_kisi=None, bildirim=True):
    baglanti = baglanti_get()
    cursor = baglanti.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS haberler (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        link TEXT NOT NULL UNIQUE,
        pub_date TEXT,
        kaynak_url TEXT,
        ozet TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           
    );
    """)

    eklenen_sayisi = 0
    for haber in haberler:
        cursor.execute("""
            INSERT INTO haberler (title, link, pub_date,kaynak_url,ozet)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (link) DO NOTHING;
        """, (haber["title"], haber["link"], haber.get("pub_date"), haber.get("kaynak_url"), haber.get("ozet")))

        # Sadece bildirim=True ise ve yeni haber eklendiyse anlık mesaj atar
        if cursor.rowcount > 0:
            eklenen_sayisi += 1
            if bildirim:
                telegrama_haber_gonder(haber["title"], haber["link"], haber.get("ozet"), gonderilecek_kisi)

    baglanti.commit()
    cursor.close()
    baglanti.close()
    return eklenen_sayisi


def son_haberleri_getir(limit=80):
    baglanti = baglanti_get()
    cursor = baglanti.cursor()

    # AND added_at >= NOW() - INTERVAL '24 hours' kuralını ekledik.
    # Bu kural sadece son 24 saatte veritabanına girenleri filtreler.
    cursor.execute("""
        SELECT id, title, link, kaynak_url, ozet 
        FROM haberler 
        WHERE kaynak_url IN (SELECT url FROM kaynaklar)
          AND added_at >= NOW() - INTERVAL '24 hours'
        ORDER BY id DESC 
        LIMIT %s;
    """, (limit,))

    haberler = cursor.fetchall()
    cursor.close()
    baglanti.close()
    return haberler


def favori_ekle(kullanici_id, haber_id):
    baglanti = baglanti_get()
    cursor = baglanti.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favoriler (
        id SERIAL PRIMARY KEY,
        kullanici_id BIGINT NOT NULL,
        haber_id INTEGER NOT NULL REFERENCES haberler(id),
        eklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(kullanici_id, haber_id)
    );
    """)

    cursor.execute("""
        INSERT INTO favoriler (kullanici_id, haber_id)
        VALUES (%s, %s)
        ON CONFLICT (kullanici_id, haber_id) DO NOTHING;
    """, (kullanici_id, haber_id))

    x = cursor.rowcount > 0
    baglanti.commit()
    cursor.close()
    baglanti.close()
    return x


def favorileri_getir(kullanici_id):
    baglanti = baglanti_get()
    cursor = baglanti.cursor()

    cursor.execute("""
        SELECT h.title, h.link 
        FROM favoriler f
        JOIN haberler h ON f.haber_id = h.id
        WHERE f.kullanici_id = %s
        ORDER BY f.eklenme_tarihi DESC LIMIT 30;
    """, (kullanici_id,))

    favoriler = cursor.fetchall()
    cursor.close()
    baglanti.close()
    return favoriler