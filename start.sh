#!/bin/bash

# Start fuel-tracker app
cd fuel-tracker
poetry run python app.py &

# Start recipe-book app
cd ../recipe-book
poetry run python app.py &

# Wait for recipe-book to be ready on 127.0.0.1:5002 (max ~30s)
ATTEMPTS=0
until (echo > /dev/tcp/127.0.0.1/5002) >/dev/null 2>&1 || [ $ATTEMPTS -ge 60 ]; do
  ATTEMPTS=$((ATTEMPTS+1))
  sleep 0.5
done

# Start nginx after backends are up
nginx &

# Start kleinanzeigen app (keep as foreground process)
cd ../kleinanzeigen-map
poetry run streamlit run app.py --server.port=8501 --server.address=0.0.0.0 