# Sidebar Tab Search (Blender Add-on)

Quickly search and switch between Sidebar (N-Panel) tabs in Blender's 3D Viewport.

![Screenshot](sidebar-tab-search_ico_256px.png)

## Why Two Search Modes? (Popup vs Popover)

This add-on provides two distinct ways to find and switch tabs, catering to different workflows:

### 1. Popup Search (Shift + Alt + T) - The "F3-like" Experience

- **Focus**: Pure speed and efficiency.
- **Behavior**: Opens a floating search box (standard Blender search style).
- **Auto-Close**: Once you select a result, the window **closes immediately**.
- **Best for**: Rapid switching when you know exactly where you want to go.

### 2. Popover Menu (Ctrl + Shift + Alt + T) - The Permanent Hub

- **Focus**: Organization and exploration.
- **Behavior**: Opens as a panel from the header.
- **Persistent Interaction**: Does not close automatically, allowing you to quickly switch between multiple tabs or manage your favorites without reopening the menu.
- **Favorites & History**: While both modes use the same sorting, the Popover is ideal for managing your list.

## Core Features

- **Blazing Fast Search**: Find any sidebar tab or panel instantly.
- **Header Integration**: Minimalist magnifying glass icon in the 3D View header.
- **Favorites System**: Keep your most-used tabs at the top. Right-click any result to "Add to Favorites".
- **Search History**: Automatically prioritizes your recent searches (when "Recent" sort is active).
- **Context Menu Utilities**: Right-click any result to:
  - **Add/Remove Favorites**.
  - **Open in Preferences**: Jump straight to that addon's settings.
  - **Open in Explorer**: Open the source folder of the addon.

## Usage

1. **Invoke**: Click the magnifying glass icon or use the shortcuts mentioned above.
2. **Search**: Start typing (minimum 2 characters).
3. **Switch**: Click on any result to instantly navigate to that sidebar tab.
4. **Manage**: Use the Right-Click menu for advanced options.

## Compatibility

- **Blender 4.2+** (Fully compatible with the Extensions system).
- Support for Blender 5.0 and 5.01+.

> [!IMPORTANT]
> **Blender 5.0+ Note**: Starting with version 5.0, Blender changed the default behavior of menus and popovers—they no longer close automatically when the mouse leaves.
> To restore the classic behavior (auto-closing on mouse leave), go to **Edit > Preferences > Interface > Menus** and enable **"Close Menus on Leave"**.

## Installation

1. Download the `sidebar_tab_search.zip`.
2. In Blender: **Edit > Preferences > Get Extensions**.
3. Click the gear/arrow icon and select **Install from Disk...**.
4. Select the `.zip` file.
