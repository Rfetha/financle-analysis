"""Big Players (13F) değer nesneleri. Spike B0 ile doğrulanmış alanlar."""

from dataclasses import dataclass

from sonar.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Row:
    """13F INFOTABLE+SUBMISSION+COVERPAGE join'inden tek ham pozisyon (parse çıktısı)."""

    accession: str
    cik: str
    filer_name: str      # COVERPAGE.FILINGMANAGER_NAME (SUBMISSION'da DEĞİL — spike B0)
    cusip: str
    issuer_name: str     # INFOTABLE.NAMEOFISSUER (her satırda dolu → gösterim CUSIP'e takılmaz)
    shares: int          # SSHPRNAMT
    value: int           # VALUE (dolar; 2023 kural sonrası bin-dolar değil)
    put_call: str        # '' = long · 'Put' · 'Call'
    amendment_type: str  # '' | 'RESTATEMENT' | 'NEW HOLDINGS' (COVERPAGE)


@dataclass(frozen=True, slots=True)
class HolderPosition:
    """Bir CUSIP'te tek filer'ın pozisyonu (depo sorgusu çıktısı)."""

    cik: str
    filer_name: str
    shares: int
    value: int
    put_call: str


@dataclass(frozen=True, slots=True)
class ShortInterest:
    symbol: Symbol
    shares_short: int
    days_to_cover: float | None
    as_of: str
    source: str
