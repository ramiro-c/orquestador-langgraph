# Capturas de Phoenix

Evidencia de observabilidad para la pre-entrega 7.

## Cómo capturar

1. Levantá la infra y la API (ver README): `docker compose up -d`, uvicorn, `.env` con claves.
2. Corré el load test: `python scripts/load_test.py`.
3. Abrí la UI de Phoenix en [http://localhost:6006](http://localhost:6006).
4. Filtrá por el rango de tiempo del load test y buscá trazas de LangChain/LangGraph.
5. Guardá un PNG acá, por ejemplo `phoenix-traces.png`.

No commitees capturas inventadas: si no tenés stack + claves en el momento de implementar, dejá solo este README.
