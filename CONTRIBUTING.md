# Contributing

Test catalog parsing changes with synthetic fixtures. Cover filename and Markdown changes with output assertions, and keep network calls out of tests.

```bash
python -m unittest discover -s tests -v
```

Do not commit provider keys, private endpoints, or account data.
