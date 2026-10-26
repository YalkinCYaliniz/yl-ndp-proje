"""JSON ile kaydetme / yükleme."""
import json
import os
from datetime import datetime, time

from randevu.kullanici import Hasta, Doktor, Yonetici, Hemsire, Teknisyen
from randevu.kurum import Hastane, Klinik, Muayene, Radyoloji, Laboratuvar
from randevu.randevu import Randevu, RandevuDurumu
from randevu.uygulama import Uygulama


class Depo:
    """Uygulama verisini bir JSON dosyasına yazar ve oradan geri okur."""

    def __init__(self, dosya: str):
        self._dosya = dosya

    def var_mi(self) -> bool:
        return os.path.exists(self._dosya)

    # ---------------- KAYDET ----------------
    def kaydet(self, uyg: Uygulama) -> None:
        veri = {
            "kurum": uyg.kurum.ad,
            "kullanicilar": [k.sozluge() for k in uyg.kullanicilar],
            "hastaneler": [self._hastane_sozluge(h) for h in uyg.kurum.hastaneler],
            "randevular": [self._randevu_sozluge(r) for r in uyg.sistem.randevular],
        }
        with open(self._dosya, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)

    def _hastane_sozluge(self, h) -> dict:
        return {
            "ad": h.ad, "acilis": h.acilis.isoformat(), "kapanis": h.kapanis.isoformat(),
            "klinikler": [{
                "ad": k.ad,
                "hizmetler": [s.sozluge() for s in k.hizmetler],   # çok biçimlilik
                "doktorlar": [d.tc_no for d in k.doktorlar],
            } for k in h.klinikler],
        }

    def _randevu_sozluge(self, r) -> dict:
        return {
            "hasta": r.hasta.tc_no, "hastane": r.hastane.ad, "klinik": r.klinik.ad,
            "doktor": r.doktor.tc_no, "hizmet": r.hizmet.ad,
            "baslangic": r.baslangic.isoformat(), "durum": r.durum.name,
            "odenen_tutar": r.odenen_tutar,
        }

    # ---------------- YÜKLE ----------------
    def yukle(self) -> Uygulama:
        with open(self._dosya, encoding="utf-8") as f:
            veri = json.load(f)

        uyg = Uygulama()
        uyg.kurum.ad = veri["kurum"]
        for k in veri["kullanicilar"]:
            uyg.kullanici_ekle(self._kullanici_olustur(k))
        kisiler = {k.tc_no: k for k in uyg.kullanicilar}

        for h in veri["hastaneler"]:
            hastane = Hastane(h["ad"], time.fromisoformat(h["acilis"]), time.fromisoformat(h["kapanis"]))
            uyg.kurum.hastane_ekle(hastane)
            for k in h["klinikler"]:
                klinik = Klinik(k["ad"])
                hastane.klinik_ekle(klinik)
                for s in k["hizmetler"]:
                    klinik.hizmet_ekle(self._hizmet_olustur(s))
                for tc in k["doktorlar"]:
                    klinik.doktor_ekle(kisiler[tc])

        for r in veri["randevular"]:
            hastane = uyg.kurum.hastane_bul(r["hastane"])
            klinik = hastane.klinik_bul(r["klinik"])
            hizmet = [s for s in klinik.hizmetler if s.ad == r["hizmet"]][0]
            uyg.sistem.randevu_yukle(Randevu(
                kisiler[r["hasta"]], hastane, klinik, kisiler[r["doktor"]], hizmet,
                datetime.fromisoformat(r["baslangic"]),
                RandevuDurumu[r["durum"]], r["odenen_tutar"]))
        return uyg

    def _kullanici_olustur(self, k: dict):
        tur = k["tur"]
        if tur == "Hasta":
            return Hasta(k["ad"], k["soyad"], k["tc_no"])
        if tur == "Yonetici":
            return Yonetici(k["ad"], k["soyad"], k["tc_no"])
        if tur == "Teknisyen":
            kisi = Teknisyen(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"], k["cihaz"])
        elif tur == "Hemsire":
            kisi = Hemsire(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"])
        else:
            kisi = Doktor(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"])
        for baslangic, bitis in k["musaitlik"]:
            kisi.musaitlik_yukle(datetime.fromisoformat(baslangic), datetime.fromisoformat(bitis))
        return kisi

    def _hizmet_olustur(self, s: dict):
        if s["tur"] == "Radyoloji":
            return Radyoloji(s["ad"], s["sure_dk"], s["taban_ucret"], s["cihaz_ucreti"])
        if s["tur"] == "Laboratuvar":
            return Laboratuvar(s["ad"], s["sure_dk"], s["taban_ucret"], s["tahlil_sayisi"])
        return Muayene(s["ad"], s["sure_dk"], s["taban_ucret"])
