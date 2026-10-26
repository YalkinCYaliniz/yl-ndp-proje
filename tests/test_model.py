import unittest
from datetime import datetime, time

from randevu.hatalar import RandevuHatasi, YetkiHatasi, BulunamadiHatasi, SistemHatasi
from randevu.kullanici import (Kullanici, Hasta, Doktor, Hemsire, Teknisyen, Yonetici)
from randevu.kurum import Kurum, Hastane, Klinik, Muayene, Radyoloji, Laboratuvar, Hizmet
from randevu.odeme import NakitOdeme, KartOdeme, SigortaOdeme
from randevu.randevu import RandevuSistemi, RandevuDurumu


class TemelTest(unittest.TestCase):
    """Her testten önce küçük bir hastane yapısı kurar."""

    def setUp(self):
        self.admin = Yonetici("Mehmet", "Kaya", "11111111111")
        self.hasta = Hasta("Ali", "Demir", "10987654321")
        self.hasta2 = Hasta("Veli", "Can", "22222222222")
        self.doktor = Doktor("Ayşe", "Yılmaz", "12345678901", "Dahiliye")
        self.kurum = Kurum("Grup")
        self.merkez = Hastane("Merkez", time(8, 0), time(17, 0))
        self.dahiliye = Klinik("Dahiliye")
        self.kardiyoloji = Klinik("Kardiyoloji")
        self.muayene = Muayene("Muayene", 30, 500.0)
        self.ekg = Radyoloji("EKG", 30, 400.0, cihaz_ucreti=300.0)
        self.admin.hastane_ekle(self.kurum, self.merkez)
        self.admin.klinik_ekle(self.merkez, self.dahiliye)
        self.admin.klinik_ekle(self.merkez, self.kardiyoloji)
        self.admin.hizmet_ekle(self.dahiliye, self.muayene)
        self.admin.hizmet_ekle(self.kardiyoloji, self.ekg)
        self.admin.doktor_ekle(self.dahiliye, self.doktor)
        self.admin.doktor_ekle(self.kardiyoloji, self.doktor)
        self.doktor.musaitlik_ekle(datetime(2026, 10, 14, 13, 0), datetime(2026, 10, 14, 15, 0))
        self.sistem = RandevuSistemi()
        self.zaman = datetime(2026, 10, 14, 13, 30)

    def randevu_al(self, hasta=None, zaman=None):
        return (hasta or self.hasta).randevu_al(
            self.sistem, self.merkez, self.dahiliye, self.doktor, self.muayene, zaman or self.zaman)


class KullaniciTest(TemelTest):
    def test_soyut_sinif_olusturulamaz(self):
        with self.assertRaises(TypeError):
            Kullanici("A", "B", "12345678901")

    def test_tc_dogrulama_kapsulleme(self):
        with self.assertRaises(ValueError):
            Hasta("A", "B", "123")
        self.hasta.tc_no = "55555555555"
        self.assertEqual(self.hasta.tc_no, "55555555555")

    def test_cok_bicimlilik_roller(self):
        roller = [k.rol() for k in (self.admin, self.hasta, self.doktor,
                                    Hemsire("H", "S", "33333333333", "Hemşirelik"),
                                    Teknisyen("T", "K", "44444444444", "Radyoloji", "EKG"))]
        self.assertEqual(roller, ["Admin", "Hasta", "Doktor", "Hemşire", "Teknisyen"])

    def test_kalitim(self):
        self.assertIsInstance(self.doktor, Kullanici)
        self.assertTrue(issubclass(Hemsire, Kullanici))

    def test_hemsire_onaylayamaz(self):
        hemsire = Hemsire("H", "S", "33333333333", "Hemşirelik")
        r = self.randevu_al()
        with self.assertRaises(YetkiHatasi):
            hemsire.randevu_onayla(r)

    def test_doktor_birden_fazla_klinik_ve_hizmet(self):
        self.assertEqual(len(self.doktor.klinikler), 2)
        self.assertEqual(len(self.doktor.hizmetler), 2)

    def test_hasta_admin_islemi_yapamaz(self):
        self.assertFalse(self.hasta.yetki_var_mi("hastane_ekle"))
        self.assertTrue(self.admin.yetki_var_mi("hastane_ekle"))


class HizmetTest(unittest.TestCase):
    def test_soyut_hizmet_olusturulamaz(self):
        with self.assertRaises(TypeError):
            Hizmet("x", 10, 1.0)

    def test_overriding_ucret(self):
        self.assertEqual(Muayene("m", 30, 500).ucret_hesapla(), 500)
        self.assertEqual(Radyoloji("r", 30, 400, 300).ucret_hesapla(), 700)
        self.assertEqual(Laboratuvar("l", 15, 100, 3).ucret_hesapla(), 300)

    def test_overloading_indirim(self):
        self.assertEqual(Muayene("m", 30, 500).ucret_hesapla(0.1), 450)


class OdemeTest(unittest.TestCase):
    def test_odeme_yontemleri(self):
        self.assertEqual(NakitOdeme().toplam_hesapla(500), 500)
        self.assertAlmostEqual(KartOdeme(3).toplam_hesapla(500), 520)
        self.assertAlmostEqual(SigortaOdeme().toplam_hesapla(500), 100)


class KurumTest(TemelTest):
    def test_bulunamadi(self):
        with self.assertRaises(BulunamadiHatasi):
            self.kurum.hastane_bul("Yok")
        with self.assertRaises(BulunamadiHatasi):
            self.merkez.klinik_bul("Yok")

    def test_hata_hiyerarsisi(self):
        self.assertTrue(issubclass(RandevuHatasi, SistemHatasi))
        self.assertTrue(issubclass(YetkiHatasi, SistemHatasi))

    def test_koleksiyonlar_salt_okunur(self):
        self.assertIsInstance(self.merkez.klinikler, tuple)
        self.assertIsInstance(self.dahiliye.doktorlar, tuple)


class RandevuTest(TemelTest):
    def test_randevu_olusur_ve_bekler(self):
        r = self.randevu_al()
        self.assertEqual(r.durum, RandevuDurumu.BEKLIYOR)
        self.assertEqual(r.bitis, datetime(2026, 10, 14, 14, 0))

    def test_cakisma(self):
        self.randevu_al()
        with self.assertRaises(RandevuHatasi):
            self.randevu_al(self.hasta2)

    def test_kismi_cakisma_baska_klinikte_de_engellenir(self):
        self.randevu_al()
        with self.assertRaises(RandevuHatasi):
            self.hasta2.randevu_al(self.sistem, self.merkez, self.kardiyoloji,
                                   self.doktor, self.ekg, datetime(2026, 10, 14, 13, 45))

    def test_musait_olmayan_saat(self):
        with self.assertRaises(RandevuHatasi):
            self.randevu_al(zaman=datetime(2026, 10, 14, 16, 0))

    def test_hastane_kapali(self):
        self.doktor.musaitlik_ekle(datetime(2026, 10, 15, 18, 0), datetime(2026, 10, 15, 20, 0))
        with self.assertRaises(RandevuHatasi):
            self.randevu_al(zaman=datetime(2026, 10, 15, 18, 0))

    def test_hizmet_klinige_ait_olmali(self):
        with self.assertRaises(RandevuHatasi):
            self.hasta.randevu_al(self.sistem, self.merkez, self.dahiliye,
                                  self.doktor, self.ekg, self.zaman)

    def test_saat_tablosu_dolu_ve_iptalde_yesil(self):
        r = self.randevu_al()
        gun = self.zaman.date()
        slotlar = {s.baslangic: s for s in self.sistem.saat_tablosu(self.merkez, self.doktor, self.muayene, gun)}
        self.assertEqual(len(slotlar), 4)
        self.assertTrue(slotlar[self.zaman].dolu)
        self.assertEqual(slotlar[self.zaman].renk, "kırmızı")
        self.hasta.randevu_iptal(r)
        slotlar = {s.baslangic: s for s in self.sistem.saat_tablosu(self.merkez, self.doktor, self.muayene, gun)}
        self.assertFalse(slotlar[self.zaman].dolu)
        self.assertEqual(slotlar[self.zaman].renk, "yeşil")

    def test_baskasinin_randevusu_iptal_edilemez(self):
        r = self.randevu_al()
        with self.assertRaises(YetkiHatasi):
            self.hasta2.randevu_iptal(r)

    def test_onay_ve_red_kurallari(self):
        r = self.randevu_al()
        self.doktor.randevu_onayla(r)
        self.assertEqual(r.durum, RandevuDurumu.ONAYLANDI)
        with self.assertRaises(RandevuHatasi):
            self.doktor.randevu_reddet(r)

    def test_red_saati_bosaltir(self):
        r = self.randevu_al()
        self.doktor.randevu_reddet(r)
        self.assertEqual(r.durum, RandevuDurumu.REDDEDILDI)
        self.randevu_al(self.hasta2)        # aynı saat tekrar alınabilir

    def test_iptal_iki_kez_olmaz(self):
        r = self.randevu_al()
        self.hasta.randevu_iptal(r)
        with self.assertRaises(RandevuHatasi):
            self.hasta.randevu_iptal(r)

    def test_listeleme(self):
        r = self.randevu_al()
        self.assertEqual(self.hasta.randevularim(self.sistem), [r])
        self.assertEqual(self.sistem.bekleyen_randevular(self.doktor), [r])
        self.doktor.randevu_onayla(r)
        self.assertEqual(self.sistem.bekleyen_randevular(self.doktor), [])

    def test_odeme_sadece_onayli_ve_tek_sefer(self):
        r = self.randevu_al()
        with self.assertRaises(RandevuHatasi):
            r.odeme_yap(NakitOdeme())
        self.doktor.randevu_onayla(r)
        self.assertEqual(r.odeme_yap(KartOdeme(3)), 520)
        self.assertTrue(r.odendi_mi)
        with self.assertRaises(RandevuHatasi):
            r.odeme_yap(NakitOdeme())

    def test_admin_randevu_ekleyebilir(self):
        r = self.admin.randevu_ekle(self.sistem, self.hasta, self.merkez, self.dahiliye,
                                    self.doktor, self.muayene, self.zaman)
        self.assertIs(r.hasta, self.hasta)


if __name__ == "__main__":
    unittest.main()
