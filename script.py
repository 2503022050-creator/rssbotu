import html
import os
import re
import time
import threading
import telebot
from dotenv import load_dotenv
import scraper
import db_operation
from ai_helper import ozetle
from telebot import types
from telebot.types import BotCommand

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(token)

# Mavi Menü (☰) Sadeleştirmesi
bot.set_my_commands([
    BotCommand("ozet", "Yanıtlanan haberi özetle"),
    BotCommand("ekle", "Yeni kaynak ekle"),
    BotCommand("sil", "Kayıtlı kaynak sil"),
    BotCommand("start", "Menüyü açar"),
])


def sabit_menu_getir():
    # is_persistent=True ile klavyeyi ekrana sabitliyoruz
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=3,
        is_persistent=True #kalıcılığı sağlayan kısım
    )

    btn_24 = types.KeyboardButton("Son 24 Saat")
    btn_3_gun = types.KeyboardButton("Son 3 Gün")
    btn_hafta = types.KeyboardButton("Son 1 Hafta")
    btn_fav = types.KeyboardButton("⭐ Favoriler")
    btn_kaynaklar = types.KeyboardButton("Kaynaklar")

    markup.row(btn_24, btn_3_gun, btn_hafta)
    markup.row(btn_fav, btn_kaynaklar)
    return markup


def calistir(isteyen_kisi_id=None, bildirim=True):
    kaynaklar = db_operation.get_links()

    if not kaynaklar:
        print("Veritabanında kayıtlı RSS adresi bulunamadı.")
        return []

    print(f"Veritabanından {len(kaynaklar)} adet RSS kaynağı alındı. Tarama başlıyor")
    haberler = scraper.rss_tara(kaynaklar)

    if haberler:
        gorulen_linkler = set()
        benzersiz_haberler = []
        for h in haberler:
            if h["link"] not in gorulen_linkler:
                gorulen_linkler.add(h["link"])
                benzersiz_haberler.append(h)
        haberler = benzersiz_haberler

        yeni_sayisi = db_operation.haberleri_kaydet(haberler, isteyen_kisi_id, bildirim=bildirim)
        print(
            f"\n İşlem tamamlandı: Toplam {len(haberler)} güncel haber tarandı ({yeni_sayisi} yeni haber veritabanına işlendi).")
    else:
        print("\n Taranan kaynaklarda yeni bir haber bulunamadı.")

    return haberler or []


# --- START KOMUTU VE BUTON YÖNETİMİ ---
@bot.message_handler(commands=['start'])
def karsilama(message):
    bot.send_message(message.chat.id, "Haber botuna hoş geldiniz\n", reply_markup=sabit_menu_getir())


@bot.message_handler(
    func=lambda message: message.text in ["Son 24 Saat", "Son 3 Gün", "Son 1 Hafta", "⭐ Favoriler", "Kaynaklar"])
def sabit_menu_islem(message):
    chat_id = message.chat.id
    kullanici_id = message.from_user.id  # Kullanıcıyı tanımak için
    secim = message.text

    if secim == "Son 24 Saat":
        haberler = db_operation.son_haberleri_getir(kullanici_id,limit=100)
        bot.send_message(chat_id, "Son 24 saat içindeki güncel haberler getiriliyor...",
                         reply_markup=sabit_menu_getir())
        haberleri_bas(chat_id, haberler, kullanici_id)


    elif secim == "Son 3 Gün":
        haberler = db_operation.son_3_gun(kullanici_id,limit=200)
        bot.send_message(chat_id, "Son 3 gün içindeki haberler getiriliyor...", reply_markup=sabit_menu_getir())
        haberleri_bas(chat_id, haberler, kullanici_id)

    elif secim == "Son 1 Hafta":
        haberler = db_operation.son_1_hafta(kullanici_id , limit=300)
        bot.send_message(chat_id, "Son 1 haftanın haberleri getiriliyor...", reply_markup=sabit_menu_getir())
        haberleri_bas(chat_id, haberler, kullanici_id)

    elif secim == "⭐ Favoriler":
        kaydedilenler = db_operation.favorileri_getir(message.from_user.id)
        if not kaydedilenler:
            bot.send_message(chat_id, "Listeniz şu an boş.", reply_markup=sabit_menu_getir())
            return
        bot.send_message(chat_id, f"<b>⭐ Okuma Listeniz ({len(kaydedilenler)} Haber):</b>", parse_mode="HTML",
                         reply_markup=sabit_menu_getir())

        for haber in kaydedilenler:
            haber_id = haber[0]
            baslik = html.escape(str(haber[1]))
            link = haber[2]

            markup = types.InlineKeyboardMarkup()
            sil_butonu = types.InlineKeyboardButton("🗑️", callback_data=f"fav_sil_{haber_id}")
            markup.add(sil_butonu)

            mesaj = f"<a href='{link}'><b>{baslik}</b></a>"
            bot.send_message(chat_id, mesaj, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

    elif secim == "Kaynaklar":
        kaynaklar_getir(message)


def haberleri_bas(chat_id, haber_listesi,kullanici_id):
    if not haber_listesi:
        bot.send_message(chat_id, "Bu aralıkta haber bulunamadı.", reply_markup=sabit_menu_getir())
        return

    toplam = len(haber_listesi)
    # Haber sayısının söylendiği ilk mesaja menüyü bağlıyoruz, ekran kapanmıyor:
    bot.send_message(chat_id, f"Toplam {toplam} haber bulundu.", reply_markup=sabit_menu_getir())

    for index, haber in enumerate(haber_listesi, start=1):
        haber_id, title, link, kaynak_url, ozet = haber
        baslik = html.escape(str(title))

        mesaj_metni = f"[{index}/{toplam}] <b>{baslik}</b>\n\n{link}\n\n<b>Kaynak:</b> {kaynak_url}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⭐", callback_data=f"kaydet_{haber_id}"))

        try:
            bot.send_message(chat_id, mesaj_metni, parse_mode="HTML", disable_web_page_preview=True,
                             reply_markup=markup)
            #Haberi ekrana bastıktan hemen sonra okundu olarak veritabanına yazıyoruz
            db_operation.haber_okundu_isaretle(kullanici_id, haber_id)
            time.sleep(0.4)
        except Exception as e:
            print(f"Hata: {e}")
            time.sleep(1)

            # DÖNGÜNÜN DIŞINA/ALTINA BU SATIRI EKLİYORUZ
    bot.send_message(chat_id, "Tüm haberler listelendi.", reply_markup=sabit_menu_getir())


# --- KAYNAK YÖNETİMİ ---
@bot.message_handler(commands=['kaynaklar'])
def kaynaklar_getir(message):
    siteler = db_operation.get_links()
    if not siteler:
        bot.send_message(message.chat.id, "Kayıtlı RSS kaynağı bulunamadı.", reply_markup=sabit_menu_getir())
        return
    liste_metni = "\n".join([f"{index}. {url}" for index, url in enumerate(siteler, start=1)])
    mesaj_metni = f"Kayıtlı Kaynaklar ({len(siteler)} Adet):\n\n{liste_metni}"
    bot.send_message(message.chat.id, mesaj_metni, disable_web_page_preview=True, reply_markup=sabit_menu_getir())


@bot.message_handler(commands=['ekle'])
def kaynak_ekle_sor(message):
    mesaj = bot.reply_to(message, "Eklemek istediğiniz RSS linkini yazınız.", reply_markup=sabit_menu_getir())
    bot.register_next_step_handler(mesaj, kaynak_ekle_kaydet)


def kaynak_ekle_kaydet(message):
    yeni_url = message.text.strip()
    if yeni_url.startswith('/'):
        bot.process_new_messages([message])
        return
    if not (yeni_url.startswith("http://") or yeni_url.startswith("https://")):
        bot.reply_to(message, "Geçersiz link. Gönderdiğiniz metin 'http://' veya 'https://' ile başlamalıdır.",
                     reply_markup=sabit_menu_getir())
        return
    mevcut_kaynaklar = db_operation.get_links()
    if yeni_url in mevcut_kaynaklar:
        bot.reply_to(message, "Bu kaynak listede mevcut.", reply_markup=sabit_menu_getir())
    else:
        ekleyen_kisi = message.from_user.username or message.from_user.first_name
        db_operation.add_link(yeni_url, ekleyen_kisi)
        bot.reply_to(message, f"Yeni kaynak eklendi:\n{yeni_url}\n(Ekleyen: {ekleyen_kisi})",
                     reply_markup=sabit_menu_getir())


@bot.message_handler(commands=['sil'])
def kaynak_sil_sor(message):
    mesaj = bot.reply_to(message, "Silmek istediğiniz RSS linkini yazınız.", reply_markup=sabit_menu_getir())
    bot.register_next_step_handler(mesaj, kaynak_sil_tamamla)


def kaynak_sil_tamamla(message):
    silinecek_url = message.text.strip()
    if silinecek_url.startswith('/'):
        bot.process_new_messages([message])
        return
    if not (silinecek_url.startswith("http://") or silinecek_url.startswith("https://")):
        bot.reply_to(message,
                     "Geçersiz link formatı. 'http://' veya 'https://' ile başlayan geçerli bir RSS linki giriniz.",
                     reply_markup=sabit_menu_getir())
        return
    mevcut_kaynaklar = db_operation.get_links()
    if silinecek_url in mevcut_kaynaklar:
        db_operation.delete_link(silinecek_url)
        bot.reply_to(message, f"Kaynak silindi:\n{silinecek_url}", reply_markup=sabit_menu_getir())
    else:
        bot.reply_to(message, "Bu kaynak listenizde zaten bulunmuyor.", reply_markup=sabit_menu_getir())


# --- ÖZET VE FAVORİ BUTONLARI ---
@bot.message_handler(commands=['ozet'])
def haber_ozetle(message):
    if message.reply_to_message is None:
        bot.reply_to(message, "Lütfen özetlemek istediğin haberi yanıtlayarak /ozet yaz.", reply_markup=sabit_menu_getir())
        return
    if not message.reply_to_message.text:
        bot.reply_to(message, "Yanıtladığın mesaj bir yazı içermiyor.", reply_markup=sabit_menu_getir())
        return
    yanitlanan_metin = message.reply_to_message.text
    link_eslesme = re.search(r'https?://[^\s]+', yanitlanan_metin)
    if link_eslesme is None:
        bot.reply_to(message, "Yanıtladığın mesajda geçerli bir haber linki bulunamadı.", reply_markup=sabit_menu_getir())
        return
    link = link_eslesme.group(0)
    bekleme_mesaji = bot.reply_to(message, "Haber içeriği özetleniyor...")
    detay_metni = scraper.haberin_icine_gir(link)
    if not detay_metni or len(detay_metni) < 50:
        detay_metni = yanitlanan_metin
    gonderilecek_metin = f"Aşağıdaki haberi Türkçe olarak kısa ve öz şekilde özetle:\n\n{detay_metni}"
    ozet_sonucu = ozetle(gonderilecek_metin)
    bot.edit_message_text(
        chat_id=bekleme_mesaji.chat.id,
        message_id=bekleme_mesaji.message_id,
        text=f"<b>Haber Özeti:</b>\n\n{ozet_sonucu}",
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('kaydet_'))
def buton(call):
    haber_numarasi = call.data.split('_')[1]
    kullanici_numarasi = call.from_user.id
    x = db_operation.favori_ekle(kullanici_numarasi, haber_numarasi)
    if x:
        bot.answer_callback_query(call.id, "⭐ Listenize eklendi")
    else:
        bot.answer_callback_query(call.id, "Zaten listenizde var.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('fav_sil_'))
def favori_sil_butonu(call):
    haber_id = int(call.data.split('_')[2])
    kullanici_id = call.from_user.id
    db_operation.favori_sil(kullanici_id, haber_id)
    bot.answer_callback_query(call.id, text="❌ Haber favorilerden çıkarıldı.")
    bot.edit_message_text("<i>Bu haber listenizden çıkarıldı.</i>", call.message.chat.id, call.message.message_id,
                          parse_mode="HTML")


# --- ARKA PLAN OTOMASYONU VE ÇALIŞTIRMA ---
def saatlik_tarama():
    while True:
        print("⏳ Arka plan taraması tetiklendi (Sessiz mod).")
        calistir(bildirim=False)
        time.sleep(3600)


if __name__ == "__main__":
    arka_plan_motoru = threading.Thread(target=saatlik_tarama, daemon=True)
    arka_plan_motoru.start()

    print("🚀 Telegram'dan mesaj bekleniyor..")
    bot.infinity_polling()