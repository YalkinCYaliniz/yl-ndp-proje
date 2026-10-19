from randevu.kullanici import Hasta, Doktor, Yonetici
from randevu.klinik import Klinik, Hizmet, RandevuSistemi


def main():
    klinik = Klinik("Merkez Klinik")
    klinik.bolum_ekle("Dahiliye")
    muayene = Hizmet("Genel Muayene", 30, 500.0)
    klinik.hizmet_ekle(muayene)

    doktor = Doktor("Ayşe", "Yılmaz", "12345678901", "Dahiliye")
    doktor.hizmet_ekle(muayene)
    doktor.musaitlik_ekle("Pazartesi", 9, 12)
    klinik.personel_ekle(doktor)

    hasta = Hasta("Ali", "Demir", "10987654321")
    yonetici = Yonetici("Mehmet", "Kaya", "11111111111")

    # Çok biçimlilik: aynı çağrı, role göre farklı sonuç
    for k in (hasta, doktor, yonetici):
        print(k, "->", k.yetkiler())

    sistem = RandevuSistemi(klinik)
    r = sistem.randevu_olustur(hasta, doktor, muayene, "Pazartesi", 9)
    r.onayla()
    print(r)

    try:
        sistem.randevu_olustur(hasta, doktor, muayene, "Pazartesi", 9)
    except ValueError as e:
        print("Hata:", e)


if __name__ == "__main__":
    main()
