# Contributing

Thanks for improving Personal Photo Toolkit.

## Basic workflow

1. Fork the repository.
2. Create a feature branch:

```bash
git checkout -b feature/my-improvement
```

3. Make a focused change.
4. Test only on **copies** of media files.
5. Commit:

```bash
git add .
git commit -m "Improve metadata detection"
```

6. Push and open a pull request.

## Safety rules

Please keep these rules when contributing:

- Never delete source media by default.
- Prefer copy + review workflows.
- Exact duplicate removal must be content-based.
- Near-duplicate removal must require review unless the user explicitly opts in.
- Uncertain AI classifications should go to `Review`.
- Personal reference photos must never be committed.
- Do not include Google Takeout archives in the repository.

## Code organization

Keep UI code in:

```text
photo_toolkit/app.py
```

Keep processing logic in separate modules:

```text
sorter.py
dates.py
trip_filter.py
cleaner.py
utils.py
```

This makes it easier to replace the UI later without rewriting the core logic.

## Testing

A future contributor can add automated tests under:

```text
tests/
```

Useful tests include:

- filename date extraction
- Google Takeout sidecar parsing
- duplicate detection
- destination collision handling
- category routing
- cancellation handling

## Pull requests

A pull request should explain:

- what changed
- why it changed
- operating systems tested
- whether dependencies changed
- how the change was tested

Do not attach personal photos to issues unless necessary and intentionally shared.
