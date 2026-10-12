import shutil
import subprocess
from pathlib import Path

import pytest

from wolf_flutter import generate_project
from wolf_flutter import dart
from tests.fixtures import sample_schema


def test_generates_expected_files():
    project = generate_project(sample_schema())
    assert set(project.files) >= {
        "pubspec.yaml", "lib/main.dart", "lib/theme.dart", "lib/widgets.dart",
        "lib/screens/home_screen.dart", "lib/screens/plant_detail_screen.dart",
        "lib/models/plant.dart", "lib/data/backend.dart", "README.md",
    }
    assert project.warnings == []


def test_pubspec_reflects_config():
    pubspec = generate_project(sample_schema()).files["pubspec.yaml"]
    assert "name: plantpal" in pubspec
    assert "version: 1.2.0+3" in pubspec
    assert "supabase_flutter" in pubspec and "url_launcher" in pubspec and "google_fonts" in pubspec


def test_strings_are_escaped():
    home = generate_project(sample_schema()).files["lib/screens/home_screen.dart"]
    assert r"'Good morning, Ada\'s \"plants\" cost \$5'".replace('\\"', '"') in home


def test_tabs_and_navigation():
    main = generate_project(sample_schema()).files["lib/main.dart"]
    assert "class AppShell" in main and "NavigationBar(" in main
    assert "Icons.home" in main
    stack = generate_project(sample_schema(nav="stack")).files["lib/main.dart"]
    assert "AppShell" not in stack and "initialRoute: HomeScreen.routeName" in stack


def test_models_handle_types_and_reserved_words():
    model = generate_project(sample_schema()).files["lib/models/plant.dart"]
    assert "final int? waterEveryDays;" in model
    assert "(json['price'] as num?)?.toDouble()" in model
    assert "DateTime.parse(json['lastWatered'] as String)" in model
    assert "final String? classValue;" in model


def test_backends():
    for provider, marker in [("supabase", "Supabase.initialize"), ("rest", "http.get"), ("firebase", "Firebase.initializeApp")]:
        files = generate_project(sample_schema(provider=provider)).files
        assert marker in files["lib/data/backend.dart"]
    none = generate_project(sample_schema(provider="none")).files
    assert "lib/data/backend.dart" not in none
    assert "initBackend" not in none["lib/main.dart"]


def test_broken_references_become_warnings():
    schema = sample_schema()
    schema["screens"][0]["root"]["children"].append(
        {"id": "x", "type": "Button", "props": {"label": "?"}, "style": {}, "children": [], "onTap": {"type": "navigate", "screenId": "gone"}}
    )
    schema["screens"][0]["root"]["children"].append({"id": "y", "type": "Blink", "props": {}, "style": {}, "children": []})
    project = generate_project(schema)
    assert len(project.warnings) == 2


def test_dart_helpers():
    assert dart.color("#ff0000") == "Color(0xFFFF0000)"
    assert dart.color("red") is None
    assert dart.icon("class") == "Icons.class_"
    assert dart.icon("not valid!") == "Icons.help_outline"
    assert dart.edge_insets([1, 2, 3, 4]) == "EdgeInsets.fromLTRB(4.0, 1.0, 2.0, 3.0)"


@pytest.mark.skipif(shutil.which("flutter") is None, reason="Flutter SDK not installed")
@pytest.mark.parametrize("provider,nav", [("supabase", "tabs"), ("none", "stack")])
def test_generated_project_passes_flutter_analyze(tmp_path: Path, provider, nav):
    """The real check: the output must compile. Needs the Flutter SDK and network for pub get."""
    project = generate_project(sample_schema(provider=provider, nav=nav))
    for rel, content in project.files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    get = subprocess.run(["flutter", "pub", "get"], cwd=tmp_path, capture_output=True, text=True, timeout=600)
    assert get.returncode == 0, get.stdout + get.stderr
    result = subprocess.run(["flutter", "analyze", "--no-fatal-infos", "--no-fatal-warnings"], cwd=tmp_path, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stdout + result.stderr
