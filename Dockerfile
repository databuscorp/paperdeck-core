# Python 3.13 to match the version the app is developed and CI-tested against.
FROM python:3.13-slim

# System dependencies for the rendering libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # cairosvg (SVG→PNG). Required — without libcairo2, cairocffi raises OSError (not
    # ImportError) and PNG export and PDF diagram embedding are both dead.
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # rdkit (organic chemistry structures). Its manylinux wheel vendors boost and its
    # own cairo, but NOT these X11/fontconfig libs — and python:*-slim doesn't ship
    # them. Without them `from rdkit import Chem` raises ImportError, which the
    # chemistry renderer CATCHES: molecules would silently fall back to the crude
    # SMILES-as-text renderer and the app would look perfectly healthy.
    # Verified against rdkit 2026.3.3 cp313. Guarded by diagrams/tests/test_deps.py.
    libxrender1 \
    libxext6 \
    libx11-6 \
    libfontconfig1 \
    # matplotlib fonts
    fonts-dejavu-core \
    # psycopg2
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# cairosvg and rdkit are in requirements.txt and are REQUIRED, not optional — a broken
# install must fail the build here rather than degrade quietly in production.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Prove the render stack is not just installed but actually USABLE. Both of these fail
# soft at runtime (ImportError / OSError swallowed by a fallback), so without this
# assert a missing native library ships silently and shows up as bad diagrams.
RUN python -c "\
import cairosvg; \
from rdkit import Chem; \
assert Chem.MolFromSmiles('CC(=O)Oc1ccccc1') is not None; \
print('render deps OK: cairosvg', cairosvg.__version__, '+ rdkit')"

COPY . .

RUN mkdir -p media/rendered

ENV DJANGO_SETTINGS_MODULE=paperdeck.settings
ENV PYTHONUNBUFFERED=1
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

# entrypoint runs migrations, then execs gunicorn.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
