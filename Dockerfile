FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY data/ data/

RUN pip install --no-cache-dir -e . google-generativeai anthropic google-cloud-firestore

ENV GOOGLE_CLOUD_PROJECT=zeta-matrix-483109-u9
ENV FIRESTORE_DATABASE=wikirace

EXPOSE 8080

CMD ["python", "-c", "from wiki_race.web import app; app.run(host='0.0.0.0', port=8080, threaded=True)"]
