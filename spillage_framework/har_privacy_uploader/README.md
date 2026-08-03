# HAR Privacy Uploader

Interface locale : le HAR est analysé dans le navigateur et n'est jamais téléversé brut.
Seuls les événements cochés dans la prévisualisation sont envoyés à FastAPI.

```bash
python3 serve.py
```

Ouvrir `http://127.0.0.1:8787`, sélectionner le HAR, renseigner l'URL ngrok et vérifier la
prévisualisation avant envoi.
