import html
import os
import re  #sadece http:// veya https:// ile başlayan haber linki alır
import time
import telebot #Telegram Bot API'si ile kodumuz arasında iletişim köprüsü
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv #.env dosyasındaki gizli değişkenleri python'ın okuyabileceği formata getirme
import scraper
import db_operation
from ai_helper import ozetle
from telebot import types
from telebot.types import BotCommand, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()#env dosyasını okuyarak içindeki gizli şifreleri aktif hale getirir

token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(token)
#bot menü kısmı
bot.set_my_commands([
    BotCommand("haber", "Son haberleri getir"),
    BotCommand("ozet", "Yanıtlanan haberi özetle"),
    BotCommand("kaynaklar", "Kayıtlı kaynakları listele"),
    BotCommand("favoriler", "Daha sonra oku listeniz"),
    BotCommand("ekle", "Yeni kaynak ekle"),
    BotCommand("sil", "Kayıtlı kaynak sil"),
    BotCommand("start", "Başlangıç mesajı"),
])

def calistir(isteyen_kisi_id=None, bildirim=True):
    kaynaklar = db_operation.get_links()

    if not kaynaklar:
        print("Veritabanında kayıtlı RSS adresi bulunamadı.")
        return []

    print(f"Veritabanından {len(kaynaklar)} adet RSS kaynağı alındı. Tarama başlıyor")
    haberler = scraper.rss_tara(kaynaklar)

    if haberler:
        # Tekrarlanan linkleri tekilleştir
        gorulen_linkler = set()
        benzersiz_haberler = []
        for h in haberler:
            if h["link"] not in gorulen_linkler:
                gorulen_linkler.add(h["link"])
                benzersiz_haberler.append(h)
        haberler = benzersiz_haberler

        # bildirim durumunu db_operation'a aktarıyoruz
        yeni_sayisi = db_operation.haberleri_kaydet(haberler, isteyen_kisi_id, bildirim=bildirim)
        print(f"\n İşlem tamamlandı: Toplam {len(haberler)} güncel haber tarandı ({yeni_sayisi} yeni haber veritabanına işlendi).")
    else:
        print("\n Taranan kaynaklarda yeni bir haber bulunamadı.")

    return haberler or []

#start komutu,Karşılama Mesajı
@bot.message_handler(commands=['start'])
def karsilama(message):
    rehber_mesaji = (
        "Kullanabileceğiniz komutlar:\n\n"
        "`/haber` - Son güncel haberleri getirir\n"
        "`/kaynaklar` - Kayıtlı RSS sitelerini gösterir\n"
        "`/ozet` - Yanıtlanan haberi özetler\n"
        "`/ekle https://site.com/rss` - Yeni kaynak ekler\n"
        "`/sil https://site.com/rss` - Kaynak siler"
    )
    bot.reply_to(message, rehber_mesaji)


#kaynakları getirme
@bot.message_handler(commands=['kaynaklar'])
def kaynaklar_getir(message):
    siteler = db_operation.get_links()

    if not siteler: #liste boşsa hata olmaması için
        bot.send_message(message.chat.id, "Kayıtlı RSS kaynağı bulunamadı.")
        return

    #linkleri alt alta ve numaralandırarak sıralama
    liste_metni = "\n".join([f"{index}. {url}" for index, url in enumerate(siteler, start=1)])
    mesaj_metni = f"Kayıtlı Kaynaklar ({len(siteler)} Adet):\n\n{liste_metni}"

    bot.send_message(message.chat.id, mesaj_metni, disable_web_page_preview=True)


#kaynak ekleme
@bot.message_handler(commands=['ekle'])
def kaynak_ekle_sor(message):
    mesaj=bot.reply_to(message,"Eklemek istediğiniz RSS linkini yazınız.",reply_markup=ForceReply())
    bot.register_next_step_handler(mesaj, kaynak_ekle_kaydet)#sonraki adımı kaydetmek için


def kaynak_ekle_kaydet(message):
    yeni_url = message.text.strip()  # Metnin başındaki ve sonundaki görünmeyen karakterlerini kırpar.

    #kullanıcı link yerine başka bir komut girdiyse işlemi iptal et
    if yeni_url.startswith('/'):
        bot.process_new_messages([message])
        return

    #gelen metnin geçerli bir RSS linki olup olmadığını kontrol et
    if not (yeni_url.startswith("http://") or yeni_url.startswith("https://")):
        bot.reply_to(message, "Geçersiz link. Gönderdiğiniz metin 'http://' veya 'https://' ile başlamalıdır.")
        return

    mevcut_kaynaklar = db_operation.get_links()
    if yeni_url in mevcut_kaynaklar:
        bot.reply_to(message, "Bu kaynak listede mevcut.")
    else:
        #kullanıcı adını Telegram mesajından yakalıyoruz
        ekleyen_kisi = message.from_user.username or message.from_user.first_name

        #veritabanına hem linki hem de ekleyen kişiyi gönderiyoruz
        db_operation.add_link(yeni_url, ekleyen_kisi)

        bot.reply_to(message, f"Yeni kaynak eklendi:\n{yeni_url}\n(Ekleyen: {ekleyen_kisi})")

#kaynak silme
@bot.message_handler(commands=['sil'])
def kaynak_sil_sor(message):
    mesaj = bot.reply_to(message,"Silmek istediğiniz RSS linkini yazınız.",reply_markup=ForceReply())
    bot.register_next_step_handler(mesaj, kaynak_sil_tamamla)


def kaynak_sil_tamamla(message):
    silinecek_url = message.text.strip()

    #Kullanıcı link yerine başka bir komut girdiyse, o komutu direkt çalıştır
    if silinecek_url.startswith('/'):
        bot.process_new_messages([message]) #ardarda komut verdiğimizde sıkıntı çıkmasın diye
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
    # Kullanıcıya bekleme mesajı gönderiyoruz
    bot.send_message(message.chat.id, "Son haberler taranıyor..")

    # 1. Kaynakları tara ve yeni haberleri veritabanına kaydet (bildirim atmadan)
    calistir(bildirim=False)

    # 2. Butonlara ID ekleyebilmek için son 20 haberi her halükarda veritabanından çekiyoruz
    son_haberler = db_operation.son_haberleri_getir(limit=100)

    # Eğer veritabanı tamamen boşsa uyarı ver ve işlemi bitir
    if not son_haberler:
        bot.send_message(message.chat.id, "Henüz haber bulunmuyor.")
        return

    toplam_haber = len(son_haberler)
    bot.send_message(message.chat.id, f"{toplam_haber} haber bulundu.")

    # 3. Veritabanından gelen haberleri tek tek dönüp ekrana basıyoruz
    for index, haber in enumerate(son_haberler, start=1):

        # db_operation dosyasında "SELECT id, title, link, kaynak_url, ozet" dediğimiz için
        # veriler tam olarak bu sırayla geliyor. Bunları değişkenlere atıyoruz:
        haber_id, title, link, kaynak_url, ozet = haber

        # Başlıktaki HTML'i bozabilecek (<, >) özel karakterleri temizliyoruz
        baslik = html.escape(str(title))

        # Gönderilecek metni hazırlıyoruz
        mesaj_metni = f"[{index}/{toplam_haber}] <b>{baslik}</b>\n\n{link}\n\n<b>Kaynak:</b> {kaynak_url}"

        # 4. Haberin altına eklenecek "Daha Sonra Oku" butonunu oluşturuyoruz
        markup = InlineKeyboardMarkup()
        # Butonun içine arka planda haberin kimlik numarasını (haber_id) gizliyoruz
        markup.add(InlineKeyboardButton("⭐", callback_data=f"kaydet_{haber_id}"))

        # 5. Mesajı ve butonu Telegram'a gönderiyoruz
        try:
            bot.send_message(
                message.chat.id,
                mesaj_metni,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=markup
            )
            time.sleep(0.4)  # Telegram bizi çok hızlı mesaj atmaktan engellemesin diye kısa bekleme

        except ApiTelegramException as e:

            if e.error_code == 429:
                bekleme_suresi = int(e.result_json.get('parameters', {}).get('retry_after', 3))
                time.sleep(bekleme_suresi + 1)
                bot.send_message(
                    message.chat.id,
                    mesaj_metni,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=markup
                )
            else:
                print(f"Telegram API hatası: {e}")
        except Exception as e:
            print(f"Haber gönderilemedi: {e}")

    bot.send_message(message.chat.id, "Tarama tamamlandı")
@bot.message_handler(commands=['ozet'])
def haber_ozetle(message):
    #mesaja reply yapılmış mı kontrolü
    if message.reply_to_message is None:
        bot.reply_to(message, "Lütfen özetlemek istediğin haberi yanıtlayarak /ozet yaz.")
        return

    #yanıtlanan mesajın içinde metin var mı kontrolü
    if not message.reply_to_message.text:
        bot.reply_to(message, "Yanıtladığın mesaj bir yazı içermiyor.")
        return

    yanitlanan_metin = message.reply_to_message.text
    link_eslesme = re.search(r'https?://[^\s]+', yanitlanan_metin) #linkin nerede olduğu hakkında bilgi paketi

    #mesajın içinden link bulunabildi mi
    if link_eslesme is None:
        bot.reply_to(message, "Yanıtladığın mesajda geçerli bir haber linki bulunamadı.")
        return

    link = link_eslesme.group(0) #o bilgi paketinden tek linki çeker
    bekleme_mesaji = bot.reply_to(message, " Haber içeriği özetleniyor...")

    #haberin web adresine gidip tüm paragraflarını çeker
    detay_metni = scraper.haberin_icine_gir(link)

    #eğer siteden metin çekilemezse veya çok kısa kalırsa yanıtlanan mesajın kendisini kullanır
    if not detay_metni or len(detay_metni) < 50:
        detay_metni = yanitlanan_metin

    gonderilecek_metin = f"Aşağıdaki haberi Türkçe olarak kısa ve öz şekilde özetle:\n\n{detay_metni}"
    ozet_sonucu = ozetle(gonderilecek_metin)

    bot.edit_message_text( #mevcut mesajın yazısını güncelleyen fonksiyon
        chat_id=bekleme_mesaji.chat.id,
        message_id=bekleme_mesaji.message_id, #hangi mesajın değişceğini söyler
        text=f"<b>Haber Özeti:</b>\n\n{ozet_sonucu}", #eski yazının yerine ne yazılıcak
        parse_mode="HTML"
    )


# 1. BUTONA TIKLANDIĞINDA ÇALIŞACAK KISIM
@bot.callback_query_handler(func=lambda call: call.data.startswith('kaydet_'))
def buton(call):
    haber_numarasi = call.data.split('_')[1]
    kullanici_numarasi = call.from_user.id


    basarili_mi = db_operation.favori_ekle(kullanici_numarasi, haber_numarasi)

    # Kullanıcının ekranında çıkacak küçük bildirim mesajı
    if basarili_mi:
        bot.answer_callback_query(call.id, "⭐ Listenize eklendi")
    else:
        bot.answer_callback_query(call.id, "Zaten listenizde var.")


@bot.message_handler(commands=['favoriler'])
def favorileri_goster(message):
    kullanici_numarasi = message.from_user.id
    kaydedilenler = db_operation.favorileri_getir(kullanici_numarasi)

    if not kaydedilenler:
        bot.send_message(message.chat.id, "Listeniz şu an boş.")
        return

    bot.send_message(message.chat.id, f"<b>⭐ Okuma Listeniz ({len(kaydedilenler)} Haber):</b>", parse_mode="HTML")

    for haber in kaydedilenler:
        haber_id = haber[0]
        baslik = html.escape(str(haber[1]))
        link = haber[2]

        # Her haberin altına özel Listeden Çıkar butonu
        markup = types.InlineKeyboardMarkup()
        sil_butonu = types.InlineKeyboardButton("🗑️", callback_data=f"fav_sil_{haber_id}")
        markup.add(sil_butonu)

        mesaj = f"<a href='{link}'><b>{baslik}</b></a>"
        bot.send_message(message.chat.id, mesaj, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

        @bot.callback_query_handler(func=lambda call: call.data.startswith('fav_sil_'))
        def favori_sil_butonu(call):

            haber_id = int(call.data.split('_')[2])
            kullanici_id = call.from_user.id

            db_operation.favori_sil(kullanici_id, haber_id)

            bot.answer_callback_query(call.id, text="❌ Haber favorilerden çıkarıldı.")
            bot.edit_message_text("<i>Bu haber listenizden çıkarıldı.</i>", call.message.chat.id,
                                  call.message.message_id, parse_mode="HTML")

if __name__ == "__main__":
    print(" Telegram'dan mesaj bekleniyor..")
    bot.infinity_polling()#sunucularını kesintisiz ve sonsuz bir döngüde dinlemesini sağlıyor