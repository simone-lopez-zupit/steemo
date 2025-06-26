#!/bin/bash

echo "🚀 Avvio del server FastAPI..."

uvicorn app.main:app --host 0.0.0.0 --port 80