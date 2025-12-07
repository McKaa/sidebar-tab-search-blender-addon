bl_info = {
    "name": "Sidebar Tab Search",
    "author": "McKaa (Powered by Antigravity)",
    "version": (1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Header",
    "description": "Szybkie wyszukiwanie i przełączanie między kartami paska bocznego (N-Panel). / Quick search and switch between Sidebar (N-Panel) tabs.",
    "warning": "",
    "doc_url": "",
    "tracker_url": "https://github.com/McKaa/sidebar-tab-search-blender-addon",
    "support": "COMMUNITY",
    "category": "Interface",
    # Note: 'license' field is not standard in bl_info dictionary itself for display in list, 
    # but often added as comments or doc strings unless using specific repo requirements.
    # However, we can add it here if it's for internal clarity, though Blender executes it.
}

import bpy

# Grupa właściwości przechowująca zapytanie wyszukiwania
class SEARCHTABS_PG_properties(bpy.types.PropertyGroup):
    search_query: bpy.props.StringProperty(
        name="Wyszukaj kartę",
        description="Wpisz, aby wyszukać kartę paska bocznego",
        default="",
        options={'TEXTEDIT_UPDATE'}  # Aktualizuj przy każdym naciśnięciu klawisza lub po zatwierdzeniu
    )

# Operator do przełączania kategorii paska bocznego
class SEARCHTABS_OT_switch_tab(bpy.types.Operator):
    """Przełącz na wybraną kartę paska bocznego"""
    bl_idname = "searchtabs.switch_tab"
    bl_label = "Przełącz kartę"
    
    category_name: bpy.props.StringProperty()
    target_panel_label: bpy.props.StringProperty(default="")

    def execute(self, context):
        # 1. Upewnij się, że pasek boczny jest widoczny
        if context.space_data and context.space_data.type == 'VIEW_3D':
            # Jeśli pasek jest ukryty, pokaż go
            if not context.space_data.show_region_ui:
                context.space_data.show_region_ui = True

        # 2. Próba znalezienia regionu 'UI' (Sidebar) w aktywnym obszarze
        sidebar_region = None
        for region in context.area.regions:
            if region.type == 'UI':
                sidebar_region = region
                break
        
        if sidebar_region:
            try:
                # W Blenderze 4.0+ (i 5.0) używamy active_panel_category na regionie
                # Musimy to robić z try-except, bo czasem API zgłasza błąd read-only
                # jeśli region dopiero się otwiera.
                try:
                    sidebar_region.active_panel_category = self.category_name
                except TypeError:
                    # Fallback: czasem pomaga odświeżenie przed ustawieniem
                    pass
                except AttributeError:
                     # Starsze wersje / specyficzne błędy
                    pass

                # Ponowna próba (często potrzebna przy pierwszym otwarciu paska)
                if sidebar_region.active_panel_category != self.category_name:
                     sidebar_region.active_panel_category = self.category_name
                
                # Wymuś odświeżenie regionu
                sidebar_region.tag_redraw()
                
                # Próba przewinięcia widoku na górę
                with context.temp_override(area=context.area, region=sidebar_region):
                    try:
                        bpy.ops.view2d.scroll_up(deltas=100)
                    except Exception:
                        pass 

                return {'FINISHED'}
            except Exception as e:
                # Jeśli nadal jest błąd, zgłoś go, ale nie crashuj
                self.report({'WARNING'}, f"Ostrzeżenie: {e}")
                return {'FINISHED'} # Zwracamy finished, aby nie blokować UI
        else:
            self.report({'WARNING'}, "Nie znaleziono paska bocznego (Sidebar).")
            return {'CANCELLED'}

# Panel Popover (wyskakujące okienko)
class SEARCHTABS_PT_popover(bpy.types.Panel):
    """Tworzy wyskakujący panel wyszukiwania"""
    bl_label = "Szukaj Kart"
    bl_idname = "SEARCHTABS_PT_popover"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 14 # Nieco szersze okno dla długich nazw

    def draw(self, context):
        layout = self.layout
        props = context.scene.searchtabs_props

        # Pole wejściowe
        row = layout.row(align=True)
        row.prop(props, "search_query", text="", icon='VIEWZOOM')

        query = props.search_query.lower()

        # Zbieranie danych: Kategoria -> Lista Paneli (Etykiet)
        # Struktur: entries = [ {'search_text': "Auto Mirror", 'display': "Auto Mirror (Edit)", 'cat': "Edit"}, ... ]
        
        entries = []
        seen_categories = set()
        
        # 1. Najpierw iterujemy, aby zebrać unikalne panele z etykietami
        for panel in bpy.types.Panel.__subclasses__():
            if (hasattr(panel, 'bl_space_type') and panel.bl_space_type == 'VIEW_3D' and
                hasattr(panel, 'bl_region_type') and panel.bl_region_type == 'UI' and
                hasattr(panel, 'bl_category')):
                
                cat = panel.bl_category
                if cat == " Search": continue

                label = getattr(panel, 'bl_label', "")
                
                # Dodaj samą kategorię jako bazowy wynik (tylko raz)
                if cat not in seen_categories:
                    entries.append({
                        'search_text': cat.lower(),
                        'display': cat,
                        'cat': cat,
                        'is_main': True
                    })
                    seen_categories.add(cat)
                
                # Dodaj panel (podkategorię) jeśli ma etykietę inną niż kategoria
                if label and label != cat:
                    entries.append({
                        'search_text': f"{label} {cat}".lower(), # Pozwala szukać po obu
                        'display': f"{label} ({cat})",
                        'cat': cat,
                        'is_main': False
                    })

        # Sortowanie alfabetyczne
        entries.sort(key=lambda x: x['display'])

        # Wyświetlanie
        col = layout.column(align=True)
        
        found_count = 0
        if query:
            for entry in entries:
                if query in entry['search_text']:
                    found_count += 1
                    # Limit wyników, żeby nie muliło przy krótkim query
                    if found_count > 20:
                        break
                    
                    icon = 'NODE' if entry['is_main'] else 'DOT'
                    op = col.operator("searchtabs.switch_tab", text=entry['display'], icon=icon)
                    op.category_name = entry['cat']
            
            if found_count == 0:
                col.label(text="Brak wyników")
        else:
            col.label(text="Wpisz, aby szukać...")
            # Pokaż tylko główne kategorie gdy pusto
            main_cats = sorted([e for e in entries if e['is_main']], key=lambda x: x['display'])
            for entry in main_cats:
                op = col.operator("searchtabs.switch_tab", text=entry['display'], icon='NODE')
                op.category_name = entry['cat']

# Funkcja rysująca ikonkę w nagłówku
def draw_header_icon(self, context):
    layout = self.layout
    layout.popover(panel="SEARCHTABS_PT_popover", text="", icon='VIEWZOOM')

# Rejestracja
classes = (
    SEARCHTABS_PG_properties,
    SEARCHTABS_OT_switch_tab,
    SEARCHTABS_PT_popover,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.searchtabs_props = bpy.props.PointerProperty(type=SEARCHTABS_PG_properties)
    
    # Dodaj do nagłówka widoku 3D
    # Najpierw spróbuj usunąć, aby uniknąć duplikatów przy przeładowaniu w tej samej sesji
    try:
        bpy.types.VIEW3D_HT_header.remove(draw_header_icon)
    except ValueError:
        pass
    bpy.types.VIEW3D_HT_header.append(draw_header_icon)

def unregister():
    # Usuń z nagłówka
    try:
        bpy.types.VIEW3D_HT_header.remove(draw_header_icon)
    except ValueError:
        pass
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.searchtabs_props

if __name__ == "__main__":
    register()
