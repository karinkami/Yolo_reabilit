import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Релоадер Flask держит два процесса — веб-камера часто «занята» во втором.
    use_reloader = os.environ.get("FLASK_USE_RELOADER", "").lower() in ("1", "true", "yes")
    app.run(debug=True, use_reloader=use_reloader)