from datetime import date, datetime, time

from randevu.kullanici import Hasta, Doktor, Yonetici
from randevu.kurum import Kurum, Hastane, Klinik, Hizmet
from randevu.randevu import RandevuSistemi


def main():
    # Kurum -> Hastane -> Klinik -> Doktor
    kurum = Kurum("Yaşam Sağlık Grubu")
    merkez = Hastane("Merkez Hastane", time(8, 0), time(17, 0))
    kadikoy = Hastane("Kadıköy Hastane", time(9, 0), time(18, 0))
    kurum.hastane_ekle(merkez)
    kurum.hastane_ekle(kadikoy)

    dahiliye = Klinik("Dahiliye")
    kardiyoloji = Klinik("Kardiyoloji")
    merkez.klinik_ekle(dahiliye)
    merkez.klinik_ekle(kardiyoloji)

    # Hizmetler kliniğe bağlı
    muayene = Hizmet("Genel Muayene", 30, 500.0)
    ekg = Hizmet("EKG", 30, 700.0)
    dahiliye.hizmet_ekle(muayene)
    kardiyoloji.hizmet_ekle(muayene)
    kardiyoloji.hizmet_ekle(ekg)

    # Bir doktor iki kliniğe bağlı
    doktor = Doktor("Ayşe", "Yılmaz", "12345678901", "Dahiliye")
    dahiliye.doktor_ekle(doktor)
    kardiyoloji.doktor_ekle(doktor)

    gun = date(2026, 10, 14)
    # Doktor 14.10.2026 günü 13:00-15:00 arası çalışıyor
    doktor.musaitlik_ekle(datetime(2026, 10, 14, 13, 0), datetime(2026, 10, 14, 15, 0))

    hasta = Hasta("Ali", "Demir", "10987654321")
    yonetici = Yonetici("Mehmet", "Kaya", "11111111111")

    # Çok biçimlilik: aynı çağrı, role göre farklı sonuç
    for k in (hasta, doktor, yonetici):
        print(k, "->", k.yetkiler())

    # MHRS akışı: hastane -> klinik -> doktor -> saat tablosu
    sistem = RandevuSistemi()
    print("Doktorun klinikleri:", [k.ad for k in doktor.klinikler])

    def tabloyu_goster():
        for slot in sistem.saat_tablosu(merkez, doktor, muayene, gun):
            print("  ", slot)

    print("Saat tablosu (başlangıç):")
    tabloyu_goster()

    zaman = datetime(2026, 10, 14, 13, 30)
    r = sistem.randevu_olustur(hasta, merkez, dahiliye, doktor, muayene, zaman)
    r.onayla()
    print(r)
    print("Randevudan sonra:")
    tabloyu_goster()

    try:
        sistem.randevu_olustur(hasta, merkez, kardiyoloji, doktor, ekg, zaman)
    except ValueError as e:
        print("Hata:", e)

    r.iptal()
    print("İptalden sonra (13:30 tekrar yeşil):")
    tabloyu_goster()


if __name__ == "__main__":
    main()
