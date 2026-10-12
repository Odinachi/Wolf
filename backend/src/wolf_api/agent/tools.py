"""Schema-editing tools for the AI agent.

Each tool validates its input against the live schema (unknown ids, children on non-containers,
unknown props) and then mutates the schema in place. Errors are returned to the model as
tool errors so it can correct itself. Tool input schemas are generated from the pydantic models
below, so what the model sees and what we validate can't drift apart.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from functools import cache
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .. import config

HEX = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
FRAME_WIDTH, FRAME_GAP = 390, 120


@cache
def catalog() -> dict[str, Any]:
    """The component catalog exported from web/packages/schema (catalog.json)."""
    return json.loads(config.CATALOG_PATH.read_text())


def new_id() -> str:
    return str(uuid.uuid4())


class ToolError(Exception):
    """An invalid call. The message is returned to the model so it can fix and retry."""


# ─── Lookups ─────────────────────────────────────────────────────────────────


def find_screen(schema: dict, screen_id: str) -> dict:
    for s in schema["screens"]:
        if s["id"] == screen_id:
            return s
    known = ", ".join(f"{s['name']} ({s['id']})" for s in schema["screens"]) or "none"
    raise ToolError(f"Unknown screen_id '{screen_id}'. Screens: {known}")


def find_node(node: dict, node_id: str) -> dict | None:
    if node["id"] == node_id:
        return node
    for child in node.get("children", []):
        found = find_node(child, node_id)
        if found:
            return found
    return None


def find_parent(node: dict, node_id: str) -> tuple[dict, int] | None:
    for i, child in enumerate(node.get("children", [])):
        if child["id"] == node_id:
            return node, i
        found = find_parent(child, node_id)
        if found:
            return found
    return None


def get_node(screen: dict, node_id: str) -> dict:
    node = find_node(screen["root"], node_id)
    if not node:
        raise ToolError(f"Component '{node_id}' is not on screen '{screen['name']}'.")
    return node


def find_model(schema: dict, model_id: str) -> dict:
    for m in schema["dataModels"]:
        if m["id"] == model_id:
            return m
    known = ", ".join(f"{m['name']} ({m['id']})" for m in schema["dataModels"]) or "none"
    raise ToolError(f"Unknown model_id '{model_id}'. Data models: {known}")


def is_container(kind: str) -> bool:
    return bool(catalog().get(kind, {}).get("container"))


# ─── Input shapes ────────────────────────────────────────────────────────────

ComponentType = Literal[
    "Column", "Row", "Stack", "Container", "Card", "ListView", "Grid", "Spacer", "Divider",
    "Text", "Image", "Icon", "Avatar", "Chip", "ListTile", "ProgressBar",
    "Button", "IconButton", "TextField", "Switch", "Checkbox", "Slider", "AppBar",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _color(v: str | None) -> str | None:
    if v is not None and not HEX.match(v):
        raise ValueError(f"'{v}' is not a hex color like #6750A4")
    return v


class StyleSpec(Strict):
    """Visual properties in logical pixels. Omit anything you don't need."""

    padding: float | list[float] | None = Field(None, description="All sides, or [top, right, bottom, left].")
    margin: float | list[float] | None = None
    width: float | Literal["fill"] | None = Field(None, description="'fill' stretches to the parent's width.")
    height: float | None = None
    backgroundColor: str | None = None
    color: str | None = Field(None, description="Text or icon color.")
    fontSize: float | None = None
    fontWeight: Literal[400, 500, 600, 700, 800] | None = None
    textAlign: Literal["left", "center", "right"] | None = None
    borderRadius: float | None = None
    borderColor: str | None = None
    borderWidth: float | None = None
    elevation: float | None = None
    gap: float | None = Field(None, description="Space between children (Row, Column, Card, Container, ListView, Grid).")
    mainAxisAlignment: Literal["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly"] | None = None
    crossAxisAlignment: Literal["start", "center", "end", "stretch"] | None = None
    expand: bool | None = Field(None, description="Fill the remaining space inside a Row or Column.")

    @field_validator("backgroundColor", "color", "borderColor")
    @classmethod
    def _colors(cls, v):
        return _color(v)

    @field_validator("padding", "margin")
    @classmethod
    def _sides(cls, v):
        if isinstance(v, list) and len(v) != 4:
            raise ValueError("use one number or exactly [top, right, bottom, left]")
        return v


class ActionSpec(Strict):
    type: Literal["navigate", "back", "openUrl", "snackbar"]
    screenId: str | None = Field(None, description="For navigate.")
    url: str | None = Field(None, description="For openUrl.")
    message: str | None = Field(None, description="For snackbar.")


class ComponentSpec(Strict):
    type: ComponentType
    name: str | None = Field(None, description="Layer name shown in the editor, e.g. 'Hero title'.")
    props: dict[str, Any] = Field(default_factory=dict, description="Component props; see the component list in the system prompt.")
    style: StyleSpec = Field(default_factory=StyleSpec)
    on_tap: ActionSpec | None = None
    children: list["ComponentSpec"] = Field(default_factory=list, description="Only for container components.")


class FieldSpec(Strict):
    name: str = Field(description="camelCase field name.")
    type: Literal["string", "int", "double", "bool", "datetime", "image", "reference"]
    required: bool = False
    reference_model_id: str | None = None


class TabSpec(Strict):
    screen_id: str
    label: str
    icon: str = Field(description="Material icon name, e.g. 'home', 'search', 'person'.")


# Tool inputs (docstrings become tool descriptions).

class CreateScreen(Strict):
    """Create an empty screen. Returns its screen_id and root_id (a vertical Column to add components into)."""

    name: str
    background_color: str | None = None

    @field_validator("background_color")
    @classmethod
    def _c(cls, v):
        return _color(v)


class UpdateScreen(Strict):
    """Rename a screen or change its background color."""

    screen_id: str
    name: str | None = None
    background_color: str | None = None

    @field_validator("background_color")
    @classmethod
    def _c(cls, v):
        return _color(v)


class DeleteScreen(Strict):
    """Delete a screen. Buttons that navigated to it lose their action."""

    screen_id: str


class AddComponents(Strict):
    """Add component trees under a container on a screen. Build whole sections in one call using
    nested children (e.g. a Card with its image, texts and button). Returns the new ids."""

    screen_id: str
    parent_id: str = Field(description="A container's id, or the screen's root_id.")
    index: int | None = Field(None, description="Position among the parent's children; omit to append.")
    components: list[ComponentSpec] = Field(min_length=1)


class UpdateComponent(Strict):
    """Change a component. props and style are merged into the current values (set a key to null to
    remove it). on_tap replaces the current action; pass clear_on_tap to remove it."""

    screen_id: str
    component_id: str
    name: str | None = None
    props: dict[str, Any] | None = None
    style: dict[str, Any] | None = None
    on_tap: ActionSpec | None = None
    clear_on_tap: bool = False


class RemoveComponent(Strict):
    """Remove a component and everything inside it."""

    screen_id: str
    component_id: str


class MoveComponent(Strict):
    """Move a component into a container on the same screen."""

    screen_id: str
    component_id: str
    new_parent_id: str
    index: int | None = None


class SetTheme(Strict):
    """Update the app theme. Only the given values change."""

    brightness: Literal["light", "dark"] | None = None
    primary: str | None = None
    secondary: str | None = None
    background: str | None = None
    surface: str | None = None
    text: str | None = None
    mutedText: str | None = None
    radius: float | None = None
    fontFamily: str | None = Field(None, description="A Google Font name, e.g. 'Inter', 'Poppins', 'DM Sans'.")

    @field_validator("primary", "secondary", "background", "surface", "text", "mutedText")
    @classmethod
    def _c(cls, v):
        return _color(v)


class CreateDataModel(Strict):
    """Create a data model (a table / collection). An 'id' field is added automatically."""

    name: str = Field(description="Singular PascalCase, e.g. 'Plant'.")
    fields: list[FieldSpec] = Field(default_factory=list)


class UpdateDataModel(Strict):
    """Rename a data model, add fields, or remove fields by id."""

    model_id: str
    name: str | None = None
    add_fields: list[FieldSpec] = Field(default_factory=list)
    remove_field_ids: list[str] = Field(default_factory=list)


class DeleteDataModel(Strict):
    """Delete a data model."""

    model_id: str


class SetNavigation(Strict):
    """Set how the app navigates. 'tabs' shows a bottom navigation bar with 2-5 tabs;
    'stack' starts on one screen and buttons push other screens."""

    type: Literal["stack", "tabs"]
    initial_screen_id: str
    tabs: list[TabSpec] = Field(default_factory=list, description="Required for 'tabs': 2-5 entries.")


class UpdateApp(Strict):
    """Rename the app or update its description."""

    name: str | None = None
    description: str | None = None


# ─── Handlers ────────────────────────────────────────────────────────────────


@dataclass
class Outcome:
    result: dict[str, Any]
    change: str  # human-readable, shown to the user


def _check_props(kind: str, props: dict[str, Any]) -> dict[str, Any]:
    allowed = {p["key"] for p in catalog()[kind]["props"]}
    unknown = set(props) - allowed
    if unknown:
        hint = ", ".join(sorted(allowed)) or "none"
        raise ToolError(f"{kind} has no prop(s) {', '.join(sorted(unknown))}. Allowed: {hint}.")
    return props


def _action(schema: dict, a: ActionSpec | None) -> dict | None:
    if a is None:
        return None
    if a.type == "navigate":
        if not a.screenId:
            raise ToolError("navigate needs screenId.")
        find_screen(schema, a.screenId)
        return {"type": "navigate", "screenId": a.screenId}
    if a.type == "openUrl":
        if not a.url:
            raise ToolError("openUrl needs url.")
        return {"type": "openUrl", "url": a.url}
    if a.type == "snackbar":
        return {"type": "snackbar", "message": a.message or ""}
    return {"type": "back"}


def _build(schema: dict, spec: ComponentSpec, top_level: bool) -> dict:
    if spec.children and not is_container(spec.type):
        containers = ", ".join(k for k, v in catalog().items() if v["container"])
        raise ToolError(f"{spec.type} cannot have children. Containers: {containers}.")
    if spec.type == "AppBar" and not top_level:
        raise ToolError("AppBar is only allowed as the first child of a screen's root.")
    node = {
        "id": new_id(),
        "type": spec.type,
        "props": {**catalog()[spec.type]["defaultProps"], **_check_props(spec.type, spec.props)},
        "style": {**catalog()[spec.type]["defaultStyle"], **spec.style.model_dump(exclude_none=True)},
        "children": [_build(schema, c, False) for c in spec.children],
    }
    if spec.name:
        node["name"] = spec.name
    action = _action(schema, spec.on_tap)
    if action:
        node["onTap"] = action
    return node


def _summary(node: dict) -> dict:
    out = {"id": node["id"], "type": node["type"]}
    if node["children"]:
        out["children"] = [_summary(c) for c in node["children"]]
    return out


def _label(node: dict) -> str:
    props = node.get("props", {})
    text = props.get("text") or props.get("label") or props.get("title")
    return f"{node.get('name') or node['type']}" + (f" “{str(text)[:30]}”" if text else "")


def create_screen(schema: dict, a: CreateScreen) -> Outcome:
    x = max((s["frame"]["x"] for s in schema["screens"]), default=-(FRAME_WIDTH + FRAME_GAP)) + FRAME_WIDTH + FRAME_GAP
    root = {"id": new_id(), "type": "Column", "name": "Screen", "props": {}, "style": {"padding": 16, "gap": 12}, "children": []}
    screen = {"id": new_id(), "name": a.name, "root": root, "frame": {"x": x, "y": 0}}
    if a.background_color:
        screen["backgroundColor"] = a.background_color
    schema["screens"].append(screen)
    return Outcome({"screen_id": screen["id"], "root_id": root["id"]}, f"Created {a.name} screen")


def update_screen(schema: dict, a: UpdateScreen) -> Outcome:
    screen = find_screen(schema, a.screen_id)
    if a.name:
        screen["name"] = a.name
    if a.background_color:
        screen["backgroundColor"] = a.background_color
    return Outcome({"ok": True}, f"Updated {screen['name']} screen")


def delete_screen(schema: dict, a: DeleteScreen) -> Outcome:
    screen = find_screen(schema, a.screen_id)
    if len(schema["screens"]) == 1:
        raise ToolError("An app needs at least one screen.")
    schema["screens"].remove(screen)

    def strip(node: dict) -> None:
        if node.get("onTap", {}).get("screenId") == a.screen_id:
            node.pop("onTap")
        for c in node["children"]:
            strip(c)

    for s in schema["screens"]:
        strip(s["root"])
    nav = schema["navigation"]
    nav["tabs"] = [t for t in nav["tabs"] if t["screenId"] != a.screen_id]
    if nav["initialScreenId"] == a.screen_id:
        nav["initialScreenId"] = schema["screens"][0]["id"]
    if nav["type"] == "tabs" and len(nav["tabs"]) < 2:
        nav["type"] = "stack"
        nav["tabs"] = []
    return Outcome({"ok": True}, f"Deleted {screen['name']} screen")


def add_components(schema: dict, a: AddComponents) -> Outcome:
    screen = find_screen(schema, a.screen_id)
    parent = get_node(screen, a.parent_id)
    if not is_container(parent["type"]):
        raise ToolError(f"'{a.parent_id}' is a {parent['type']}, which can't hold children.")
    top_level = parent["id"] == screen["root"]["id"]
    # Build everything first so a bad spec leaves the schema untouched.
    nodes = [_build(schema, spec, top_level) for spec in a.components]
    index = len(parent["children"]) if a.index is None else max(0, min(a.index, len(parent["children"])))
    for i, node in enumerate(nodes):
        has_bar = any(c["type"] == "AppBar" for c in parent["children"])
        if node["type"] == "AppBar" and (index + i != 0 or has_bar):
            raise ToolError("A screen has at most one AppBar, and it must be the root's first child (index 0).")
    parent["children"][index:index] = nodes
    names = ", ".join(_label(n) for n in nodes[:3]) + ("…" if len(nodes) > 3 else "")
    return Outcome({"created": [_summary(n) for n in nodes]}, f"Added {names} to {screen['name']}")


def update_component(schema: dict, a: UpdateComponent) -> Outcome:
    screen = find_screen(schema, a.screen_id)
    node = get_node(screen, a.component_id)
    if a.props:
        _check_props(node["type"], a.props)
        for k, v in a.props.items():
            if v is None:
                node["props"].pop(k, None)
            else:
                node["props"][k] = v
    if a.style:
        merged = {**node["style"], **a.style}
        merged = {k: v for k, v in merged.items() if v is not None}
        try:
            node["style"] = StyleSpec.model_validate(merged).model_dump(exclude_none=True)
        except ValidationError as e:
            raise ToolError(f"Invalid style: {_errors(e)}") from None
    if a.name:
        node["name"] = a.name
    if a.clear_on_tap:
        node.pop("onTap", None)
    elif a.on_tap:
        node["onTap"] = _action(schema, a.on_tap)
    return Outcome({"ok": True}, f"Updated {_label(node)} on {screen['name']}")


def remove_component(schema: dict, a: RemoveComponent) -> Outcome:
    screen = find_screen(schema, a.screen_id)
    if a.component_id == screen["root"]["id"]:
        raise ToolError("The screen root can't be removed; remove its children instead.")
    found = find_parent(screen["root"], a.component_id)
    if not found:
        raise ToolError(f"Component '{a.component_id}' is not on screen '{screen['name']}'.")
    parent, i = found
    node = parent["children"].pop(i)
    return Outcome({"ok": True}, f"Removed {_label(node)} from {screen['name']}")


def move_component(schema: dict, a: MoveComponent) -> Outcome:
    screen = find_screen(schema, a.screen_id)
    node = get_node(screen, a.component_id)
    target = get_node(screen, a.new_parent_id)
    if node is screen["root"]:
        raise ToolError("The screen root can't be moved.")
    if not is_container(target["type"]):
        raise ToolError(f"'{a.new_parent_id}' is a {target['type']}, which can't hold children.")
    if find_node(node, target["id"]):
        raise ToolError("Can't move a component into itself.")
    parent, i = find_parent(screen["root"], node["id"])  # type: ignore[misc]
    parent["children"].pop(i)
    index = len(target["children"]) if a.index is None else max(0, min(a.index, len(target["children"])))
    target["children"].insert(index, node)
    return Outcome({"ok": True}, f"Moved {_label(node)}")


def set_theme(schema: dict, a: SetTheme) -> Outcome:
    changes = a.model_dump(exclude_none=True)
    if not changes:
        raise ToolError("Pass at least one theme value.")
    schema["theme"].update(changes)
    return Outcome({"ok": True}, "Updated the theme")


def _fields(schema: dict, specs: list[FieldSpec]) -> list[dict]:
    out = []
    for f in specs:
        field = {"id": new_id(), "name": f.name, "type": f.type, "required": f.required}
        if f.type == "reference":
            if not f.reference_model_id:
                raise ToolError(f"Field '{f.name}' is a reference and needs reference_model_id.")
            find_model(schema, f.reference_model_id)
            field["referenceModelId"] = f.reference_model_id
        out.append(field)
    return out


def create_data_model(schema: dict, a: CreateDataModel) -> Outcome:
    if any(m["name"].lower() == a.name.lower() for m in schema["dataModels"]):
        raise ToolError(f"A data model named '{a.name}' already exists.")
    fields = _fields(schema, a.fields)
    if not any(f["name"] == "id" for f in fields):
        fields.insert(0, {"id": new_id(), "name": "id", "type": "string", "required": True})
    model = {"id": new_id(), "name": a.name, "fields": fields}
    schema["dataModels"].append(model)
    return Outcome({"model_id": model["id"], "fields": {f["name"]: f["id"] for f in fields}}, f"Created {a.name} data model")


def update_data_model(schema: dict, a: UpdateDataModel) -> Outcome:
    model = find_model(schema, a.model_id)
    ids = {f["id"] for f in model["fields"]}
    for fid in a.remove_field_ids:
        if fid not in ids:
            raise ToolError(f"Field '{fid}' is not on {model['name']}.")
    added = _fields(schema, a.add_fields)
    model["fields"] = [f for f in model["fields"] if f["id"] not in a.remove_field_ids] + added
    if a.name:
        model["name"] = a.name
    return Outcome({"added_fields": {f["name"]: f["id"] for f in added}}, f"Updated {model['name']} data model")


def delete_data_model(schema: dict, a: DeleteDataModel) -> Outcome:
    model = find_model(schema, a.model_id)
    schema["dataModels"].remove(model)
    return Outcome({"ok": True}, f"Deleted {model['name']} data model")


def set_navigation(schema: dict, a: SetNavigation) -> Outcome:
    find_screen(schema, a.initial_screen_id)
    if a.type == "tabs" and not 2 <= len(a.tabs) <= 5:
        raise ToolError("Tab navigation needs 2 to 5 tabs.")
    for t in a.tabs:
        find_screen(schema, t.screen_id)
    schema["navigation"] = {
        "type": a.type,
        "initialScreenId": a.initial_screen_id,
        "tabs": [{"screenId": t.screen_id, "label": t.label, "icon": t.icon} for t in a.tabs] if a.type == "tabs" else [],
    }
    return Outcome({"ok": True}, "Set up bottom tab navigation" if a.type == "tabs" else "Set up stack navigation")


def update_app(schema: dict, a: UpdateApp) -> Outcome:
    if a.name:
        schema["name"] = a.name
        schema["build"]["appName"] = a.name
    if a.description is not None:
        schema["description"] = a.description
    return Outcome({"ok": True}, "Updated app details")


# ─── Registry ────────────────────────────────────────────────────────────────

TOOLS: dict[str, tuple[type[BaseModel], Callable[[dict, Any], Outcome]]] = {
    "create_screen": (CreateScreen, create_screen),
    "update_screen": (UpdateScreen, update_screen),
    "delete_screen": (DeleteScreen, delete_screen),
    "add_components": (AddComponents, add_components),
    "update_component": (UpdateComponent, update_component),
    "remove_component": (RemoveComponent, remove_component),
    "move_component": (MoveComponent, move_component),
    "set_theme": (SetTheme, set_theme),
    "create_data_model": (CreateDataModel, create_data_model),
    "update_data_model": (UpdateDataModel, update_data_model),
    "delete_data_model": (DeleteDataModel, delete_data_model),
    "set_navigation": (SetNavigation, set_navigation),
    "update_app": (UpdateApp, update_app),
}


MAX_INLINE_DEPTH = 3  # how deep recursive component trees are spelled out in tool schemas (deeper levels are still validated)


def _inline_refs(node: Any, defs: dict[str, Any], depth: int = 0) -> Any:
    """Replaces $ref with the referenced schema, since some models behind OpenRouter reject $ref.
    Recursive shapes (a component's children) are unrolled to MAX_INLINE_DEPTH levels."""
    if isinstance(node, dict):
        if "$ref" in node:
            name = node["$ref"].rsplit("/", 1)[-1]
            if depth >= MAX_INLINE_DEPTH:
                return {"type": "object", "description": f"A {name} (same shape as above)."}
            return _inline_refs(defs[name], defs, depth + 1)
        return {k: _inline_refs(v, defs, depth) for k, v in node.items() if k not in ("$defs", "title")}
    if isinstance(node, list):
        return [_inline_refs(v, defs, depth) for v in node]
    return node


def tool_definitions() -> list[dict[str, Any]]:
    """Tools in OpenAI function-calling format (as OpenRouter expects), in a stable order."""
    defs = []
    for name, (model, _) in TOOLS.items():
        schema = model.model_json_schema()
        schema.pop("description", None)
        parameters = _inline_refs(schema, schema.get("$defs", {}))
        defs.append({
            "type": "function",
            "function": {"name": name, "description": (model.__doc__ or "").strip(), "parameters": parameters},
        })
    return defs


def _errors(e: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in err['loc']) or 'input'}: {err['msg']}" for err in e.errors())


def execute(schema: dict, name: str, raw_input: Any) -> Outcome:
    entry = TOOLS.get(name)
    if not entry:
        raise ToolError(f"Unknown tool '{name}'.")
    model, handler = entry
    try:
        args = model.model_validate(raw_input)
    except ValidationError as e:
        raise ToolError(f"Invalid input for {name}: {_errors(e)}") from None
    return handler(schema, args)
