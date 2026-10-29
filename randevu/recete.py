"""Doktorun yazdığı reçete: ilaç listesi ve hasta notu."""
from datetime import datetime


class Recete:
    def __init__(self, ilaclar, doktor_notu: str = "", tarih=None):
        temiz = [i.strip() for i in ilaclar if i and i.strip()]
        if not temiz and not doktor_notu.strip():
            raise ValueError("Reçetede en az bir ilaç veya not olmalıdır.")
        self._ilaclar = temiz                  # Kapsülleme: dışarıdan liste değiştirilemez
        self.doktor_notu = doktor_notu.strip()
        self.tarih = tarih or datetime.now()

    @property
    def ilaclar(self) -> tuple:
        return tuple(self._ilaclar)

    def sozluge(self) -> dict:
        return {"ilaclar": self._ilaclar, "doktor_notu": self.doktor_notu, "tarih": self.tarih.isoformat()}

    @classmethod
    def sozlukten(cls, veri: dict) -> "Recete":
        return cls(veri["ilaclar"], veri.get("doktor_notu", veri.get("not", "")), datetime.fromisoformat(veri["tarih"]))
