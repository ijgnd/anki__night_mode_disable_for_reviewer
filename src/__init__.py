# -*- coding: utf-8 -*-
"""
Copyright (c) 2020 ijgnd
              2020 Lovac42 (toolbar.py)


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from anki.hooks import addHook, wrap
from anki.lang import _

from aqt import gui_hooks
from aqt import mw
from aqt.addcards import AddCards
from aqt.browser import Browser
from aqt.editor import Editor
from aqt.qt import (
    QKeySequence,
    QMenu,
    QObjectCleanupHandler,
)
from aqt.reviewer import Reviewer
from aqt.theme import theme_manager
from aqt.utils import tooltip

from .toolbar import getMenu


MENU_NAME = "NM_Toggle"  # "&View"


def gc(arg, fail=False):
    conf = mw.addonManager.getConfig(__name__)
    if conf:
        return conf.get(arg, fail)
    return fail


def toggle_nm_from_browser(browser):
    theme_manager.night_mode ^= True
    ed = browser.editor
    ed.web = None
    ed.cleanup()
    # https://stackoverflow.com/questions/4528347/clear-all-widgets-in-a-layout-in-pyqt
    for i in reversed(range(ed.outerLayout.count())): 
        ed.outerLayout.itemAt(i).widget().setParent(None)
    ed.setupWeb()
    ed.setupTags()
    ed.setNote(browser.card.note(reload=True), focusTo=ed.currentField)


def browserSetupMenus(self):
    menu = getMenu(self, MENU_NAME)
    a = menu.addAction('toggle night_only (this mostly affects the editor/reviewer')
    a.triggered.connect(lambda _, b=self: toggle_nm_from_browser(b))
    cut = gc("shortcut toggle", "")
    if cut:
        a.setShortcut(QKeySequence(cut))
addHook("browser.setupMenus", browserSetupMenus)


def _toggle_nm_from_editor(editor, field):
    theme_manager.night_mode ^= True
    # nid = editor.note.id
    editor.web = None
    # https://stackoverflow.com/questions/4528347/clear-all-widgets-in-a-layout-in-pyqt
    for i in reversed(range(editor.outerLayout.count())): 
        editor.outerLayout.itemAt(i).widget().setParent(None)
    editor.setupWeb()
    editor.setupTags()
    editor.setNote(editor.note, focusTo=field)


def toggle_nm_from_editor(editor):
    field = editor.currentField
    editor.saveNow(lambda e=editor, f=field: _toggle_nm_from_editor(e, f))
    

def SetupShortcuts(cuts, editor):
    # Shortcut for editor in browser is already defined in browser so I may not define it twice
    # otherwise I'd get: "QAction::event: Ambiguous shortcut overload"
    if isinstance(editor.parentWindow, Browser):
        return
    shortcut = gc("shortcut toggle")
    if shortcut:
        cuts.append((shortcut, lambda e=editor: toggle_nm_from_editor(e)))
addHook("setupEditorShortcuts", SetupShortcuts)


def reload_reviewer():
    rwr = mw.reviewer
    rwr._reps -= 1
    rwr._initWeb()
    rwr._showQuestion()


def toggle_nm_from_main():
    theme_manager.night_mode ^= True
    if mw.state == "review":
        reload_reviewer()
    elif mw.state == "deckBrowser":
        mw.moveToState("deckBrowser")
    elif mw.state == "overview":
         mw.moveToState("deckBrowser")
    else:
        tooltip(f"state is: {mw.state}")


def mainSetupMenus():
    menu = getMenu(mw, MENU_NAME)
    a = menu.addAction('toggle night_only (this mostly affects the editor/reviewer')
    a.triggered.connect(toggle_nm_from_main)
    cut = gc("shortcut toggle", "")
    if cut:
        a.setShortcut(QKeySequence(cut))
addHook("profileLoaded", mainSetupMenus)


"""
# without hooks:
nm_temp_switched = False
def _showQuestion(self):
    global nm_temp_switched
    note = self.card.note()
    for e in gc("reviewer: disable night mode for these tags"):
        if e in note.tags:
            theme_manager.night_mode = False
            nm_temp_switched = True
            break
Reviewer._showQuestion = wrap(Reviewer._showQuestion, _showQuestion, "before")
"""

nm_temp_switched = False
def maybe_override_nm_for_card(munged, card, kind):
    global nm_temp_switched
    if not kind == "reviewQuestion":
        return munged
    note = card.note()
    for e in gc("reviewer: disable night mode for these tags"):
        if e in note.tags:
            theme_manager.night_mode = False
            nm_temp_switched = True
            break
    return munged
gui_hooks.card_will_show.append(maybe_override_nm_for_card)


def revert_nm_override_after_answer(reviewer, card, ease):
    global nm_temp_switched
    if nm_temp_switched:
        theme_manager.night_mode = True
        nm_temp_switched ^= True
gui_hooks.reviewer_did_answer_card.append(revert_nm_override_after_answer)


def revert_nm_on_undo_review(cid):
    global nm_temp_switched
    if nm_temp_switched:
        theme_manager.night_mode = True
        nm_temp_switched ^= True
gui_hooks.review_did_undo.append(revert_nm_on_undo_review)


def revert_nm_on_state_change(new_state, old_state):
    print(f'in revert_nm_on_state_change, to: {new_state}')
    global nm_temp_switched
    if nm_temp_switched:
        theme_manager.night_mode = True
        nm_temp_switched ^= True
        if new_state == "deckBrowser":
            mw.deckBrowser.show()
gui_hooks.state_did_change.append(revert_nm_on_state_change)
