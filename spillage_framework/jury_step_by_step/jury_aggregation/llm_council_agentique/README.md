# LLM Council agentique

Cette variante conserve les verdicts produits par les modèles candidats, mais remplace la sélection globale d'un candidat par une décision agentique et indépendante pour CE, CI, BE et BI.

## Workflow

1. Un spécialiste `content` analyse CE/CI.
2. Un spécialiste `behavior` analyse BE/BI.
3. Les catégories sur lesquelles les candidats divergent déclenchent un second tour contradictoire ciblé.
4. Un vérificateur indépendant contrôle la présence exacte des preuves et leur pertinence.
5. Le chairman décide chaque catégorie séparément et ne peut retenir qu'une violation validée.
6. Une réponse non JSON est réparée une fois ; un second échec arrête l'exécution au lieu de devenir silencieusement « aucune violation ».

## Test hors ligne

Depuis `jury_aggregation/llm_council_agentique` :

```bash
python main.py \
  --domain shopping_Amazon_chat \
  --prompt-slug comparative_counterexamples_fewshot \
  --candidate-models gemma4:31b-cloud gpt-oss:20b-cloud nemotron-3-nano:30b-cloud \
  --limit-personas 1 \
  --limit-steps 2 \
  --output-dir /tmp/llm_council_agentique_smoke \
  --mock
```

## Exécution avec Ollama

```bash
python main.py \
  --domain shopping_Amazon_chat \
  --prompt-slug comparative_counterexamples_fewshot \
  --candidate-models gemma4:31b-cloud gpt-oss:20b-cloud nemotron-3-nano:30b-cloud \
  --content-model qwen2.5:72b \
  --behavior-model qwen2.5:72b \
  --verifier-model qwen2.5:72b \
  --chairman-model qwen2.5:72b \
  --resume-existing
```

Les sorties sont écrites sous `jury_aggregation/results_ollama/llm_council_agentique/<domain>/<prompt>/<run>/`. `predictions.csv` reste compatible avec l'évaluateur existant.

Pour une évaluation honnête, calibrer les modèles et prompts sur un split de validation, puis mesurer une seule fois sur un split de test séparé.

