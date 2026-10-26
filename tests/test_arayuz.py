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
