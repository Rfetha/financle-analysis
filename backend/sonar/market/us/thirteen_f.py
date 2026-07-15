"""SEC DERA 13F structured-data ZIP parser. Yalnız byte'ları parse eder — indirme
(dosya adı keşfi dahil) B2'nin (ingest orchestration) işi.

Gerçek şema (spike B0 ile doğrulandı): filer NAME COVERPAGE.tsv'de, CIK SUBMISSION.tsv'de.
"""

import csv
import io
import zipfile
from typing import Iterator

from sonar.domain.holdings import Row

DERA_INDEX_URL = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
# Why: dosya adları tarih-aralıklı (örn. "01mar2026-31may2026_form13f.zip"); güncel adı
# ingest orchestration (Task B2) index sayfasından keşfeder.
DERA_BASE = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets"


def _table(z: zipfile.ZipFile, name: str) -> list[dict]:
    with z.open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter="\t"))


def parse_13f_zip(data: bytes) -> Iterator[Row]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        cover = {
            row["ACCESSION_NUMBER"]: (row["FILINGMANAGER_NAME"], row["AMENDMENTTYPE"])
            for row in _table(z, "COVERPAGE.tsv")
        }
        ciks = {row["ACCESSION_NUMBER"]: row["CIK"] for row in _table(z, "SUBMISSION.tsv")}

        for row in _table(z, "INFOTABLE.tsv"):
            acc = row["ACCESSION_NUMBER"]
            filer_name, amendment_type = cover.get(acc, ("?", ""))
            yield Row(
                accession=acc,
                cik=ciks.get(acc, ""),
                filer_name=filer_name,
                cusip=row["CUSIP"].strip().upper(),
                issuer_name=row["NAMEOFISSUER"].strip(),
                shares=int(float(row["SSHPRNAMT"] or 0)),
                value=int(float(row["VALUE"] or 0)),
                put_call=(row["PUTCALL"] or "").strip(),
                amendment_type=amendment_type,
            )
