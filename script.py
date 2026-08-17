import db_operation
import scraper
import telebot

bot = telebot.TeleBot("8614879384:AAFk5rv64rI_g6dgHU6zWV3S75EN2PJsJz0")

def calistir():
    print(" RSS Botu çalıştırılıyor \n")

    kaynaklar = db_operation.get_links()

    if not kaynaklar:
        print(" Veritabanında kayıtlı RSS adresi bulunamadı.")
        print(" İpucu: Önce veritabanına bir RSS adresi eklemelisiniz.")
        return

    print(f" Veritabanından {len(kaynaklar)} adet RSS kaynağı alındı. Tarama başlıyor")

    haberler = scraper.rss_tara(kaynaklar)

    if haberler:
        db_operation.haberleri_kaydet(haberler)
        print(f"\n İşlem tamamlandı Toplam {len(haberler)} haber veritabanına işlendi.")
    else:
        print("\n Taranan kaynaklarda yeni bir haber bulunamadı.")


@bot.message_handler(commands=['haber'])
def haberleri_getir(message):
    bot.reply_to(message, " Son 24 saatin haberleri toplanıyor..")
    calistir()

    bot.send_message(message.chat.id, " Tarama tamamlandı")

if __name__ == "__main__":
    print(" Telegram'dan mesaj bekleniyor..")
    bot.infinity_polling()
