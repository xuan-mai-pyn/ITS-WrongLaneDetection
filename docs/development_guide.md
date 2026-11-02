# Development guide

## Local setup

Use Python 3.10+ and install `requirements.txt` in a virtual environment. Copy `.env.example` to `.env`; configure a local weights file and, when needed, a JSON lane configuration. Start the API with `python scripts\run_backend.py`. Swagger is available at `/docs`.

## Database and tests

Run `python scripts\setup_database.py` to initialize SQLite. Run `python -m unittest discover -s tests -v` for the standard-library test suite. Tests use temporary directories and do not require model weights.

## Extending the pipeline

- Keep API transport schemas separate from domain and processing logic.
- Add camera-specific lane geometry/rules to external configuration; do not infer them from object detection.
- Preserve explicit task failure and progress information.
- Do not record a violation unless a configured rule and frame-confirmation threshold are both satisfied.
- Keep large/private videos, datasets, model weights, local databases, and `.env` files out of version control.
