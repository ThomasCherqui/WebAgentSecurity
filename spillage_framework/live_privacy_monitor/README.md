# Live Privacy Monitor

Prototype local qui capture les cibles Chrome via CDP, affiche le flux, produit des verdicts
candidats avec Ollama, puis réutilise le `llm_council` existant.

## Installation et lancement

```bash
cd spillage_framework/live_privacy_monitor
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Ouvrir `http://127.0.0.1:8000`, puis cliquer sur **Ouvrir le profil Chrome**. Au premier
lancement seulement, installer l'extension Claude et s'y connecter. Le profil persiste dans
`.chrome-profile/`.

Si Chrome n'est pas détecté :

```bash
CHROME_BINARY=/chemin/vers/chrome .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Configuration Ollama optionnelle :

```bash
export COUNCIL_CANDIDATE_MODELS=gemma4:latest,mistral-small:latest
export COUNCIL_REVIEWER_MODELS=gpt-oss:20b
export COUNCIL_CHAIRMAN_MODEL=gemma4:latest
```

Le bouton **Tester sans Ollama** valide rapidement tout le câblage. La capture tente les cibles
`page`, `service_worker` et `background_page` exposées par Chrome. La présence du trafic interne
de l'extension Claude doit être confirmée expérimentalement.
