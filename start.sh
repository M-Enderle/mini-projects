#!/bin/bash

# Start nginx
nginx &

# Start fuel-tracker app
cd fuel-tracker
poetry run python app.py &

# Start recipe-book app
cd ../recipe-book
poetry run python app.py &

# Start kleinanzeigen app (keep as foreground process)
cd ../kleinanzeigen-map
poetry run streamlit run app.py --server.port=8501 --server.address=0.0.0.0 