"""Ödeme yöntemleri: soyut Odeme + alt sınıflar (soyutlama, kalıtım, çok biçimlilik)."""
from abc import ABC, abstractmethod


class Odeme(ABC):
    """Her ödeme yöntemi hastanın ödeyeceği toplamı kendi kuralıyla hesaplar."""

    @abstractmethod
    def yontem(self) -> str:
        """Ödeme yönteminin adı."""

    @abstractmethod
    def toplam_hesapla(self, tutar: float) -> float:
        """Hizmet ücretinden hastanın ödeyeceği tutarı hesaplar."""


class NakitOdeme(Odeme):
    def yontem(self) -> str:
        return "Nakit"

    def toplam_hesapla(self, tutar: float) -> float:
        return tutar


class KartOdeme(Odeme):
    """Kartta komisyon vardır, taksit arttıkça artar."""

    def __init__(self, taksit: int = 1):
        self._taksit = taksit

    def yontem(self) -> str:
        return f"Kredi Kartı ({self._taksit} taksit)"

    def toplam_hesapla(self, tutar: float) -> float:
        komisyon = 0.02 + 0.01 * (self._taksit - 1)
        return tutar * (1 + komisyon)


class SigortaOdeme(Odeme):
    """Sigorta bedelin bir kısmını karşılar, hasta katılım payını öder."""

    def __init__(self, katilim_orani: float = 0.2):
        self._katilim_orani = katilim_orani

    def yontem(self) -> str:
        return "Sigorta"

    def toplam_hesapla(self, tutar: float) -> float:
        return tutar * self._katilim_orani
