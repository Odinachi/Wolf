"""A realistic sample schema that exercises every component type."""


def node(id_, type_, props=None, style=None, children=None, on_tap=None):
    n = {"id": id_, "type": type_, "props": props or {}, "style": style or {}, "children": children or []}
    if on_tap:
        n["onTap"] = on_tap
    return n


def sample_schema(provider="supabase", nav="tabs"):
    home = {
        "id": "s-home", "name": "Home", "frame": {"x": 0, "y": 0},
        "root": node("r-home", "Column", style={"padding": 16, "gap": 12}, children=[
            node("n1", "AppBar", {"title": "Plant Pal", "showBack": False, "actionIcon": "notifications"}),
            node("n2", "Text", {"text": "Good morning, Ada's \"plants\" cost $5", "variant": "headline"}, {"fontWeight": 700}),
            node("n3", "TextField", {"label": "Search", "hint": "Find a plant", "icon": "search", "keyboard": "text"}),
            node("n4", "ListView", {"direction": "horizontal"}, {"gap": 8, "height": 48}, [
                node("n5", "Chip", {"label": "All", "selected": True}),
                node("n6", "Chip", {"label": "Indoor", "icon": "home"}),
            ]),
            node("n7", "Grid", {"columns": 2}, {"gap": 12}, [
                node("n8", "Card", {}, {"padding": 12, "borderRadius": 16, "gap": 8}, [
                    node("n9", "Image", {"src": "https://picsum.photos/seed/fern/400/300", "fit": "cover"}, {"height": 100, "borderRadius": 12, "width": "fill"}),
                    node("n10", "Text", {"text": "Fern", "variant": "title"}),
                ], on_tap={"type": "navigate", "screenId": "s-detail"}),
            ]),
            node("n11", "Row", {}, {"gap": 8, "mainAxisAlignment": "spaceBetween"}, [
                node("n12", "Avatar", {"initials": "AL", "size": 36}),
                node("n13", "Text", {"text": "A very long name that might overflow the row"}),
                node("n14", "IconButton", {"icon": "favorite_border"}, on_tap={"type": "snackbar", "message": "Saved!"}),
                node("n14b", "Button", {"label": "Go", "variant": "tonal"}, {"width": "fill"}),
            ]),
            node("n15", "ListTile", {"title": "Watering", "subtitle": "Every 3 days", "leadingIcon": "water_drop", "trailingIcon": "chevron_right"}),
            node("n16", "ProgressBar", {"value": 0.7}),
            node("n17", "Switch", {"label": "Reminders", "value": True}),
            node("n18", "Checkbox", {"label": "Pet safe only"}),
            node("n19", "Slider", {"value": 0.3}),
            node("n20", "Divider"),
            node("n21", "Container", {}, {"padding": [8, 16, 8, 16], "backgroundColor": "#E8F5E9", "borderRadius": 12, "borderColor": "#2E7D32", "borderWidth": 1}, [
                node("n22", "Icon", {"icon": "eco", "size": 20}, {"color": "#2E7D32"}),
            ]),
            node("n23", "Stack", {}, {}, [node("n24", "Text", {"text": "Layered"})]),
            node("n25", "Button", {"label": "Docs", "variant": "outlined", "icon": "open_in_new"}, on_tap={"type": "openUrl", "url": "https://example.com"}),
            node("n26", "Button", {"label": "Ghost", "variant": "text"}),
            node("n27", "Spacer", {}, {"height": 24}),
        ]),
    }
    detail = {
        "id": "s-detail", "name": "Plant Detail", "frame": {"x": 510, "y": 0},
        "root": node("r-detail", "Column", style={"padding": 16, "gap": 12}, children=[
            node("d1", "AppBar", {"title": "Fern", "showBack": True}),
            node("d2", "Text", {"text": "Details"}, {"textAlign": "center", "color": "#1B5E20", "fontSize": 18}),
            node("d3", "Spacer"),
            node("d4", "Button", {"label": "Back", "variant": "filled"}, {"width": "fill"}, on_tap={"type": "back"}),
        ]),
    }
    profile = {
        "id": "s-profile", "name": "Profile", "frame": {"x": 1020, "y": 0},
        "root": node("r-profile", "Column", style={"padding": 16}, children=[node("p1", "Text", {"text": "Profile", "variant": "display"})]),
    }
    return {
        "version": 1,
        "name": "Plant Pal",
        "description": "Track and water your plants.",
        "theme": {"brightness": "light", "primary": "#2E7D32", "secondary": "#558B2F", "background": "#FAFAF5",
                  "surface": "#FFFFFF", "text": "#1B1B1B", "mutedText": "#5F5F5F", "radius": 14, "fontFamily": "Inter"},
        "screens": [home, detail, profile],
        "dataModels": [
            {"id": "m1", "name": "Plant", "fields": [
                {"id": "f1", "name": "id", "type": "string", "required": True},
                {"id": "f2", "name": "name", "type": "string", "required": True},
                {"id": "f3", "name": "water every days", "type": "int", "required": False},
                {"id": "f4", "name": "price", "type": "double", "required": False},
                {"id": "f5", "name": "lastWatered", "type": "datetime", "required": False},
                {"id": "f6", "name": "petSafe", "type": "bool", "required": True},
                {"id": "f7", "name": "class", "type": "string", "required": False},
            ]},
        ],
        "navigation": {"type": nav, "initialScreenId": "s-home", "tabs": [
            {"screenId": "s-home", "label": "Home", "icon": "home"},
            {"screenId": "s-profile", "label": "Profile", "icon": "person"},
        ]},
        "backend": {"provider": provider, "url": "https://abc.supabase.co", "anonKey": "public-anon"},
        "build": {"appName": "Plant Pal", "bundleId": "com.wolf.plantpal", "version": "1.2.0", "buildNumber": 3,
                  "platforms": ["android", "ios"]},
    }
