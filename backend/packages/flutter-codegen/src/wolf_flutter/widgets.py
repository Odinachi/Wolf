"""Compiles component nodes into Flutter widget expressions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import dart

CONTAINERS = {"Column", "Row", "Stack", "Container", "Card", "ListView", "Grid"}

TEXT_VARIANTS = {
    "display": "displaySmall",
    "headline": "headlineSmall",
    "title": "titleMedium",
    "body": "bodyMedium",
    "label": "labelLarge",
    "caption": "bodySmall",
}

MAIN_AXIS = {
    "start": "MainAxisAlignment.start",
    "center": "MainAxisAlignment.center",
    "end": "MainAxisAlignment.end",
    "spaceBetween": "MainAxisAlignment.spaceBetween",
    "spaceAround": "MainAxisAlignment.spaceAround",
    "spaceEvenly": "MainAxisAlignment.spaceEvenly",
}

CROSS_AXIS = {
    "start": "CrossAxisAlignment.start",
    "center": "CrossAxisAlignment.center",
    "end": "CrossAxisAlignment.end",
    "stretch": "CrossAxisAlignment.stretch",
}

FONT_WEIGHTS = {400: "FontWeight.w400", 500: "FontWeight.w500", 600: "FontWeight.w600", 700: "FontWeight.w700", 800: "FontWeight.w800"}


@dataclass
class Context:
    """Compilation state shared across one project."""

    # screen id -> route name, e.g. '/home'
    routes: dict[str, str]
    uses_url_launcher: bool = False
    warnings: list[str] = field(default_factory=list)


def call(name: str, args: list[str | None]) -> str:
    """Formats `Name(arg, arg,)` with one argument per line, like dart format."""
    present = [a for a in args if a]
    if not present:
        return f"{name}()"
    if len(present) == 1 and "\n" not in present[0] and len(name) + len(present[0]) < 60:
        return f"{name}({present[0]})"
    body = ",\n".join(dart.indent(a, 2) for a in present)
    return f"{name}(\n{body},\n)"


def named(key: str, value: str | None) -> str | None:
    return f"{key}: {value}" if value is not None else None


def widget_list(items: list[str]) -> str:
    if not items:
        return "[]"
    body = ",\n".join(dart.indent(i, 2) for i in items)
    return f"[\n{body},\n]"


# ─── Actions ─────────────────────────────────────────────────────────────────


def action_callback(action: Any, ctx: Context) -> str | None:
    if not isinstance(action, dict):
        return None
    kind = action.get("type")
    if kind == "navigate":
        route = ctx.routes.get(action.get("screenId", ""))
        if not route:
            ctx.warnings.append(f"Navigate action points at a missing screen ({action.get('screenId')}).")
            return None
        return f"() => Navigator.of(context).pushNamed({dart.string(route)})"
    if kind == "back":
        return "() => Navigator.of(context).maybePop()"
    if kind == "openUrl" and action.get("url"):
        ctx.uses_url_launcher = True
        return f"() => launchUrl(Uri.parse({dart.string(action['url'])}))"
    if kind == "snackbar":
        msg = dart.string(action.get("message", ""))
        return f"() => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text({msg})))"
    return None


# ─── Styling wrappers ────────────────────────────────────────────────────────


def text_style(style: dict, base: str | None) -> str | None:
    parts = [
        named("color", dart.color(style.get("color"))),
        named("fontSize", dart.number(style.get("fontSize"))),
        named("fontWeight", FONT_WEIGHTS.get(style.get("fontWeight"))),
    ]
    parts = [p for p in parts if p]
    if base:
        return f"Theme.of(context).textTheme.{base}?.copyWith({', '.join(parts)})" if parts else f"Theme.of(context).textTheme.{base}"
    return f"TextStyle({', '.join(parts)})" if parts else None


def border_radius(style: dict) -> str | None:
    r = dart.number(style.get("borderRadius"))
    return f"BorderRadius.circular({r})" if r else None


def decoration(style: dict) -> str | None:
    border = None
    border_color = dart.color(style.get("borderColor"))
    if border_color or style.get("borderWidth"):
        border = call("Border.all", [
            named("color", border_color or "Theme.of(context).dividerColor"),
            named("width", dart.number(style.get("borderWidth")) or "1.0"),
        ])
    args = [
        named("color", dart.color(style.get("backgroundColor"))),
        named("borderRadius", border_radius(style)),
        named("border", border),
    ]
    if not any(args):
        return None
    return call("BoxDecoration", args)


def wrap_box(widget: str, style: dict, *, handles_padding: bool, handles_size: bool, in_row: bool) -> str:
    """Applies padding, size and margin that the widget itself didn't consume."""
    if not handles_padding:
        pad = dart.edge_insets(style.get("padding"))
        if pad:
            widget = call("Padding", [named("padding", pad), named("child", widget)])
    if not handles_size:
        width = style.get("width")
        w = "double.infinity" if width == "fill" and not in_row else dart.number(width)
        h = dart.number(style.get("height"))
        if w or h:
            widget = call("SizedBox", [named("width", w), named("height", h), named("child", widget)])
    margin = dart.edge_insets(style.get("margin"))
    if margin:
        widget = call("Padding", [named("padding", margin), named("child", widget)])
    return widget


def with_gap(children: list[str], gap: Any, axis: str) -> list[str]:
    g = dart.number(gap)
    if not g or len(children) < 2:
        return children
    spacer = f"const SizedBox({'height' if axis == 'vertical' else 'width'}: {g})"
    out: list[str] = []
    for i, child in enumerate(children):
        if i:
            out.append(spacer)
        out.append(child)
    return out


# ─── Nodes ───────────────────────────────────────────────────────────────────


def compile_children(node: dict, ctx: Context, parent_axis: str | None) -> list[str]:
    return [compile_node(c, ctx, parent_axis) for c in node.get("children") or [] if isinstance(c, dict)]


def flex(node: dict, ctx: Context, axis: str) -> str:
    style = node.get("style") or {}
    children = with_gap(compile_children(node, ctx, axis), style.get("gap"), axis)
    name = "Column" if axis == "vertical" else "Row"
    default_cross = "CrossAxisAlignment.stretch" if axis == "vertical" else "CrossAxisAlignment.center"
    return call(name, [
        named("mainAxisAlignment", MAIN_AXIS.get(style.get("mainAxisAlignment"))),
        named("crossAxisAlignment", CROSS_AXIS.get(style.get("crossAxisAlignment"), default_cross)),
        "mainAxisSize: MainAxisSize.min" if axis == "vertical" else None,
        named("children", widget_list(children)),
    ])


def compile_node(node: dict, ctx: Context, parent_axis: str | None = None) -> str:
    """Compiles one node. `parent_axis` is 'vertical' / 'horizontal' inside a Column / Row."""
    kind = node.get("type")
    props = node.get("props") or {}
    style = node.get("style") or {}
    on_tap = action_callback(node.get("onTap"), ctx)
    in_row = parent_axis == "horizontal"
    handles_padding = False
    handles_size = False
    tappable = False  # whether the widget consumed on_tap itself

    if kind == "Column":
        widget = flex(node, ctx, "vertical")
    elif kind == "Row":
        widget = flex(node, ctx, "horizontal")
    elif kind == "Stack":
        widget = call("Stack", [named("children", widget_list(compile_children(node, ctx, None)))])
    elif kind in ("Container", "Card"):
        children = with_gap(compile_children(node, ctx, "vertical"), style.get("gap"), "vertical")
        inner = children[0] if len(children) == 1 else call("Column", [
            "crossAxisAlignment: CrossAxisAlignment.stretch",
            "mainAxisSize: MainAxisSize.min",
            named("children", widget_list(children)),
        ])
        pad = dart.edge_insets(style.get("padding"))
        if kind == "Card":
            body = call("Padding", [named("padding", pad), named("child", inner)]) if pad else inner
            if on_tap:
                body = call("InkWell", [named("onTap", on_tap), named("child", body)])
                tappable = True
            radius = border_radius(style)
            widget = call("Card", [
                named("elevation", dart.number(style.get("elevation"))),
                named("color", dart.color(style.get("backgroundColor"))),
                "clipBehavior: Clip.antiAlias",
                "margin: EdgeInsets.zero",
                named("shape", call("RoundedRectangleBorder", [named("borderRadius", radius)]) if radius else None),
                named("child", body),
            ])
        else:
            width = style.get("width")
            widget = call("Container", [
                named("width", "double.infinity" if width == "fill" and not in_row else dart.number(width)),
                named("height", dart.number(style.get("height"))),
                named("padding", pad),
                named("decoration", decoration(style)),
                named("child", inner) if children else None,
            ])
            handles_size = True
        handles_padding = True
    elif kind == "ListView":
        horizontal = props.get("direction") == "horizontal"
        axis = "horizontal" if horizontal else "vertical"
        children = with_gap(compile_children(node, ctx, axis), style.get("gap"), axis)
        pad = dart.edge_insets(style.get("padding"))
        handles_padding = True
        if horizontal:
            widget = call("SizedBox", [
                named("height", dart.number(style.get("height")) or "140.0"),
                named("child", call("ListView", [
                    "scrollDirection: Axis.horizontal",
                    named("padding", pad),
                    named("children", widget_list(children)),
                ])),
            ])
            handles_size = True
        else:
            # Nested vertical lists size to their content; the screen body handles scrolling.
            widget = call("ListView", [
                "shrinkWrap: true",
                "physics: const NeverScrollableScrollPhysics()",
                named("padding", pad or "EdgeInsets.zero"),
                named("children", widget_list(children)),
            ])
    elif kind == "Grid":
        gap = dart.number(style.get("gap")) or "0.0"
        columns = props.get("columns") if isinstance(props.get("columns"), int) and props.get("columns") > 0 else 2
        widget = call("GridView.count", [
            f"crossAxisCount: {columns}",
            f"mainAxisSpacing: {gap}",
            f"crossAxisSpacing: {gap}",
            f"childAspectRatio: {dart.number(props.get('aspectRatio')) or '0.8'}",
            "shrinkWrap: true",
            "physics: const NeverScrollableScrollPhysics()",
            named("padding", dart.edge_insets(style.get("padding")) or "EdgeInsets.zero"),
            named("children", widget_list(compile_children(node, ctx, None))),
        ])
        handles_padding = True
    elif kind == "Spacer":
        h = dart.number(style.get("height"))
        if h is None and parent_axis:
            return "const Spacer()"
        size = h or "16.0"
        return f"const SizedBox({'width' if in_row else 'height'}: {size})"
    elif kind == "Divider":
        widget = "const Divider(height: 1)"
    elif kind == "Text":
        base = TEXT_VARIANTS.get(props.get("variant"), "bodyMedium")
        align = {"left": "TextAlign.left", "center": "TextAlign.center", "right": "TextAlign.right"}.get(style.get("textAlign"))
        widget = call("Text", [dart.string(props.get("text", "")), named("style", text_style(style, base)), named("textAlign", align)])
    elif kind == "Image":
        fit = {"cover": "BoxFit.cover", "contain": "BoxFit.contain", "fill": "BoxFit.fill"}.get(props.get("fit"), "BoxFit.cover")
        width = style.get("width")
        img = call("Image.network", [
            dart.string(props.get("src", "")),
            f"fit: {fit}",
            named("width", "double.infinity" if width == "fill" and not in_row else dart.number(width)),
            named("height", dart.number(style.get("height"))),
            "errorBuilder: (context, error, stack) => Container(color: Theme.of(context).colorScheme.surfaceContainerHighest)",
        ])
        radius = border_radius(style)
        widget = call("ClipRRect", [named("borderRadius", radius), named("child", img)]) if radius else img
        handles_size = True
    elif kind == "Icon":
        widget = call("Icon", [dart.icon(props.get("icon")), named("size", dart.number(props.get("size"))), named("color", dart.color(style.get("color")))])
    elif kind == "Avatar":
        size = props.get("size") if isinstance(props.get("size"), (int, float)) else 40
        src = props.get("src")
        widget = call("CircleAvatar", [
            named("radius", dart.number(size / 2)),
            named("backgroundColor", dart.color(style.get("backgroundColor"))),
            named("backgroundImage", f"NetworkImage({dart.string(src)})" if src else None),
            None if src else named("child", f"Text({dart.string(props.get('initials', ''))})"),
        ])
    elif kind == "Chip":
        widget = call("FilterChip", [
            named("label", f"Text({dart.string(props.get('label', ''))})"),
            named("avatar", f"Icon({dart.icon(props.get('icon'))}, size: 18)" if props.get("icon") else None),
            f"selected: {'true' if props.get('selected') else 'false'}",
            f"onSelected: (_) {{ {f'({on_tap})();' if on_tap else ''} }}",
        ])
        tappable = True
    elif kind == "ListTile":
        widget = call("ListTile", [
            named("leading", f"Icon({dart.icon(props.get('leadingIcon'))})" if props.get("leadingIcon") else None),
            named("title", f"Text({dart.string(props.get('title', ''))})"),
            named("subtitle", f"Text({dart.string(props.get('subtitle'))})" if props.get("subtitle") else None),
            named("trailing", f"Icon({dart.icon(props.get('trailingIcon'))})" if props.get("trailingIcon") else None),
            named("onTap", on_tap),
            "contentPadding: EdgeInsets.zero",
        ])
        tappable = True
    elif kind == "ProgressBar":
        value = props.get("value") if isinstance(props.get("value"), (int, float)) else 0.5
        widget = call("LinearProgressIndicator", [
            f"value: {dart.number(max(0, min(1, value)))}",
            named("borderRadius", border_radius(style) or "BorderRadius.circular(4)"),
            "minHeight: 6",
        ])
    elif kind == "Button":
        variant = props.get("variant", "filled")
        cls = {"filled": "FilledButton", "tonal": "FilledButton", "outlined": "OutlinedButton", "text": "TextButton"}.get(variant, "FilledButton")
        label = f"Text({dart.string(props.get('label', ''))})"
        if props.get("icon"):
            ctor = "FilledButton.tonalIcon" if variant == "tonal" else f"{cls}.icon"
            widget = call(ctor, [named("onPressed", on_tap or "() {}"), named("icon", f"Icon({dart.icon(props.get('icon'))})"), named("label", label)])
        else:
            ctor = "FilledButton.tonal" if variant == "tonal" else cls
            widget = call(ctor, [named("onPressed", on_tap or "() {}"), named("child", label)])
        tappable = True
    elif kind == "IconButton":
        widget = call("IconButton", [named("onPressed", on_tap or "() {}"), named("icon", f"Icon({dart.icon(props.get('icon'))})"), named("color", dart.color(style.get("color")))])
        tappable = True
    elif kind == "TextField":
        keyboard = {"email": "TextInputType.emailAddress", "number": "TextInputType.number", "phone": "TextInputType.phone"}.get(props.get("keyboard"))
        widget = call("TextField", [
            "obscureText: true" if props.get("obscure") else None,
            named("keyboardType", keyboard),
            named("decoration", call("InputDecoration", [
                named("labelText", dart.string(props["label"]) if props.get("label") else None),
                named("hintText", dart.string(props["hint"]) if props.get("hint") else None),
                named("prefixIcon", f"Icon({dart.icon(props.get('icon'))})" if props.get("icon") else None),
                "border: const OutlineInputBorder()",
            ])),
        ])
    elif kind == "Switch":
        widget = call("WolfSwitch", [named("label", dart.string(props.get("label", ""))), f"initialValue: {'true' if props.get('value') else 'false'}"])
    elif kind == "Checkbox":
        widget = call("WolfCheckbox", [named("label", dart.string(props.get("label", ""))), f"initialValue: {'true' if props.get('value') else 'false'}"])
    elif kind == "Slider":
        value = props.get("value") if isinstance(props.get("value"), (int, float)) else 0.5
        widget = call("WolfSlider", [f"initialValue: {dart.number(max(0, min(1, value)))}"])
    elif kind == "AppBar":
        # App bars are lifted into the Scaffold; one elsewhere renders as a title row.
        widget = call("Text", [dart.string(props.get("title", "")), "style: Theme.of(context).textTheme.titleLarge"])
    else:
        ctx.warnings.append(f"Unknown component type '{kind}' was skipped.")
        return "const SizedBox.shrink()"

    if on_tap and not tappable:
        widget = call("InkWell", [named("onTap", on_tap), named("child", widget)])

    widget = wrap_box(widget, style, handles_padding=handles_padding, handles_size=handles_size, in_row=in_row)

    # Inside a Row, text-like children must be able to shrink or they overflow.
    if parent_axis and (style.get("expand") or (in_row and style.get("width") == "fill")):
        widget = call("Expanded", [named("child", widget)])
    elif in_row and kind in ("Text", "Column", "ListTile", "TextField", "Slider"):
        widget = call("Flexible", [named("child", widget)])
    return widget
