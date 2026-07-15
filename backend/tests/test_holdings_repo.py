import csv
import io
import zipfile

from sonar.domain.holdings import Row
from sonar.market.us.thirteen_f import parse_13f_zip
from sonar.store.holdings_repo import HoldingsRepo


def _row(**overrides) -> Row:
    defaults = dict(
        accession="ACC1",
        cik="CIK1",
        filer_name="Acme Capital",
        cusip="123456789",
        issuer_name="Acme Corp",
        shares=100,
        value=1000,
        put_call="",
        amendment_type="",
    )
    defaults.update(overrides)
    return Row(**defaults)


def test_restatement_replaces_prior_rows(conn):
    repo = HoldingsRepo(conn)
    repo.ingest([_row(shares=100, value=1000)], quarter="2026Q1")
    repo.ingest(
        [_row(shares=999, value=9999, amendment_type="RESTATEMENT")], quarter="2026Q1"
    )

    holders = repo.holders_of("123456789", "2026Q1")
    assert len(holders) == 1
    assert holders[0].shares == 999
    assert holders[0].value == 9999


def test_new_holdings_appends(conn):
    repo = HoldingsRepo(conn)
    repo.ingest([_row(cusip="AAA111111")], quarter="2026Q1")
    repo.ingest(
        [_row(cusip="BBB222222", amendment_type="NEW HOLDINGS")], quarter="2026Q1"
    )

    holdings = repo.filer_holdings("CIK1", "2026Q1")
    assert len(holdings) == 2
    assert {h["cusip"] for h in holdings} == {"AAA111111", "BBB222222"}


def test_prune_keeps_last_n_quarters(conn):
    repo = HoldingsRepo(conn)
    repo.ingest([_row()], quarter="2025Q3")
    repo.ingest([_row()], quarter="2025Q4")
    repo.ingest([_row()], quarter="2026Q1")

    repo.prune(keep=2)

    assert repo.quarters() == ["2025Q4", "2026Q1"]
    assert repo.holders_of("123456789", "2025Q3") == []


def test_holders_of_includes_put_and_long_positions(conn):
    repo = HoldingsRepo(conn)
    repo.ingest(
        [
            _row(cik="CIK1", filer_name="Long Fund", shares=100, value=1000, put_call=""),
            _row(cik="CIK2", filer_name="Put Fund", shares=50, value=500, put_call="Put"),
        ],
        quarter="2026Q1",
    )

    holders = repo.holders_of("123456789", "2026Q1")
    assert len(holders) == 2
    by_filer = {h.filer_name: h for h in holders}
    assert by_filer["Long Fund"].put_call == ""
    assert by_filer["Put Fund"].put_call == "Put"


def test_trend_survives_prune(conn):
    repo = HoldingsRepo(conn)
    repo.ingest([_row(shares=100, value=1000)], quarter="2025Q3")
    repo.ingest([_row(shares=200, value=2000)], quarter="2025Q4")
    repo.ingest([_row(shares=300, value=3000)], quarter="2026Q1")

    repo.prune(keep=2)

    trend = repo.trend("123456789")
    assert [t["quarter"] for t in trend] == ["2025Q3", "2025Q4", "2026Q1"]
    assert trend[0]["total_shares"] == 100
    assert trend[0]["filer_count"] == 1


def _build_zip() -> bytes:
    cover_rows = [
        {
            "ACCESSION_NUMBER": "ACC1",
            "FILINGMANAGER_NAME": "Acme Capital",
            "AMENDMENTTYPE": "",
        }
    ]
    submission_rows = [{"ACCESSION_NUMBER": "ACC1", "CIK": "0001234567"}]
    infotable_rows = [
        {
            "ACCESSION_NUMBER": "ACC1",
            "NAMEOFISSUER": "Acme Corp",
            "CUSIP": "123456789",
            "VALUE": "1000",
            "SSHPRNAMT": "100",
            "PUTCALL": "",
        },
        {
            "ACCESSION_NUMBER": "ACC1",
            "NAMEOFISSUER": "Beta Inc",
            "CUSIP": "987654321",
            "VALUE": "2000",
            "SSHPRNAMT": "200",
            "PUTCALL": "Call",
        },
    ]

    def _tsv(rows: list[dict]) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("COVERPAGE.tsv", _tsv(cover_rows))
        z.writestr("SUBMISSION.tsv", _tsv(submission_rows))
        z.writestr("INFOTABLE.tsv", _tsv(infotable_rows))
    return buf.getvalue()


def test_parse_13f_zip_joins_filer_name_and_cik():
    rows = list(parse_13f_zip(_build_zip()))

    assert len(rows) == 2
    first = rows[0]
    assert first.accession == "ACC1"
    assert first.cik == "0001234567"
    assert first.filer_name == "Acme Capital"
    assert first.cusip == "123456789"
    assert first.issuer_name == "Acme Corp"
    assert first.shares == 100
    assert first.value == 1000
    assert first.put_call == ""

    second = rows[1]
    assert second.put_call == "Call"
    assert second.cusip == "987654321"
