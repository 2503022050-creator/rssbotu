import db_operation
import scraper
import time
def calistir():
    print(" RSS Botu çalıştırılıyor \n")

    kaynaklar = db_operation.get_links()

    if not kaynaklar:
        print(" Veritabanında kayıtlı hiç RSS adresi bulunamadı.")
        print(" İpucu: Önce veritabanına bir RSS adresi eklemelisiniz.")
        return

    print(f" Veritabanından {len(kaynaklar)} adet RSS kaynağı alındı. Tarama başlıyor")

    haberler = scraper.rss_tara(kaynaklar)

    if haberler:
        db_operation.haberleri_kaydet(haberler)
        print(f"\n İşlem tamamlandı Toplam {len(haberler)} haber veritabanına işlendi.")
    else:
        print("\n Taranan kaynaklarda yeni bir haber bulunamadı.")


if __name__ == "__main__":
    while True:
        calistir()

        print("\n Tarama bitti. 1 saat  bekleniyor.\n")

        time.sleep(3600)