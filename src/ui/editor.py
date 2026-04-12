from __future__ import annotations

from collections.abc import Callable

import wx

from src.core.project_manager import ProjectItem
from src.ui.labels import (
    PRIORITY_OPTIONS,
    append_options,
    get_selected_value,
    set_selected_value,
    STATUS_OPTIONS,
)


class ItemEditorPanel(wx.Panel):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent)
        self.current_item: ProjectItem | None = None
        self.on_change: Callable[[], None] | None = None
        self.on_paste_image: Callable[[], str] | None = None
        self._loading = False

        root = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        form.AddGrowableCol(1, 1)
        form.AddGrowableRow(4, 1)

        self.id_text = wx.StaticText(self, label="-")
        self.content_text = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.status_choice = wx.ComboBox(self, style=wx.CB_READONLY)
        self.priority_choice = wx.ComboBox(self, style=wx.CB_READONLY)
        self.image_path = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.paste_button = wx.Button(self, label="从剪贴板粘贴截图")
        append_options(self.status_choice, STATUS_OPTIONS)
        append_options(self.priority_choice, PRIORITY_OPTIONS)
        self.content_text.SetName("检查项内容")
        self.status_choice.SetName("检查项状态")
        self.priority_choice.SetName("检查项优先级")
        self.image_path.SetName("截图路径")
        self.paste_button.SetName("从剪贴板粘贴截图")

        form.Add(wx.StaticText(self, label="ID"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.id_text, 1, wx.EXPAND)
        form.Add(wx.StaticText(self, label="检查项"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.content_text, 1, wx.EXPAND)
        form.Add(wx.StaticText(self, label="状态"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.status_choice, 1, wx.EXPAND)
        form.Add(wx.StaticText(self, label="优先级"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.priority_choice, 1, wx.EXPAND)
        form.Add(wx.StaticText(self, label="截图路径"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.image_path, 1, wx.EXPAND)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        button_row.Add(self.paste_button, 0)

        root.Add(form, 1, wx.ALL | wx.EXPAND, 12)
        root.Add(button_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.SetSizer(root)

        for control, event in (
            (self.content_text, wx.EVT_TEXT),
            (self.status_choice, wx.EVT_COMBOBOX),
            (self.priority_choice, wx.EVT_COMBOBOX),
        ):
            control.Bind(event, self._emit_change)

        self.paste_button.Bind(wx.EVT_BUTTON, self._on_paste_image)
        self.enable_fields(False)

    def bind_handlers(
        self,
        on_change: Callable[[], None],
        on_paste_image: Callable[[], str],
    ) -> None:
        self.on_change = on_change
        self.on_paste_image = on_paste_image

    def load_item(self, item: ProjectItem | None) -> None:
        self._loading = True
        self.current_item = item
        enabled = item is not None
        self.enable_fields(enabled)

        if item is None:
            self.id_text.SetLabel("-")
            self.content_text.SetValue("")
            self.status_choice.SetSelection(wx.NOT_FOUND)
            self.priority_choice.SetSelection(wx.NOT_FOUND)
            self.image_path.SetValue("")
            self._loading = False
            return

        self.id_text.SetLabel(item.id)
        self.content_text.SetValue(item.content)
        set_selected_value(self.status_choice, item.status)
        set_selected_value(self.priority_choice, item.priority)
        self.image_path.SetValue(item.image_path)
        self._loading = False

    def write_back(self) -> None:
        if not self.current_item:
            return

        self.current_item.content = self.content_text.GetValue().strip()
        self.current_item.status = get_selected_value(self.status_choice, "pending")
        self.current_item.priority = get_selected_value(self.priority_choice, "medium")
        self.current_item.image_path = self.image_path.GetValue().strip()

    def enable_fields(self, enabled: bool) -> None:
        for control in (
            self.content_text,
            self.status_choice,
            self.priority_choice,
            self.image_path,
            self.paste_button,
        ):
            control.Enable(enabled)

    def _emit_change(self, _event) -> None:
        if self._loading:
            return
        self.write_back()
        if self.on_change:
            self.on_change()

    def _on_paste_image(self, _event: wx.CommandEvent) -> None:
        if not self.current_item or not self.on_paste_image:
            return
        relative_path = self.on_paste_image()
        if not relative_path:
            return
        self.image_path.SetValue(relative_path)
        self.write_back()
        if self.on_change:
            self.on_change()
