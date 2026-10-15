# Home TV changes

## 1.0.2

One Left from the channel list explicitly focuses the top menu. The active menu
has an underline and a contextual remote hint; the channel row loses its white
highlight while the menu has focus. Down restores the same channel selection.
The playing-channel text colour fix from 1.0.1 is preserved.

## 1.0.1

Use the author's `Color_SelectedText` include for the three labels in a focused
channel row. It supplies both `textcolor` and `selectedcolor`: Kodi can apply
the latter to the channel currently playing. Previously that state inherited
white text, making number, channel name and programme disappear on the white
highlight. The existing theme colours and navigation are preserved.

## 1.0.0

Initial channel-list Home with native PVR content and the Arctic top menu.
