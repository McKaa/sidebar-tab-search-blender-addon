bl_info = {
    "name": "Sidebar Tab Search",
    "author": "McKaa (Powered by Antigravity)",
    "version": (1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Header",
    "description": "Quick search and switch between Sidebar (N-Panel) tabs.",
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

# Property group storing the search query
class SEARCHTABS_PG_properties(bpy.types.PropertyGroup):
    search_query: bpy.props.StringProperty(
        name="Search Tab",
        description="Type to search sidebar tabs",
        default="",
        options={'TEXTEDIT_UPDATE'}  # Update on every keystroke or after confirmation
    )

# Operator to switch sidebar category
class SEARCHTABS_OT_switch_tab(bpy.types.Operator):
    """Switch to selected sidebar tab"""
    bl_idname = "searchtabs.switch_tab"
    bl_label = "Switch Tab"
    
    category_name: bpy.props.StringProperty()
    target_panel_label: bpy.props.StringProperty(default="")

    def execute(self, context):
        # 1. Make sure the sidebar is visible
        if context.space_data and context.space_data.type == 'VIEW_3D':
            # If the sidebar is hidden, show it
            if not context.space_data.show_region_ui:
                context.space_data.show_region_ui = True

        # 2. Try to find the 'UI' region (Sidebar) in the active area
        sidebar_region = None
        for region in context.area.regions:
            if region.type == 'UI':
                sidebar_region = region
                break
        
        if sidebar_region:
            try:
                # Get list of available categories in current context
                available_categories = []
                for panel in bpy.types.Panel.__subclasses__():
                    if (hasattr(panel, 'bl_space_type') and panel.bl_space_type == 'VIEW_3D' and
                        hasattr(panel, 'bl_region_type') and panel.bl_region_type == 'UI' and
                        hasattr(panel, 'bl_category')):
                        
                        # Check if panel is available in current context
                        if hasattr(panel, 'poll'):
                            try:
                                if not panel.poll(context):
                                    continue
                            except Exception:
                                # If poll fails, skip this panel
                                continue
                        
                        cat = panel.bl_category
                        if cat not in available_categories:
                            available_categories.append(cat)
                
                # Check if requested category is available
                if self.category_name not in available_categories:
                    self.report({'WARNING'}, f"Category '{self.category_name}' is not available in current context")
                    return {'CANCELLED'}
                
                # In Blender 4.0+ (and 5.0) we use active_panel_category on the region
                # We need to do this with try-except, because sometimes the API raises a read-only error
                # if the region is just opening.
                try:
                    sidebar_region.active_panel_category = self.category_name
                except TypeError:
                    # Fallback: sometimes refreshing before setting helps
                    pass
                except AttributeError:
                     # Older versions / specific errors
                    pass

                # Retry (often needed on first sidebar opening)
                if sidebar_region.active_panel_category != self.category_name:
                     sidebar_region.active_panel_category = self.category_name
                
                # Force region refresh
                sidebar_region.tag_redraw()
                
                # Try to scroll the view to the top
                with context.temp_override(area=context.area, region=sidebar_region):
                    try:
                        bpy.ops.view2d.scroll_up(deltas=100)
                    except Exception:
                        pass 

                return {'FINISHED'}
            except Exception as e:
                # If there's still an error, report it but don't crash
                self.report({'WARNING'}, f"Warning: {e}")
                return {'FINISHED'} # Return finished to not block the UI
        else:
            self.report({'WARNING'}, "Sidebar not found.")
            return {'CANCELLED'}

# Popover Panel (popup window)
class SEARCHTABS_PT_popover(bpy.types.Panel):
    """Creates a search popover panel"""
    bl_label = "Search Tabs"
    bl_idname = "SEARCHTABS_PT_popover"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 14 # Slightly wider window for long names

    def draw(self, context):
        layout = self.layout
        props = context.scene.searchtabs_props

        # Input field
        row = layout.row(align=True)
        row.prop(props, "search_query", text="", icon='VIEWZOOM')

        query = props.search_query.lower()

        # Collecting data: Category -> List of Panels (Labels)
        # Structure: entries = [ {'search_text': "Auto Mirror", 'display': "Auto Mirror (Edit)", 'cat': "Edit"}, ... ]
        
        entries = []
        seen_categories = set()
        
        # 1. First iterate to collect unique panels with labels (only those available in current context)
        for panel in bpy.types.Panel.__subclasses__():
            if (hasattr(panel, 'bl_space_type') and panel.bl_space_type == 'VIEW_3D' and
                hasattr(panel, 'bl_region_type') and panel.bl_region_type == 'UI' and
                hasattr(panel, 'bl_category')):
                
                # Check if panel is available in current context
                if hasattr(panel, 'poll'):
                    try:
                        if not panel.poll(context):
                            continue  # Skip panels not available in current context
                    except Exception:
                        # If poll fails, skip this panel
                        continue
                
                cat = panel.bl_category
                if cat == " Search": continue

                label = getattr(panel, 'bl_label', "")
                
                # Add the category itself as a base result (only once)
                if cat not in seen_categories:
                    entries.append({
                        'search_text': cat.lower(),
                        'display': cat,
                        'cat': cat,
                        'is_main': True
                    })
                    seen_categories.add(cat)
                
                # Add panel (subcategory) if it has a label different from the category
                if label and label != cat:
                    entries.append({
                        'search_text': f"{label} {cat}".lower(), # Allows searching by both
                        'display': f"{label} ({cat})",
                        'cat': cat,
                        'is_main': False
                    })

        # Alphabetical sorting
        entries.sort(key=lambda x: x['display'])

        # Display
        col = layout.column(align=True)
        
        found_count = 0
        if query:
            for entry in entries:
                if query in entry['search_text']:
                    found_count += 1
                    # Limit results to avoid clutter with short queries
                    if found_count > 20:
                        break
                    
                    icon = 'NODE' if entry['is_main'] else 'DOT'
                    op = col.operator("searchtabs.switch_tab", text=entry['display'], icon=icon)
                    op.category_name = entry['cat']
            
            if found_count == 0:
                col.label(text="No results")
        else:
            col.label(text="Type to search...")
            # Show only main categories when empty
            main_cats = sorted([e for e in entries if e['is_main']], key=lambda x: x['display'])
            for entry in main_cats:
                op = col.operator("searchtabs.switch_tab", text=entry['display'], icon='NODE')
                op.category_name = entry['cat']

# Function to draw the icon in the header
def draw_header_icon(self, context):
    layout = self.layout
    layout.popover(panel="SEARCHTABS_PT_popover", text="", icon='VIEWZOOM')

# Registration
classes = (
    SEARCHTABS_PG_properties,
    SEARCHTABS_OT_switch_tab,
    SEARCHTABS_PT_popover,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.searchtabs_props = bpy.props.PointerProperty(type=SEARCHTABS_PG_properties)
    
    # Add to 3D view header
    # First try to remove to avoid duplicates when reloading in the same session
    try:
        bpy.types.VIEW3D_HT_header.remove(draw_header_icon)
    except ValueError:
        pass
    bpy.types.VIEW3D_HT_header.append(draw_header_icon)

def unregister():
    # Remove from header
    try:
        bpy.types.VIEW3D_HT_header.remove(draw_header_icon)
    except ValueError:
        pass
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.searchtabs_props

if __name__ == "__main__":
    register()
