# Poprawka: Filtrowanie paneli według dostępności w kontekście

## Problem

Wtyczka wyświetlała wszystkie kategorie paneli zarejestrowane w Blenderze, niezależnie od tego, czy były dostępne w aktualnym kontekście (tryb obiektu, tryb edycji, itp.).

**Objawy:**

- Kliknięcie na niektóre kategorie (np. "Paint") nie powodowało żadnej akcji
- W konsoli pojawiał się komunikat błędu:

  ```
  Warning: bpy_struct: item.attr = val: enum "Paint" not found in (...)
  ```

**Przyczyna:**
Kategoria "Paint" (i inne) są widoczne tylko w określonych trybach (np. Sculpt Mode, Texture Paint Mode), ale wtyczka próbowała przełączyć się na nie nawet w Object Mode, gdzie nie są dostępne.

## Rozwiązanie

Dodano **filtrowanie paneli według dostępności w kontekście** przy użyciu metody `poll()`:

### 1. W funkcji `draw()` (popover panel)

```python
# Check if panel is available in current context
if hasattr(panel, 'poll'):
    try:
        if not panel.poll(context):
            continue  # Skip panels not available in current context
    except Exception:
        # If poll fails, skip this panel
        continue
```

**Efekt:** Teraz w wynikach wyszukiwania pokazują się **tylko te kategorie i panele, które są dostępne w aktualnym kontekście**.

### 2. W operatorze `SEARCHTABS_OT_switch_tab.execute()`

```python
# Get list of available categories in current context
available_categories = []
for panel in bpy.types.Panel.__subclasses__():
    # ... sprawdzanie typu i regionu ...
    
    # Check if panel is available in current context
    if hasattr(panel, 'poll'):
        try:
            if not panel.poll(context):
                continue
        except Exception:
            continue
    
    cat = panel.bl_category
    if cat not in available_categories:
        available_categories.append(cat)

# Check if requested category is available
if self.category_name not in available_categories:
    self.report({'WARNING'}, f"Category '{self.category_name}' is not available in current context")
    return {'CANCELLED'}
```

**Efekt:** Nawet jeśli użytkownik jakoś kliknie na niedostępną kategorię, operator sprawdzi dostępność przed próbą przełączenia i wyświetli ostrzeżenie zamiast błędu.

## Przykłady

### Przed poprawką

- **Object Mode**: Pokazywało kategorie: Item, Edit, Tool, View, Paint, Sculpt, ...
- **Kliknięcie "Paint"**: Błąd + brak akcji

### Po poprawce

- **Object Mode**: Pokazuje tylko: Item, Edit, Tool, View, ... (bez Paint, Sculpt)
- **Sculpt Mode**: Pokazuje: Item, Tool, View, Paint, Sculpt, ...
- **Kliknięcie dowolnej kategorii**: Działa poprawnie

## Metoda poll()

Każdy panel w Blenderze może mieć metodę `poll(context)`, która określa, czy panel powinien być widoczny w danym kontekście:

```python
class MY_PT_Panel(bpy.types.Panel):
    # ...
    
    @classmethod
    def poll(cls, context):
        # Panel widoczny tylko w Object Mode
        return context.mode == 'OBJECT'
```

Nasza poprawka wykorzystuje tę metodę do filtrowania wyników.

## Testowanie

Aby przetestować poprawkę:

1. **Object Mode**: Otwórz wyszukiwarkę - nie powinno być kategorii "Paint"
2. **Sculpt Mode** (`Ctrl+Tab` → Sculpting): Otwórz wyszukiwarkę - kategoria "Paint" powinna być widoczna
3. **Edit Mode** (`Tab`): Otwórz wyszukiwarkę - kategorie dostosowane do trybu edycji

## Commit

```
d33579c - Fix: Filter panels by context availability using poll() to prevent unavailable category errors
```

## Dodatkowe informacje

- Poprawka jest **wstecznie kompatybilna** - nie zmienia API ani struktury danych
- Nie wpływa na wydajność - sprawdzanie `poll()` jest szybkie
- Działa ze wszystkimi trybami Blendera (Object, Edit, Sculpt, Texture Paint, itp.)
