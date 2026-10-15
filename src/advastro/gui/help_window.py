"""The manual inside the app: chapters and sections on the left, the text on the right.

One window is shared by the whole app. F1 anywhere opens it at the section for what the
user is looking at; the "?" on a finding opens that finding's entry. Searching filters the
sections and highlights the words in the text.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QKeySequence,
    QPalette,
    QShortcut,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from advastro import APP_NAME, __version__
from advastro import help as manual
from advastro.gui import icons
from advastro.gui.theme import DARK, Theme
from advastro.i18n import current_language, tr

_window: HelpWindow | None = None


def show_help(topic: str = "intro", parent: QWidget | None = None) -> HelpWindow:
    """Open (or raise) the help window at a topic id such as 'rate.verdict'."""
    global _window
    if _window is None:
        theme = getattr(parent.window(), "theme", DARK) if parent is not None else DARK
        _window = HelpWindow(theme)
    _window.show_topic(topic)
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window


def set_help_theme(theme: Theme) -> None:
    if _window is not None:
        _window.set_theme(theme)


def show_about(parent: QWidget) -> None:
    QMessageBox.about(parent, tr("help.about_title"), tr("help.about_text", version=__version__))


def add_help_shortcut(widget: QWidget, topic_for) -> QShortcut:
    """F1 on a window opens help; topic_for() returns the topic for the current view."""
    sc = QShortcut(QKeySequence(QKeySequence.StandardKey.HelpContents), widget)
    sc.setContext(Qt.ShortcutContext.WindowShortcut)
    sc.activated.connect(lambda: show_help(topic_for(), widget))
    return sc


class HelpWindow(QMainWindow):
    def __init__(self, theme: Theme) -> None:
        super().__init__(None, Qt.WindowType.Window)
        self.lang = current_language()
        self.theme = theme
        self.chapter = None
        self.setWindowTitle(f"{tr('help.title')} — {APP_NAME}")
        self.setWindowIcon(icons.app_icon())
        self.resize(1100, 780)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.setCentralWidget(split)

        left = QFrame()
        left.setObjectName("panel")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 12, 8, 12)
        lv.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("help.search"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        lv.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.itemClicked.connect(lambda item: self.show_topic(item.data(0, 256)))
        lv.addWidget(self.tree, 1)
        self.no_hits = QLabel(tr("help.no_hits"))
        self.no_hits.setObjectName("statLabel")
        self.no_hits.setWordWrap(True)
        self.no_hits.hide()
        lv.addWidget(self.no_hits)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(28, 10, 16, 4)
        self.crumb = QLabel("")
        self.crumb.setObjectName("statLabel")
        bar.addWidget(self.crumb, 1)
        rv.addLayout(bar)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._link)
        self.browser.setFrameShape(QFrame.Shape.NoFrame)
        self.browser.document().setDocumentMargin(26)
        rv.addWidget(self.browser, 1)
        split.addWidget(right)
        split.setSizes([300, 800])

        self._build_tree()
        self.set_theme(theme)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self, self.search.setFocus)

    # ---- content ---------------------------------------------------------------
    def _build_tree(self) -> None:
        self.tree.clear()
        self.items = {}
        for ch in manual.chapters(self.lang):
            top = QTreeWidgetItem([ch.title])
            top.setData(0, 256, ch.key)
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            self.items[ch.key] = top
            parent_for_level = {1: top}
            for sec in ch.sections[1:]:
                if sec.level > 3 and not sec.id.startswith("finding."):
                    continue
                parent = parent_for_level.get(sec.level - 1) or top
                item = QTreeWidgetItem([sec.title])
                item.setData(0, 256, sec.id)
                parent.addChild(item)
                parent_for_level[sec.level] = item
                self.items[sec.id] = item

    def set_theme(self, theme: Theme) -> None:
        self.theme = t = theme
        pal = self.browser.palette()
        pal.setColor(QPalette.ColorRole.Link, QColor(t.accent))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor(t.accent))
        self.browser.setPalette(pal)
        self.setWindowIcon(icons.app_icon())
        if self.chapter is not None:
            self._render(self.chapter)

    def _render(self, chapter) -> None:
        self.chapter = chapter
        self._target = None
        doc = self.browser.document()
        doc.setMarkdown(chapter.markdown)
        # Tables: a little padding reads much better than Qt's default.
        from PySide6.QtGui import QTextTableFormat

        block = doc.begin()
        seen = set()
        while block.isValid():
            cursor = self.browser.textCursor()
            cursor.setPosition(block.position())
            level = block.blockFormat().headingLevel()
            code = block.blockFormat().nonBreakableLines()
            if not cursor.currentTable() and not code:
                bf = block.blockFormat()
                bf.setTopMargin({1: 4, 2: 20, 3: 16, 4: 14}.get(level, bf.topMargin()))
                bf.setBottomMargin(6 if level else max(bf.bottomMargin(), 6))
                bf.setLineHeight(118, 1)      # proportional line height, 118 %
                cursor.setBlockFormat(bf)
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid() and frag.charFormat().isAnchor():
                    c2 = self.browser.textCursor()
                    c2.setPosition(frag.position())
                    c2.setPosition(frag.position() + frag.length(), c2.MoveMode.KeepAnchor)
                    cf = frag.charFormat()
                    cf.setForeground(QColor(self.theme.accent))
                    cf.setFontUnderline(False)
                    c2.setCharFormat(cf)
                it += 1
            table = cursor.currentTable()
            if table is not None and id(table) not in seen:
                seen.add(id(table))
                fmt = table.format()
                if isinstance(fmt, QTextTableFormat):
                    fmt.setCellPadding(5)
                    fmt.setCellSpacing(0)
                    fmt.setBorder(0.5)
                    fmt.setBorderBrush(QColor(self.theme.border))
                    table.setFormat(fmt)
            block = block.next()
        self._highlight()

    def show_topic(self, topic: str) -> None:
        found = manual.locate(topic or "intro", self.lang)
        if found is None:
            found = manual.locate("intro", self.lang)
        chapter, section = found
        if chapter is not self.chapter:
            self._render(chapter)
        self._scroll_to(section.title, section.level)
        item = self.items.get(section.id) or self.items.get(chapter.key)
        if item is not None:
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)
        self.crumb.setText(chapter.title if section.id == chapter.key
                           else f"{chapter.title}  ›  {section.title}")

    def _scroll_to(self, title: str, level: int) -> None:
        doc = self.browser.document()
        block = doc.begin()
        while block.isValid():
            if block.blockFormat().headingLevel() > 0 and block.text().strip() == title:
                break
            block = block.next()
        sb = self.browser.verticalScrollBar()
        if not block.isValid() or level == 1:
            sb.setValue(0)
            return
        cursor = self.browser.textCursor()
        cursor.setPosition(block.position())
        self.browser.setTextCursor(cursor)
        def to_top() -> None:
            sb.setValue(sb.maximum())    # bring the heading to the top, not just into view
            self.browser.ensureCursorVisible()

        to_top()
        QTimer.singleShot(0, to_top)     # again once the new text has been laid out
        # Mark the heading, so it is easy to spot near the end of a chapter.
        cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
        self._target = QTextEdit.ExtraSelection()
        self._target.cursor = cursor
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.theme.accent))
        self._target.format = fmt
        self._highlight()

    def _link(self, url: QUrl) -> None:
        if url.scheme() == "help":
            self.show_topic(url.path().strip("/") or url.host())
        else:
            QDesktopServices.openUrl(url)

    # ---- search ------------------------------------------------------------------
    def _filter(self, text: str) -> None:
        text = text.strip()
        hits = {sec.id for _, sec in manual.search(text, self.lang)} if text else None
        any_hit = False
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            child_hit = self._filter_item(top, hits)
            top_hit = hits is None or top.data(0, 256) in hits or child_hit
            top.setHidden(not top_hit)
            top.setExpanded(hits is not None and child_hit)
            any_hit |= top_hit
        self.no_hits.setVisible(not any_hit)
        if hits:
            first = next((self.items[k] for k in self.items if k in hits), None)
            if first is not None:
                self.show_topic(first.data(0, 256))
        self._highlight()

    def _filter_item(self, item, hits) -> bool:
        shown = False
        for i in range(item.childCount()):
            child = item.child(i)
            sub = self._filter_item(child, hits)
            hit = hits is None or child.data(0, 256) in hits or sub
            child.setHidden(not hit)
            child.setExpanded(hits is not None and sub)
            shown |= hit
        return shown

    def _highlight(self) -> None:
        words = [w for w in self.search.text().split() if len(w) > 1]
        target = getattr(self, "_target", None)
        sels = [target] if target is not None and target.cursor.document() is \
            self.browser.document() else []
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(self.theme.warn_tint))
        fmt.setForeground(QColor(self.theme.warn))
        doc = self.browser.document()
        for w in words:
            cur = doc.find(w)
            while not cur.isNull() and len(sels) < 400:
                sel = QTextEdit.ExtraSelection()
                sel.cursor, sel.format = cur, fmt
                sels.append(sel)
                cur = doc.find(w, cur)
        self.browser.setExtraSelections(sels)

    def sizeHint(self) -> QSize:
        return QSize(1100, 780)
