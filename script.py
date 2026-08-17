import os
import telebot
from dotenv import load_dotenv
import scraper
import db_operation

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(token)


def calistir(isteyen_kisi_id=None):
    kaynaklar = db_operation.get_links()

    if not kaynaklar:
        print("Veritabanında kayıtlı RSS adresi bulunamadı.")
        print("Veritabanına bir RSS adresi eklemelisiniz.")
        return

    print(f"Veritabanından {len(kaynaklar)} adet RSS kaynağı alındı. Tarama başlıyor")
    haberler = scraper.rss_tara(kaynaklar)

    if haberler:
        #Komutu yazan kişinin ID'sini veritabanı fonksiyonuna iletiyor
        db_operation.haberleri_kaydet(haberler, isteyen_kisi_id)
        print(f"\n İşlem tamamlandı Toplam {len(haberler)} haber veritabanına işlendi.")
    else:
        print("\n Taranan kaynaklarda yeni bir haber bulunamadı.")


# /start komutu,Karşılama Mesajı
@bot.message_handler(commands=['start'])
def karsilama(message):
    bot.reply_to(message,
                 "Son 24 saatteki güncel haberleri okumak için /haber yazmanız yeterlidir.")


# /haber komutu
@bot.message_handler(commands=['haber'])
def haberleri_getir(message):
    bot.reply_to(message, "Son haberler taranıyor..")

    calistir()

    son_haberler = db_operation.son_haberleri_getir(limit=20)

    if son_haberler:
        for baslik, link in son_haberler:
            bot.send_message(message.chat.id, f"{baslik}\n{link}")
    else:
        bot.send_message(message.chat.id, "Henüz veritabanında haber bulunmuyor.")

    bot.send_message(message.chat.id, " Tarama tamamlandı")

if __name__ == "__main__":
    print(" Telegram'dan mesaj bekleniyor..")
    bot.infinity_polling()