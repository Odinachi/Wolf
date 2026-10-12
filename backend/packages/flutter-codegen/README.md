# wolf-flutter-codegen

Compiles a [Wolf](../../README.md) app schema into a Flutter project.

```python
from wolf_flutter import generate_project

project = generate_project(schema)  # schema: the AppSchema as a dict
for path, contents in project.files.items():
    ...
print(project.warnings)  # e.g. buttons pointing at deleted screens
```

The output contains `lib/` and `pubspec.yaml` but no platform folders. Run
`flutter create . --platforms=android,ios,web` in the output to add them.

Tests include a real `flutter analyze` of the generated code when the Flutter SDK is installed.
