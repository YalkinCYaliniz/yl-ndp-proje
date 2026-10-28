"""Şifre güvenliği: şifre düz metin olarak saklanmaz, tuzlu özet (hash) tutulur."""
import hashlib
import hmac
import os


class Sifre:
    """Değiştirilemez şifre nesnesi. Sadece doğrulama yapar, şifreyi geri vermez."""

    TEKRAR = 20000
    MIN_UZUNLUK = 6

    def __init__(self, tuz: bytes, ozet: bytes):
        self._tuz = tuz
        self._ozet = ozet

    @classmethod
    def olustur(cls, duz_sifre: str) -> "Sifre":
        if len(duz_sifre) < cls.MIN_UZUNLUK:
            raise ValueError(f"Şifre en az {cls.MIN_UZUNLUK} karakter olmalıdır.")
        tuz = os.urandom(16)
        return cls(tuz, cls._ozetle(duz_sifre, tuz))

    @staticmethod
    def _ozetle(duz_sifre: str, tuz: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", duz_sifre.encode("utf-8"), tuz, Sifre.TEKRAR)

    def dogru_mu(self, duz_sifre: str) -> bool:
        return hmac.compare_digest(self._ozet, self._ozetle(duz_sifre, self._tuz))

    def sozluge(self) -> dict:
        return {"tuz": self._tuz.hex(), "ozet": self._ozet.hex()}

    @classmethod
    def sozlukten(cls, veri: dict) -> "Sifre":
        return cls(bytes.fromhex(veri["tuz"]), bytes.fromhex(veri["ozet"]))
