#!/bin/bash

# Start nginx
nginx &

# Start kleinanzeigen app
cd kleinanzeigen-map
poetry run streamlit run app.py --server.port=8501 --server.address=0.0.0.0 