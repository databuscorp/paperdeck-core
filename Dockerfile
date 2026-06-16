FROM python:3.11-slim

# System dependencies for rendering libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    # cairosvg (SVG→PNG conversion)
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # matplotlib fonts
    fonts-dejavu-core \
    # psycopg2
    libpq-dev \
    gcc \
    # cleanup
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir cairosvg

# Copy project
COPY . .

# Create media directory
RUN mkdir -p media/rendered

# Collect static files
ENV DJANGO_SETTINGS_MODULE=paperdeck.settings
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

CMD ["gunicorn", "paperdeck.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-"]
