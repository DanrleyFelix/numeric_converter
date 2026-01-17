from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, h_spacing=10, v_spacing=10):
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def add_item(self, item):
        self._items.append(item)

    def addItem(self, item):
        # Qt chama esse método internamente
        self.add_item(item)

    def count(self):
        return len(self._items)

    def item_at(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def itemAt(self, index):
        # Qt chama esse método internamente
        return self.item_at(index)

    def take_at(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def takeAt(self, index):
        # Qt chama esse método internamente
        return self.take_at(index)

    def expanding_directions(self):
        return Qt.Orientations(0)

    def expandingDirections(self):
        return self.expanding_directions()

    def has_height_for_width(self):
        return True

    def hasHeightForWidth(self):
        return self.has_height_for_width()

    def height_for_width(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def heightForWidth(self, width):
        return self.height_for_width(width)

    def set_geometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def setGeometry(self, rect):
        self.set_geometry(rect)

    def size_hint(self):
        return self.minimum_size()

    def sizeHint(self):
        return self.size_hint()

    def minimum_size(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def minimumSize(self):
        return self.minimum_size()

    def _do_layout(self, rect, test_only=False):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)

        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width()

            if next_x > effective_rect.right() + 1 and line_height > 0:
                x = effective_rect.x()
                y += line_height + self._v_spacing
                next_x = x + hint.width()
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = next_x + self._h_spacing
            line_height = max(line_height, hint.height())

        return (y + line_height - effective_rect.y()) + top + bottom
