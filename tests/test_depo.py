import os
import tempfile
import unittest
from datetime import datetime

from randevu.depo import Depo
from randevu.hatalar import SistemHatasi
from randevu.kullanici import Doktor, Hasta, Asistan
from randevu.odeme import KartOdeme
from randevu.randevu import RandevuDurumu
from randevu.uygulama import ornek_veri


class DepoTest(unittest.TestCase):
    def setUp(self):
        self.dosya = os.path.join(tempfile.mkdtemp(), "veri.json")
        self.depo = Depo(self.dosya)

    def test_var_mi(self):
        self.assertFalse(self.depo.var_mi())
        self.depo.kaydet(ornek_veri())
        self.assertTrue(self.depo.var_mi())

    def test_kaydet_yukle_yapi_ayni_kalir(self):
        uyg = ornek_veri()
        self.depo.kaydet(uyg)
        yeni = self.depo.yukle()
        self.assertEqual([str(k) for k in yeni.kullanicilar], [str(k) for k in uyg.kullanicilar])
        self.assertEqual([h.ad for h in yeni.kurum.hastaneler], [h.ad for h in uyg.kurum.hastaneler])
        klinik = yeni.kurum.hastane_bul("Merkez Hastane").klinik_bul("Kardiyoloji")
        self.assertEqual([s.tur() for s in klinik.hizmetler], ["Radyoloji", "Laboratuvar"])
        self.assertEqual([s.ucret for s in klinik.hizmetler], [700.0, 300.0])
        self.assertEqual(len(yeni.kullanicilar), len(uyg.kullanicilar))

    def test_doktor_cok_klinik_ve_musaitlik_korunur(self):
        self.depo.kaydet(ornek_veri())
        doktor = [k for k in self.depo.yukle().kullanicilar if isinstance(k, Doktor)][0]
        self.assertEqual(len(doktor.klinikler), 2)
        self.assertEqual(len(doktor.musaitlik), 6)

    def test_asistan_baglantisi_ve_klinik_personeli_korunur(self):
        self.depo.kaydet(ornek_veri())
        yeni = self.depo.yukle()
        asistan = [k for k in yeni.kullanicilar if isinstance(k, Asistan)][0]
        self.assertEqual(asistan.doktor.tam_ad, "Ayşe Yılmaz")
        self.assertEqual(asistan.doktor.asistan_metni, "Asistan: Elif Aydın")
        dahiliye = yeni.kurum.hastane_bul("Merkez Hastane").klinik_bul("Dahiliye")
        self.assertEqual([p.rol() for p in dahiliye.personeller], ["Asistan", "Hemşire"])

    def test_ayni_tc_iki_kez_kaydedilemez(self):
        uyg = ornek_veri()
        with self.assertRaises(SistemHatasi):
            uyg.kullanici_ekle(Hasta("Kopya", "Kişi", "10987654321"))

    def test_randevu_durum_ve_odeme_korunur(self):
        uyg = ornek_veri()
        hasta = [k for k in uyg.kullanicilar if isinstance(k, Hasta)][0]
        doktor = [k for k in uyg.kullanicilar if isinstance(k, Doktor)][0]
        hastane = uyg.kurum.hastaneler[0]
        klinik = hastane.klinikler[0]
        r = hasta.randevu_al(uyg.sistem, hastane, klinik, doktor,
                             klinik.hizmetler[0], datetime(2026, 10, 28, 9, 0))
        doktor.randevu_onayla(r)
        r.odeme_yap(KartOdeme(3))
        self.depo.kaydet(uyg)

        yeni = self.depo.yukle()
        yr = yeni.sistem.randevular[0]
        self.assertEqual(yr.durum, RandevuDurumu.ONAYLANDI)
        self.assertEqual(yr.odenen_tutar, 520)
        self.assertEqual(yr.baslangic, datetime(2026, 10, 28, 9, 0))
        # yüklenen veride çakışma kuralı hâlâ çalışıyor
        hasta2 = yeni.kullanicilar[2]
        h = yeni.kurum.hastaneler[0]
        k = h.klinikler[0]
        with self.assertRaises(Exception):
            hasta2.randevu_al(yeni.sistem, h, k, k.doktorlar[0], k.hizmetler[0],
                              datetime(2026, 10, 28, 9, 0))


if __name__ == "__main__":
    unittest.main()
