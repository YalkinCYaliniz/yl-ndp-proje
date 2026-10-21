from datetime import date, datetime, time

from randevu.kullanici import Hasta, Doktor, Yonetici
from randevu.kurum import Kurum, Hastane, Klinik, Muayene, Radyoloji, Laboratuvar
from randevu.randevu import RandevuSistemi


def main():
    kurum = Kurum("Yaşam Sağlık Grubu")
    sistem = RandevuSistemi()

    admin = Yonetici("Mehmet", "Kaya", "11111111111")
    hasta = Hasta("Ali", "Demir", "10987654321")
    baska_hasta = Hasta("Veli", "Can", "22222222222")
    doktor = Doktor("Ayşe", "Yılmaz", "12345678901", "Dahiliye")

    # Çok biçimlilik: aynı çağrı, role göre farklı sonuç
    for k in (admin, hasta, doktor):
        print(k, "->", k.yetkiler())

    # Admin yapıyı kurar: Kurum -> Hastane -> Klinik -> Doktor
    merkez = Hastane("Merkez Hastane", time(8, 0), time(17, 0))
    dahiliye = Klinik("Dahiliye")
    kardiyoloji = Klinik("Kardiyoloji")
    muayene = Muayene("Genel Muayene", 30, 500.0)
    ekg = Radyoloji("EKG", 30, 400.0, cihaz_ucreti=300.0)

    admin.hastane_ekle(kurum, merkez)
    admin.klinik_ekle(merkez, dahiliye)
    admin.klinik_ekle(merkez, kardiyoloji)
    admin.hizmet_ekle(dahiliye, muayene)
    admin.hizmet_ekle(kardiyoloji, ekg)
    admin.doktor_ekle(dahiliye, doktor)
    admin.doktor_ekle(kardiyoloji, doktor)   # bir doktor iki klinikte
    doktor.musaitlik_ekle(datetime(2026, 10, 14, 13, 0), datetime(2026, 10, 14, 15, 0))

    # Normal kullanıcı randevu alır
    zaman = datetime(2026, 10, 14, 13, 30)
    r = hasta.randevu_al(sistem, merkez, dahiliye, doktor, muayene, zaman)
    doktor.randevu_onayla(r)
    print(r)

    # Yetkisiz işlemler engellenir
    denemeler = [
        ("Hasta hastane eklemeye çalışıyor", lambda: hasta.hastane_ekle(kurum, merkez)),
        ("Başkası randevuyu iptal etmeye çalışıyor", lambda: baska_hasta.randevu_iptal(r)),
    ]
    for aciklama, islem in denemeler:
        try:
            islem()
        except (PermissionError, AttributeError) as e:
            print(aciklama, "-> Engellendi:", e)

    # Hasta kendi randevusunu iptal eder -> saat yeşile döner
    hasta.randevu_iptal(r)
    print(r.durum.value)
    for slot in sistem.saat_tablosu(merkez, doktor, muayene, date(2026, 10, 14)):
        print("  ", slot)


if __name__ == "__main__":
    main()
