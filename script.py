import os
import telebot #Telegram Bot API'si ile kodumuz arasında iletişim köprüsü
from dotenv import load_dotenv #.env dosyasındaki gizli değişkenleri python'ın okuyabileceği formata getirme
import scraper
import db_operation

load_dotenv()#env dosyasını okuyarak içindeki gizli şifreleri aktif hale getirir

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


#start komutu,Karşılama Mesajı
@bot.message_handler(commands=['start'])
def karsilama(message):
    rehber_mesaji = (
        "Kullanabileceğiniz komutlar:\n\n"
        "`/haber` - Son güncel haberleri getirir\n"
        "`/kaynaklar` - Kayıtlı RSS sitelerini gösterir\n"
        "`/ekle https://site.com/rss` - Yeni kaynak ekler\n"
        "`/sil https://site.com/rss` - Kaynak siler"
    )
    bot.reply_to(message, rehber_mesaji)


#kaynakları getirme
@bot.message_handler(commands=['kaynaklar'])
def kaynaklar_getir(message):
    siteler = db_operation.get_links()
    bot.send_message(message.chat.id, f"Kayıtlı Kaynaklar:\n{siteler}")


#kaynak ekleme
@bot.message_handler(commands=['ekle'])
def kaynak_ekle(message):
    parcalar = message.text.split()

    if len(parcalar) > 1:
        yeni_url = parcalar[1]
        mevcut_kaynaklar=db_operation.get_links()

        if yeni_url in mevcut_kaynaklar:
            bot.reply_to(message, "Bu kaynak lisetede mevcut.")
        else:
            db_operation.add_link(yeni_url)
            bot.reply_to(message, f"Yeni kaynak eklendi:\n{yeni_url}")
    else:
        bot.reply_to(message, "Lütfen bir link belirtin. ")


#kaynak silme
@bot.message_handler(commands=['sil'])
def kaynak_sil(message):
    parcalar = message.text.split()

    if len(parcalar) > 1:
        silinecek_url = parcalar[1]
        mevcut_kaynaklar = db_operation.get_links()

        if silinecek_url in mevcut_kaynaklar:
            db_operation.delete_link(silinecek_url)
            bot.reply_to(message, f"Kaynak silindi:\n{silinecek_url}")
        else:
            bot.reply_to(message, " Bu kaynak listenizde zaten bulunmuyor.")
    else:
        bot.reply_to(message, "Lütfen silinecek bir link belirtin.")

#haber komutu
@bot.message_handler(commands=['haber'])
def haberleri_getir(message):

    bot.send_message(message.chat.id, "Son haberler taranıyor..")
    calistir()

    son_haberler = db_operation.son_haberleri_getir(limit=20)

    if son_haberler:
        for baslik, link in son_haberler:
            bot.send_message(message.chat.id, f"{baslik}\n{link}")
    else:
        bot.send_message(message.chat.id, "Henüz veritabanında haber bulunmuyor.")

    bot.send_message(message.chat.id, "Tarama tamamlandı")

if __name__ == "__main__":
    print(" Telegram'dan mesaj bekleniyor..")
    bot.infinity_polling()#sunucularını kesintisiz ve sonsuz bir döngüde dinlemesini sağlıyor