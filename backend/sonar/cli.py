import threading
import webbrowser
import uvicorn
from sonar.api.app import create_app


def main() -> None:
    port = 8000
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
