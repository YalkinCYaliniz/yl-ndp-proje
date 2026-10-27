import unittest
from datetime import datetime, time

from randevu.hatalar import RandevuHatasi, YetkiHatasi, BulunamadiHatasi, SistemHatasi
from randevu.kullanici import (Kullanici, Hasta, Doktor, Hemsire, Teknisyen, Yonetici, Asistan)
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


class AsistanTest(TemelTest):
    def setUp(self):
        super().setUp()
        self.diger = Doktor("Can", "Öztürk", "55555555555", "Kardiyoloji")
        self.admin.doktor_ekle(self.kardiyoloji, self.diger)
        self.asistan = Asistan("Elif", "Aydın", "66666666666")

    def test_klinige_atama_cok_biciimli(self):
        self.admin.personel_ata(self.dahiliye, self.asistan)     # personel listesine
        self.admin.personel_ata(self.kardiyoloji, self.diger)    # zaten doktor, tekrar eklenmez
        self.assertIn(self.asistan, self.dahiliye.personeller)
        self.assertNotIn(self.asistan, self.dahiliye.doktorlar)
        self.assertEqual(self.asistan.klinikler, (self.dahiliye,))
        yeni = Doktor("Yeni", "Doktor", "88888888888", "Dahiliye")
        self.admin.personel_ata(self.dahiliye, yeni)             # doktor ise doktor listesine
        self.assertIn(yeni, self.dahiliye.doktorlar)

    def test_ortak_klinik_olmadan_baglanamaz(self):
        self.admin.personel_ata(self.dahiliye, self.asistan)
        with self.assertRaises(SistemHatasi):
            self.admin.asistan_bagla(self.asistan, self.diger)   # diger sadece kardiyolojide

    def test_baglama_ve_baska_doktora_tasima(self):
        self.admin.personel_ata(self.dahiliye, self.asistan)
        self.admin.personel_ata(self.kardiyoloji, self.asistan)
        self.admin.asistan_bagla(self.asistan, self.doktor)
        self.assertIs(self.asistan.doktor, self.doktor)
        self.assertEqual(self.doktor.asistan_metni, "Asistan: Elif Aydın")
        self.admin.asistan_bagla(self.asistan, self.diger)       # taşıma
        self.assertIs(self.asistan.doktor, self.diger)
        self.assertEqual(self.doktor.asistanlar, ())
        self.assertEqual(self.doktor.asistan_metni, "")
        self.assertEqual(self.diger.asistanlar, (self.asistan,))

    def test_bir_doktorun_birden_fazla_asistani_olur(self):
        ikinci = Asistan("Derya", "Kurt", "99999999999")
        for a in (self.asistan, ikinci):
            self.admin.personel_ata(self.dahiliye, a)
            self.admin.asistan_bagla(a, self.doktor)
        self.assertEqual(self.doktor.asistanlar, (self.asistan, ikinci))
        self.assertEqual(self.doktor.asistan_metni, "Asistan: Elif Aydın, Derya Kurt")

    def test_asistan_kapasitesi(self):
        asistanlar = [Asistan(f"A{i}", "Test", f"7000000000{i}") for i in range(Doktor.MAX_ASISTAN + 1)]
        for a in asistanlar[:-1]:
            self.admin.personel_ata(self.dahiliye, a)
            self.admin.asistan_bagla(a, self.doktor)
        self.assertTrue(self.doktor.asistan_kapasitesi_dolu_mu)
        fazla = asistanlar[-1]
        self.admin.personel_ata(self.dahiliye, fazla)
        with self.assertRaises(SistemHatasi):
            self.admin.asistan_bagla(fazla, self.doktor)

    def test_dolu_doktora_tasima_eski_baglantiyi_bozmaz(self):
        self.admin.personel_ata(self.dahiliye, self.asistan)
        self.admin.personel_ata(self.kardiyoloji, self.asistan)
        self.admin.asistan_bagla(self.asistan, self.diger)
        for i in range(Doktor.MAX_ASISTAN):
            a = Asistan(f"B{i}", "Test", f"6000000000{i}")
            self.admin.personel_ata(self.dahiliye, a)
            self.admin.asistan_bagla(a, self.doktor)
        with self.assertRaises(SistemHatasi):
            self.admin.asistan_bagla(self.asistan, self.doktor)
        self.assertIs(self.asistan.doktor, self.diger)      # hâlâ eski doktorda

    def test_asistan_ayirma(self):
        self.admin.personel_ata(self.dahiliye, self.asistan)
        self.admin.asistan_bagla(self.asistan, self.doktor)
        self.admin.asistan_ayir(self.asistan)
        self.assertIsNone(self.asistan.doktor)
        self.assertEqual(self.doktor.asistanlar, ())
        self.assertFalse(self.hasta.yetki_var_mi("asistan_bagla"))   # hasta bu işlemi yapamaz

    def test_hasta_hazirla_sadece_bagli_doktor(self):
        self.admin.personel_ata(self.dahiliye, self.asistan)
        self.admin.asistan_bagla(self.asistan, self.doktor)
        r = self.randevu_al()
        self.assertIn("hazırlandı", self.asistan.hasta_hazirla(r))
        self.admin.personel_ata(self.kardiyoloji, self.asistan)
        self.admin.asistan_bagla(self.asistan, self.diger)
        with self.assertRaises(YetkiHatasi):
            self.asistan.hasta_hazirla(r)

    def test_sadece_admin_personel_yonetir(self):
        self.assertFalse(self.hasta.yetki_var_mi("asistan_bagla"))
        self.assertFalse(self.doktor.yetki_var_mi("personel_ata"))
        self.assertTrue(self.admin.yetki_var_mi("asistan_bagla"))

    def test_asistan_rol_ve_kalitim(self):
        self.assertEqual(self.asistan.rol(), "Asistan")
        self.assertIsInstance(self.asistan, Kullanici)
        self.assertNotIn("randevu_onayla", self.asistan.yetkiler())


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

    def test_musait_gunler_ve_bos_sayisi(self):
        self.assertEqual(self.sistem.musait_gunler(self.merkez, self.doktor, self.muayene),
                         [(self.zaman.date(), 4)])
        self.randevu_al()
        self.assertEqual(self.sistem.musait_gunler(self.merkez, self.doktor, self.muayene)[0][1], 3)

    def test_dolu_slot_randevuyu_gosterir(self):
        r = self.randevu_al()
        slotlar = self.sistem.saat_tablosu(self.merkez, self.doktor, self.muayene, self.zaman.date())
        dolu = [s for s in slotlar if s.dolu][0]
        self.assertIs(dolu.randevu, r)

    def test_musaitlik_cakisan_aralik_eklenemez(self):
        with self.assertRaises(ValueError):
            self.doktor.musaitlik_ekle(datetime(2026, 10, 14, 14, 0), datetime(2026, 10, 14, 16, 0))

    def test_musaitlik_sil(self):
        self.doktor.musaitlik_sil(0, self.sistem.doktorun_randevulari(self.doktor))
        self.assertEqual(self.doktor.musaitlik, ())

    def test_aktif_randevusu_olan_musaitlik_silinemez(self):
        r = self.randevu_al()
        with self.assertRaises(RandevuHatasi):
            self.doktor.musaitlik_sil(0, self.sistem.doktorun_randevulari(self.doktor))
        self.hasta.randevu_iptal(r)         # iptal sonrası silinebilir
        self.doktor.musaitlik_sil(0, self.sistem.doktorun_randevulari(self.doktor))
        self.assertEqual(self.doktor.musaitlik, ())

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
