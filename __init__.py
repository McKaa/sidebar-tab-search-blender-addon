# Sidebar Tab Search - Blender Add-on
# Copyright (C) 2025 McKaa

bl_info = {
    "name": "Sidebar Tab Search",
    "author": "McKaa (Powered by Antigravity)",
    "version": (2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Header",
    "description": "Quick search and switch between Sidebar (N-Panel) tabs.",
    "category": "Interface",
}

import bpy
import sys
import os
import json
import subprocess
import importlib

# --- PERSISTENCE ---

STORAGE_FILE = "sidebar_tab_search_settings.json"

def get_storage_path():
    config_dir = os.path.join(bpy.utils.user_resource('CONFIG'), "sidebar_tab_search")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, STORAGE_FILE)

_STORAGE_CACHE = {"favorites": [], "install_dates": {}, "history": []}

def load_storage():
    path = get_storage_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                _STORAGE_CACHE.update(json.load(f))
        except: pass

def save_storage():
    try:
        with open(get_storage_path(), 'w', encoding='utf-8') as f:
            json.dump(_STORAGE_CACHE, f, indent=4)
    except: pass

def is_favorite(name): return name in _STORAGE_CACHE["favorites"]

def toggle_fav(name):
    f = _STORAGE_CACHE["favorites"]
    f.remove(name) if name in f else f.append(name)
    save_storage()

def get_ctime(mod_name):
    c = _STORAGE_CACHE["install_dates"]
    if mod_name in c: return c[mod_name]
    ct = 0.0
    mod = sys.modules.get(mod_name.split('.')[0])
    if mod and hasattr(mod, '__file__') and mod.__file__:
        try: ct = os.path.getctime(mod.__file__)
        except: pass
    c[mod_name] = ct
    return ct

# --- CORE LOGIC ---

def get_all_tabs(context):
    entries, seen = [], set()
    for p in bpy.types.Panel.__subclasses__():
        if (getattr(p, 'bl_space_type', None) == 'VIEW_3D' and 
            getattr(p, 'bl_region_type', None) == 'UI' and 
            hasattr(p, 'bl_category')):
            
            cat = p.bl_category.strip()
            if not cat or cat == "Search": continue
            if hasattr(p, 'bl_options') and 'HIDE_HEADER' in p.bl_options: continue
            
            try:
                if hasattr(p, 'poll') and not p.poll(context): continue
            except: continue
            
            label = getattr(p, 'bl_label', "")
            ct = get_ctime(p.__module__)
            
            if cat not in seen:
                entries.append({'search': cat.lower(), 'display': cat, 'cat': cat, 'is_main': True, 'ctime': ct})
                seen.add(cat)
            
            if label and label != cat:
                d_name = f"{label} ({cat})"
                if d_name not in seen:
                    entries.append({'search': f"{label} {cat}".lower(), 'display': d_name, 'cat': cat, 'is_main': False, 'ctime': ct})
                    seen.add(d_name)
    return entries

def sort_entries(entries, context):
    prefs = context.preferences.addons.get(__package__ or __name__)
    sm = prefs.preferences.default_sort_method if prefs else 'ALPHABETICAL'
    sd = prefs.preferences.sort_direction if prefs else 'ASCENDING'
    
    if sm == 'ALPHABETICAL': entries.sort(key=lambda x: x['display'])
    elif sm == 'RECENT':
        hr = {x["display_name"]: i for i, x in enumerate(_STORAGE_CACHE["history"])}
        entries.sort(key=lambda x: (hr.get(x['display'], 9999), x['display']))
    elif sm == 'DATE': entries.sort(key=lambda x: x['ctime'])
    
    if sd == 'DESCENDING': entries.reverse()
    entries.sort(key=lambda x: not is_favorite(x['display']))
    return entries

# --- PROPERTIES ---

class SEARCHTABS_PG_history_item(bpy.types.PropertyGroup):
    category: bpy.props.StringProperty()
    display_name: bpy.props.StringProperty()
    icon_name: bpy.props.StringProperty()

class SEARCHTABS_PG_properties(bpy.types.PropertyGroup):
    search_query: bpy.props.StringProperty(name="Search", default="", options={'TEXTEDIT_UPDATE'})
    history: bpy.props.CollectionProperty(type=SEARCHTABS_PG_history_item)

# --- OPERATORS ---

class SEARCHTABS_OT_switch_tab(bpy.types.Operator):
    bl_idname = "searchtabs.switch_tab"
    bl_label = "Switch Tab"
    bl_options = {'REGISTER'}
    category_name: bpy.props.StringProperty()
    target_panel_label: bpy.props.StringProperty(default="")
    icon_name: bpy.props.StringProperty(default="NODE")

    def execute(self, context):
        if context.space_data and context.space_data.type == 'VIEW_3D':
            context.space_data.show_region_ui = True
        
        target = self.category_name
        area = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if area:
            region = next((r for r in area.regions if r.type == 'UI'), None)
            if region:
                try: region.active_panel_category = target
                except:
                    def delayed():
                        region.active_panel_category = target
                        return None
                    bpy.app.timers.register(delayed)

        hist = context.scene.searchtabs_props.history
        idx = next((i for i, x in enumerate(hist) if x.category == target), -1)
        if idx != -1: hist.remove(idx)
        
        item = hist.add()
        item.category, item.display_name, item.icon_name = target, (self.target_panel_label or target), self.icon_name
        if len(hist) > 1: hist.move(len(hist)-1, 0)
        while len(hist) > 50: hist.remove(len(hist)-1)
            
        _STORAGE_CACHE["history"] = [{"category": h.category, "display_name": h.display_name, "icon_name": h.icon_name} for h in hist]
        save_storage()
        return {'FINISHED'}

class SEARCHTABS_OT_toggle_favorite(bpy.types.Operator):
    bl_idname = "searchtabs.toggle_favorite"
    bl_label = "Toggle Favorite"; bl_options = {'INTERNAL'}
    display_name: bpy.props.StringProperty()
    def execute(self, context):
        toggle_fav(self.display_name); return {'FINISHED'}

class SEARCHTABS_OT_call_popover(bpy.types.Operator):
    bl_idname = "searchtabs.call_popover"
    bl_label = "Search Sidebar"
    def execute(self, context):
        bpy.ops.wm.call_panel(name="SEARCHTABS_PT_popover")
        return {'FINISHED'}

# --- UI DRAWING ---

class SEARCHTABS_PT_popover(bpy.types.Panel):
    bl_label = "Search Tabs"
    bl_idname = "SEARCHTABS_PT_popover"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 15

    def draw(self, context):
        layout = self.layout
        props = context.scene.searchtabs_props
        prefs = context.preferences.addons.get(__package__ or __name__)
        
        row = layout.row(align=True)
        if hasattr(row, "activate_init"): row.activate_init = True
        row.prop(props, "search_query", text="", icon='VIEWZOOM')

        query = props.search_query.lower()
        entries = sort_entries(get_all_tabs(context), context)
        limit = prefs.preferences.max_search_results if prefs else 25

        def draw_row(l, d, c, i):
            r = l.row(align=True)
            op = r.row(align=True).operator("searchtabs.switch_tab", text=d, icon=i)
            op.category_name, op.target_panel_label, op.icon_name = c, d, i
            if is_favorite(d): r.label(text="", icon='SOLO_ON')

        col = layout.column(align=True)
        if len(query) >= 2:
            cnt = 0
            for e in entries:
                if query in e['search']:
                    cnt += 1
                    if cnt > limit: break
                    draw_row(col, e['display'], e['cat'], 'NODE' if e['is_main'] else 'DOT')
            if cnt == 0: col.label(text="No results")
        elif len(query) == 1: col.label(text="Type 2+ chars...")
        else:
            for e in [x for x in entries if x['is_main']]:
                draw_row(col, e['display'], e['cat'], 'NODE')

def build_enum(self, context):
    items = []
    entries = sort_entries(get_all_tabs(context), context)
    for e in entries:
        uid = f"{e['cat']}::{e['display']}" if not e['is_main'] else e['cat']
        items.append((uid, e['display'], "", 'NODE' if e['is_main'] else 'DOT', len(items)))
    return items if items else [("", "No Tags", "", 'ERROR', 0)]

class SEARCHTABS_OT_search_popup(bpy.types.Operator):
    bl_idname = "searchtabs.search_popup"
    bl_label = "Search Sidebar Tab"
    bl_property = "search_enum"
    search_enum: bpy.props.EnumProperty(name="Tab", items=build_enum)
    def execute(self, context):
        if self.search_enum:
            cat = self.search_enum.split('::')[0]
            dname = self.search_enum.split('::')[1] if '::' in self.search_enum else self.search_enum
            bpy.ops.searchtabs.switch_tab(category_name=cat, target_panel_label=dname)
        return {'FINISHED'}
    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self); return {'RUNNING_MODAL'}

# --- PREFERENCES ---

class SEARCHTABS_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__ or __name__
    max_search_results: bpy.props.IntProperty(name="Max Search Results", default=25, min=1, max=500)
    default_sort_method: bpy.props.EnumProperty(name="Sort Method", items=[('ALPHABETICAL', "A-Z", ""), ('DATE', "Installation Date", ""), ('RECENT', "Recent", "")], default='ALPHABETICAL')
    sort_direction: bpy.props.EnumProperty(name="Sort Direction", items=[('ASCENDING', "Ascending", ""), ('DESCENDING', "Descending", "")], default='ASCENDING')

    def draw(self, context):
        l = self.layout
        box = l.box()
        box.label(text="General Settings", icon='SETTINGS')
        box.prop(self, "max_search_results")
        row = box.row(align=True)
        row.prop(self, "default_sort_method", text=""); row.prop(self, "sort_direction", text="")
        
        box = l.box(); box.label(text="Keyboard Shortcuts", icon='KEYINGSET')
        col, wm = box.column(), context.window_manager
        found = False
        for kc in wm.keyconfigs:
            km = kc.keymaps.get('3D View')
            if not km: continue
            for kmi in km.keymap_items:
                if kmi.idname in {"searchtabs.search_popup", "searchtabs.call_popover"}:
                    r = col.row()
                    r.label(text="Popup (F3-like)" if kmi.idname == "searchtabs.search_popup" else "Popover Menu")
                    r.prop(kmi, "type", text="", full_event=True); r.prop(kmi, "active", text="")
                    found = True
            if found: break

# --- UTILS ---

def get_addon_package(module_name):
    if not module_name: return ""
    parts = module_name.split(".")
    if parts[0] == "bl_ext": return ".".join(parts[:3]) if len(parts) >= 3 else ""
    if parts[0] in {"bpy", "bl_ui", "bl_operators", "bl_app_template_utils"}: return ""
    return parts[0]

def find_mod(c, l):
    if l != c:
        for p in bpy.types.Panel.__subclasses__():
            if (getattr(p, 'bl_space_type', None) == 'VIEW_3D' and getattr(p, 'bl_region_type', None) == 'UI' and getattr(p, 'bl_category', None) == c):
                label = getattr(p, 'bl_label', "")
                if l == label or l == f"{label} ({c})":
                    pkg = get_addon_package(p.__module__)
                    if pkg: return pkg
        return ""
    
    # Check if category contains built-ins
    has_builtin, addon_pkgs = False, set()
    for p in bpy.types.Panel.__subclasses__():
        if (getattr(p, 'bl_space_type', None) == 'VIEW_3D' and getattr(p, 'bl_region_type', None) == 'UI' and getattr(p, 'bl_category', None) == c):
            pkg = get_addon_package(p.__module__)
            if not pkg: has_builtin = True; break
            else: addon_pkgs.add(pkg)
                
    if has_builtin: return ""
    return list(addon_pkgs)[0] if len(addon_pkgs) == 1 else ""

class SEARCHTABS_OT_open_addon_prefs(bpy.types.Operator):
    bl_idname = "searchtabs.open_addon_prefs"; bl_label = "Open in Preferences"; bl_options = {'INTERNAL'}
    module: bpy.props.StringProperty()
    def execute(self, context):
        if self.module:
            try:
                bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
                context.preferences.active_section = 'ADDONS'
                bpy.ops.preferences.addon_show(module=self.module)
            except: pass
        return {'FINISHED'}

class SEARCHTABS_OT_open_addon_folder(bpy.types.Operator):
    bl_idname = "searchtabs.open_addon_folder"; bl_label = "Open in Explorer"; bl_options = {'INTERNAL'}
    module: bpy.props.StringProperty()
    def execute(self, context):
        if self.module and sys.platform == 'win32':
            m = sys.modules.get(self.module)
            if not m:
                try: m = importlib.import_module(self.module)
                except: pass
            if m and hasattr(m, "__file__") and m.__file__:
                mod_dir = os.path.dirname(m.__file__)
                if os.path.exists(mod_dir): subprocess.Popen(['explorer', os.path.normpath(mod_dir)])
        return {'FINISHED'}

# --- REGISTRATION ---

def draw_header(self, context):
    r = self.layout.row(align=True)
    r.operator("searchtabs.search_popup", text="", icon='VIEWZOOM')
    r.operator("searchtabs.call_popover", text="", icon='DISCLOSURE_TRI_DOWN')

def draw_context(self, context):
    op = getattr(context, "button_operator", None)
    if not op or not (hasattr(op, "target_panel_label") and hasattr(op, "category_name")): return
    
    d, c = op.target_panel_label, op.category_name
    m = find_mod(c, d)
    l = self.layout
    l.separator()
    l.operator("searchtabs.toggle_favorite", text="Remove from Favorites" if is_favorite(d) else "Add to Favorites", icon='SOLO_ON' if is_favorite(d) else 'SOLO_OFF').display_name = d
    if m:
        l.separator()
        l.operator("searchtabs.open_addon_prefs", icon='PREFERENCES').module = m
        l.operator("searchtabs.open_addon_folder", icon='FILE_FOLDER').module = m

classes = (SEARCHTABS_PG_history_item, SEARCHTABS_PG_properties, SEARCHTABS_OT_switch_tab, SEARCHTABS_OT_toggle_favorite, SEARCHTABS_OT_open_addon_prefs, SEARCHTABS_OT_open_addon_folder, SEARCHTABS_OT_call_popover, SEARCHTABS_OT_search_popup, SEARCHTABS_PT_popover, SEARCHTABS_AddonPreferences)
_KMS = []

def register():
    load_storage()
    for c in classes: bpy.utils.register_class(c)
    bpy.types.Scene.searchtabs_props = bpy.props.PointerProperty(type=SEARCHTABS_PG_properties)
    bpy.types.VIEW3D_HT_header.append(draw_header); bpy.types.WM_MT_button_context.append(draw_context)
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon or wm.keyconfigs.user
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        _KMS.append((km, km.keymap_items.new("searchtabs.search_popup", 'T', 'PRESS', shift=True, alt=True)))
        _KMS.append((km, km.keymap_items.new("searchtabs.call_popover", 'T', 'PRESS', ctrl=True, shift=True, alt=True)))

def unregister():
    save_storage()
    for km, kmi in _KMS: km.keymap_items.remove(kmi)
    _KMS.clear()
    bpy.types.VIEW3D_HT_header.remove(draw_header); bpy.types.WM_MT_button_context.remove(draw_context)
    for c in reversed(classes): bpy.utils.unregister_class(c)
    del bpy.types.Scene.searchtabs_props

if __name__ == "__main__": register()
