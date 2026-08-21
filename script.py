import os
import telebot #Telegram Bot API'si ile kodumuz arasında iletişim köprüsü
from dotenv import load_dotenv #.env dosyasındaki gizli değişkenleri python'ın okuyabileceği formata getirme
import scraper
import db_operation
from telebot.types import BotCommand, ForceReply

load_dotenv()#env dosyasını okuyarak içindeki gizli şifreleri aktif hale getirir

token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(token)
#bot menü kısmı
bot.set_my_commands([
    BotCommand("haber", "Son haberleri getir"),
    BotCommand("kaynaklar", "Kayıtlı kaynakları listele"),
    BotCommand("ekle", "Yeni kaynak ekle"),
    BotCommand("sil", "Kayıtlı kaynak sil"),
    BotCommand("start", "Başlangıç mesajı")
])

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
    bot.send_message(message.chat.id, f"Kayıtlı Kaynaklar:\n{siteler}", disable_web_page_preview=True)


#kaynak ekleme
@bot.message_handler(commands=['ekle'])
def kaynak_ekle_sor(message):
    mesaj=bot.reply_to(message,"Eklemek istediğiniz RSS linkini yazınız.",reply_markup=ForceReply())
    bot.register_next_step_handler(mesaj, kaynak_ekle_kaydet)#sonraki adımı kaydetmek için

def kaynak_ekle_kaydet(message):
    yeni_url=message.text.strip()#Metnin başındaki ve sonundaki görünmeyen karakterlerini kırpar.

    #Kullanıcı link yerine başka bir komut girdiyse işlemi iptal et
    if yeni_url.startswith('/'):
        bot.process_new_messages([message])
        return

    #Gelen metnin geçerli bir RSS linki olup olmadığını kontrol et
    if not (yeni_url.startswith("http://") or yeni_url.startswith("https://")):
        bot.reply_to(message, "Geçersiz link.Gönderdiğiniz metin 'http://' veya 'https://' ile başlamalıdır.")
        return

    mevcut_kaynaklar = db_operation.get_links()
    if yeni_url in mevcut_kaynaklar:
        bot.reply_to(message, "Bu kaynak listede mevcut.")
    else:
        db_operation.add_link(yeni_url)
        bot.reply_to(message, f" Yeni kaynak eklendi:\n{yeni_url}")


#kaynak silme
@bot.message_handler(commands=['sil'])
def kaynak_sil_sor(message):
    mesaj = bot.reply_to(message,"Silmek istediğiniz RSS linkini yazınız.",reply_markup=ForceReply())
    bot.register_next_step_handler(mesaj, kaynak_sil_tamamla)


def kaynak_sil_tamamla(message):
    silinecek_url = message.text.strip()

    #Kullanıcı link yerine başka bir komut girdiyse, o komutu direkt çalıştır
    if silinecek_url.startswith('/'):
        bot.process_new_messages([message])
        return

    if not (silinecek_url.startswith("http://") or silinecek_url.startswith("https://")):
        bot.reply_to(message,
                     " Geçersiz link formatı.'http://' veya 'https://' ile başlayan geçerli bir RSS linki giriniz.")
        return

    mevcut_kaynaklar = db_operation.get_links()

    if silinecek_url in mevcut_kaynaklar:
        db_operation.delete_link(silinecek_url)
        bot.reply_to(message, f"Kaynak silindi:\n{silinecek_url}")
    else:
        bot.reply_to(message, "Bu kaynak listenizde zaten bulunmuyor.")

#haber komutu
@bot.message_handler(commands=['haber'])
def haberleri_getir(message):

    bot.send_message(message.chat.id, "Son haberler taranıyor..")
    calistir()

    son_haberler = db_operation.son_haberleri_getir(limit=30)

    if son_haberler:
        bot.send_message(message.chat.id, f"{len(son_haberler)} haber bulundu.")
        for index, (baslik, link) in enumerate(son_haberler, start=1):
            bot.send_message(message.chat.id, f"[{index}/{len(son_haberler)}] {baslik}\n{link}",disable_web_page_preview=True)
    else:
        bot.send_message(message.chat.id, "Henüz veritabanında haber bulunmuyor.")

    bot.send_message(message.chat.id, "Tarama tamamlandı")

if __name__ == "__main__":
    print(" Telegram'dan mesaj bekleniyor..")
    bot.infinity_polling()#sunucularını kesintisiz ve sonsuz bir döngüde dinlemesini sağlıyor