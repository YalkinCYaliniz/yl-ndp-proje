"""Doktor veya klinik adına göre arama ve en yakın boş randevu."""
from datetime import datetime

_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def sadelestir(metin: str) -> str:
    """Türkçe karakterleri ve büyük/küçük harf farkını yok sayar: 'Ayşe' -> 'ayse'."""
    return metin.translate(_TR).lower().strip()


class AramaSonucu:
    """Tek bir arama satırı: nerede, hangi doktor, hangi hizmet, en yakın boş saat."""

    def __init__(self, hastane_sira, hastane, klinik_sira, klinik,
                 doktor_sira, doktor, hizmet_sira, hizmet, en_yakin):
        self.hastane_sira, self.hastane = hastane_sira, hastane
        self.klinik_sira, self.klinik = klinik_sira, klinik
        self.doktor_sira, self.doktor = doktor_sira, doktor
        self.hizmet_sira, self.hizmet = hizmet_sira, hizmet
        self.en_yakin = en_yakin            # en yakın boş saat (Slot); yoksa None


class Arama:
    def __init__(self, uygulama):
        self._kurum = uygulama.kurum
        self._sistem = uygulama.sistem

    def ara(self, sorgu: str, sonra=None, limit: int = 60) -> list:
        """Doktor, uzmanlık, klinik veya hastane adında geçenleri bulur; en yakın randevuya göre sıralar."""
        aranan = sadelestir(sorgu)
        if not aranan:
            return []
        sonra = sonra or datetime.now()
        sonuclar = []
        for hi, hastane in enumerate(self._kurum.hastaneler):
            for ki, klinik in enumerate(hastane.klinikler):
                for di, doktor in enumerate(klinik.doktorlar):
                    metin = " ".join(sadelestir(m) for m in
                                     (doktor.tam_ad, doktor.uzmanlik, klinik.ad, hastane.ad))
                    hizmetler = doktor.sunulan_hizmetler(klinik)
                    if aranan not in metin or not hizmetler:
                        continue
                    sonuclar.append(self._sonuc(hi, hastane, ki, klinik, di, doktor, hizmetler, sonra))
        sonuclar.sort(key=lambda s: (s.en_yakin is None, s.en_yakin.baslangic if s.en_yakin else datetime.max))
        return sonuclar[:limit]

    def _sonuc(self, hi, hastane, ki, klinik, di, doktor, hizmetler, sonra) -> AramaSonucu:
        """Doktorun verdiği hizmetler arasında en erken boş saati bulur."""
        en_iyi = (0, hizmetler[0], None)
        for si, hizmet in enumerate(hizmetler):
            slot = self._sistem.en_yakin_bos(hastane, doktor, hizmet, sonra)
            if slot and (en_iyi[2] is None or slot.baslangic < en_iyi[2].baslangic):
                en_iyi = (si, hizmet, slot)
        return AramaSonucu(hi, hastane, ki, klinik, di, doktor, en_iyi[0], en_iyi[1], en_iyi[2])
