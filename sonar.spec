# sonar.spec
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("backend/sonar/web/static", "sonar/web/static")]
hiddenimports = (
    collect_submodules("yfinance")
    + collect_submodules("uvicorn")
    + collect_submodules("fastapi")
    + collect_submodules("starlette")
    + collect_submodules("anyio")
    + collect_submodules("multipart")
    + ["anyio._backends._asyncio", "anyio._backends._trio"]
)

a = Analysis(
    ["backend/sonar/cli.py"],
    pathex=["backend"],
    datas=datas,
    hiddenimports=hiddenimports,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="sonar", console=True)
