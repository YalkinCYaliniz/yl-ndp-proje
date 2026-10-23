"""Projeye özel hata sınıfları (kalıtım: hepsi SistemHatasi'ndan türer)."""


class SistemHatasi(Exception):
    """Tüm proje hatalarının ortak atası."""


class RandevuHatasi(SistemHatasi):
    """Çakışma, müsait olmayan saat, uyumsuz klinik/hizmet gibi randevu sorunları."""


class YetkiHatasi(SistemHatasi):
    """Rolün yapmaya yetkisi olmadığı işlemler."""


class BulunamadiHatasi(SistemHatasi):
    """Hastane veya klinik bulunamadığında."""
