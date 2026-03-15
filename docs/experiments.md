# Experiment Layer

## Purpose
Experiments are the first-class research unit above individual indicators.

## Hierarchy
- indicator -> source truth
- family -> interpretation group
- variant -> concrete reproducible strategy rules
- run -> one execution over one matrix cell

## Rule
Do not rank only indicator slugs. Rank experiment variants first, then aggregate upward.

## Layout
- `experiments/families/<family>/family.yaml`
- `experiments/variants/<experiment-slug>/experiment.yaml`
- `experiments/variants/<experiment-slug>/logic.py`
- `experiments/combinations/<experiment-slug>/experiment.yaml`
- `experiments/combinations/<experiment-slug>/logic.py`
- `experiments/registry/experiments.csv`

## CLI
- `tvir experiment <slug> ...`
- `tvir experiment-batch --status active ...`
