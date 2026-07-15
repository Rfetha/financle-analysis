import os

from sonar.config import _load_dotenv


def test_load_dotenv_fills_missing_strips_quotes_skips_comments(tmp_path, monkeypatch):
    monkeypatch.setenv("SONAR_T_EXISTING", "real")  # gerçek env
    env = tmp_path / ".env"
    env.write_text(
        '# yorum satiri\n'
        "SONAR_T_NEW=hello\n"
        'SONAR_T_QUOTED="a b c"\n'
        "SONAR_T_EXISTING=fromfile\n"
        "\n"
        "COMMENTSIZ_ESITSIZ_SATIR\n",
        encoding="utf-8",
    )
    try:
        _load_dotenv(env)
        assert os.environ["SONAR_T_NEW"] == "hello"          # eksik → dolduruldu
        assert os.environ["SONAR_T_QUOTED"] == "a b c"       # tırnak sıyrıldı
        assert os.environ["SONAR_T_EXISTING"] == "real"      # gerçek env EZİLMEDİ
        assert "COMMENTSIZ_ESITSIZ_SATIR" not in os.environ  # '=' yok → atlandı
    finally:
        monkeypatch.delenv("SONAR_T_NEW", raising=False)
        monkeypatch.delenv("SONAR_T_QUOTED", raising=False)


def test_load_dotenv_missing_file_is_noop(tmp_path):
    _load_dotenv(tmp_path / "yok.env")  # patlamamalı
