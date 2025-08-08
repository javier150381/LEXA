# Classifier Usage

The classifier provides basic suggestions for case categories based on a text
description.  It is intended to assist users in choosing the appropriate area
when generating a demand.

## Examples

```
>>> from src.classifier.suggest_type import suggest_type
>>> suggest_type("La empresa no pagó mi salario tras el despido")
['Laboral']
>>> suggest_type("Busco la custodia de mi hijo luego del divorcio")
['Familiar']
```

## Limitations

- The classifier uses simple keyword matching and does not understand context.
- Categories must already exist as areas in the application to be selected
  automatically.
- Suggestions are heuristics only; legal expertise is required to confirm the
  appropriate classification.
