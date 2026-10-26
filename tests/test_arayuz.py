"""Flask arayüzü için duman (smoke) testleri."""
import unittest

import app as uygulama_modulu
from randevu.uygulama import ornek_veri


class ArayuzTest(unittest.TestCase):
    def setUp(self):
        uygulama_modulu.uyg = ornek_veri()      # her testte temiz veri
        uygulama_modulu.depo = None             # testler dosyaya yazmasın
        self.istemci = uygulama_modulu.app.test_client()

    def giris(self, sira):
        self.istemci.get(f"/giris/{sira}")

    def test_giris_sayfasi(self):
        self.assertEqual(self.istemci.get("/").status_code, 200)

    def test_her_rol_paneli_acilir(self):
        for sira in range(4):       # admin, ali, veli, doktor
            self.giris(sira)
            self.assertEqual(self.istemci.get("/panel").status_code, 200)

    def test_saat_tablosu_ve_randevu_akisi(self):
        self.giris(1)
        sayfa = self.istemci.get("/panel?h=0&k=0&d=0&s=0&tarih=2026-10-28").get_data(as_text=True)
        self.assertIn("slot bos", sayfa)
        self.istemci.post("/hasta/randevu-al", data={
            "h": 0, "k": 0, "d": 0, "s": 0, "zaman": "2026-10-28T09:00:00"})
        sayfa = self.istemci.get("/panel?h=0&k=0&d=0&s=0&tarih=2026-10-28").get_data(as_text=True)
        self.assertIn("slot dolu", sayfa)
        self.assertIn("Bekliyor", sayfa)

    def test_hasta_musait_gunleri_gorur(self):
        self.giris(1)
        sayfa = self.istemci.get("/panel?h=0&k=0&d=0&s=0").get_data(as_text=True)
        self.assertIn("28.10.2026", sayfa)
        self.assertIn("12 boş", sayfa)

    def test_doktor_takvimi(self):
        self.giris(3)
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Takvimim", sayfa)
        self.assertIn("slot bos", sayfa)

    def test_doktor_musaitlik_ekler_ve_siler(self):
        self.giris(3)
        doktor = uygulama_modulu.uyg.doktorlar()[0]
        onceki = len(doktor.musaitlik)
        self.istemci.post("/doktor/musaitlik", data={
            "baslangic": "2026-11-05T09:00", "bitis": "2026-11-05T12:00"})
        self.assertEqual(len(doktor.musaitlik), onceki + 1)
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("05.11.2026", sayfa)
        self.istemci.post(f"/doktor/musaitlik-sil/{onceki}")
        self.assertEqual(len(doktor.musaitlik), onceki)

    def test_yetkisiz_islem_engellenir(self):
        self.giris(1)       # hasta, admin işlemi dener
        self.istemci.post("/admin/hastane", data={"ad": "X", "acilis": "08:00", "kapanis": "17:00"})
        self.assertEqual(len(uygulama_modulu.uyg.kurum.hastaneler), 2)

    def test_admin_hastane_ekler(self):
        self.giris(0)
        self.istemci.post("/admin/hastane", data={"ad": "Yeni", "acilis": "08:00", "kapanis": "17:00"})
        self.assertEqual(len(uygulama_modulu.uyg.kurum.hastaneler), 3)


if __name__ == "__main__":
    unittest.main()
