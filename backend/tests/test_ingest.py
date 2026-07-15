import csv
import io
import zipfile

from sonar.market.us.cusip import CusipMap
from sonar.store.holdings_repo import HoldingsRepo
from sonar.store.ingest import Ingester

_URL_Q1 = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets/01mar2026-31may2026_form13f.zip"
_URL_Q4 = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets/01dec2025-28feb2026_form13f.zip"

_INDEX_HTML = f"""
<a href="{_URL_Q1.replace("https://www.sec.gov", "")}">latest</a>
<a href="{_URL_Q4.replace("https://www.sec.gov", "")}">prior</a>
"""

_TICKERS = {"0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"}}


def _tsv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _build_zip(cusip_issuer: dict[str, str]) -> bytes:
    cover_rows = [{"ACCESSION_NUMBER": "ACC1", "FILINGMANAGER_NAME": "Acme Capital", "AMENDMENTTYPE": ""}]
    submission_rows = [{"ACCESSION_NUMBER": "ACC1", "CIK": "0001234567"}]
    infotable_rows = [
        {
            "ACCESSION_NUMBER": "ACC1",
            "NAMEOFISSUER": issuer,
            "CUSIP": cusip,
            "VALUE": "1000",
            "SSHPRNAMT": "100",
            "PUTCALL": "",
        }
        for cusip, issuer in cusip_issuer.items()
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("COVERPAGE.tsv", _tsv(cover_rows))
        z.writestr("SUBMISSION.tsv", _tsv(submission_rows))
        z.writestr("INFOTABLE.tsv", _tsv(infotable_rows))
    return buf.getvalue()


class _FakeHttp:
    def __init__(self, blobs: dict[str, bytes]) -> None:
        self._blobs = blobs

    def get_bytes(self, url: str) -> bytes:
        return self._blobs[url]


class _BoomHttp:
    def get_bytes(self, url: str) -> bytes:
        raise RuntimeError("SEC 503")


async def test_ingest_marks_ready_writes_rows_and_filters_unresolved_cusips(conn):
    blob_q1 = _build_zip({"67066G104": "NVIDIA CORPORATION", "999999999": "OBSCURE HOLDINGS XYZ"})
    blob_q4 = _build_zip({"67066G104": "NVIDIA CORPORATION"})
    http = _FakeHttp({_URL_Q1: blob_q1, _URL_Q4: blob_q4})
    repo = HoldingsRepo(conn)
    cusip_map = CusipMap(conn)

    ing = Ingester(repo, cusip_map, http, _TICKERS, fetch_index=lambda: _INDEX_HTML)
    assert ing.state.status == "idle"

    await ing.run()

    assert ing.state.status == "ready"
    assert ing.state.progress == 1.0
    assert cusip_map.ticker_for("67066G104") == "NVDA"
    assert cusip_map.ticker_for("999999999") is None  # obscure isim eşleşmedi

    holders = repo.holders_of("67066G104", "01mar2026-31may2026")
    assert len(holders) == 1
    assert holders[0].shares == 100

    # spike B0 kararı: ticker'a çözülemeyen (obscure) satırlar filtrelenir.
    assert repo.holders_of("999999999", "01mar2026-31may2026") == []
    assert set(repo.quarters()) == {"01dec2025-28feb2026", "01mar2026-31may2026"}


async def test_ingest_error_is_visible_not_silent(conn):
    ing = Ingester(
        HoldingsRepo(conn), CusipMap(conn), _BoomHttp(), _TICKERS, fetch_index=lambda: _INDEX_HTML
    )

    await ing.run()

    assert ing.state.status == "error"
    assert "SEC 503" in ing.state.message  # sessiz düşme yok
