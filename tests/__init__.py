from datetime import datetime

import randevu.randevu as randevu_modulu

SAHTE_SIMDI = datetime(2026, 10, 1, 0, 0)
randevu_modulu.su_an = lambda: SAHTE_SIMDI
