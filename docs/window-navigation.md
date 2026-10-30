# Keep related tasks in one main window

A House app should keep the current task and its saved records connected. Opening history or settings must leave a visible route back. Use the existing House controls and tokens for that navigation.

RTI uses one main window for Live, Sessions, Chats and Settings. Its recording header remains visible above every page. A user can read a saved chat, return to the selected session, change a setting and resume the live conversation without finding another window. Meeting briefs open as a dismissible sheet. About is a settings pane.

Navigation state belongs to the app's workspace. Recording, saved records and credentials keep their existing owners. Keep the live composer mounted across page changes so an unfinished question survives. Hide inactive content from hit testing, keyboard input and accessibility. Stop archive playback when leaving its page. Closing the main window keeps recording active.

Use the same route for a menu command, shortcut, deep link and button. A second settings controller must not become another settings implementation. Keep the library toggle available even when its sidebar is hidden. Show primary navigation in empty, loading and failure states too.

Quick Launch still benefits from its transient launcher and larger conversation window. Local Dictation still needs its recording pill beside the user's work. Those surfaces serve different tasks. Consolidate windows that split one task; keep a separate surface when its role requires it.

Before release, test the full return trip through every page, with a hidden sidebar and an empty or unavailable library. Check that a draft, the selected record and recording state survive. Verify menu commands and keyboard shortcuts against the visible page. Inspect light and dark renders at standard and minimum widths, then walk through the installed app.

Size and surface depth are part of the workspace contract. RTI starts at 860 by 660 points, with a 720 by 520 minimum. Page changes retain the frame. Use the sunken surface for chrome and sidebars, the standard surface for the workspace ground, and the raised surface for reading panels and settings cards. Existing card shadows, top highlights and inset spacing separate these layers in both appearances. Verify all pages at the same minimum, standard and larger sizes.
