"""開發伺服器進入點：`flask run` 或 `python run.py`。"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
