from __future__ import annotations

import wx

from src.core.project_manager import ProjectItem
from src.ui.labels import (
    PRIORITY_OPTIONS,
    STATUS_OPTIONS,
    append_options,
    get_selected_value,
    priority_label,
    set_selected_value,
    status_label,
)


class NewItemDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, suggested_id: str) -> None:
        super().__init__(parent, title="新增检查项", size=(460, 320))

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=10, hgap=10)
        form.AddGrowableCol(1, 1)
        form.AddGrowableRow(1, 1)

        self.id_input = wx.TextCtrl(panel, value=suggested_id)
        self.content_input = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        self.status_choice = wx.Choice(panel)
        self.priority_choice = wx.Choice(panel)
        append_options(self.status_choice, STATUS_OPTIONS)
        append_options(self.priority_choice, PRIORITY_OPTIONS)
        set_selected_value(self.status_choice, "pending")
        set_selected_value(self.priority_choice, "medium")
        self.id_input.SetName("检查项编号")
        self.content_input.SetName("检查项内容")
        self.status_choice.SetName("检查项状态")
        self.priority_choice.SetName("检查项优先级")

        form.Add(wx.StaticText(panel, label="ID"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.id_input, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label="检查项"), 0, wx.ALIGN_TOP)
        form.Add(self.content_input, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label="状态"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.status_choice, 1, wx.EXPAND)
        form.Add(wx.StaticText(panel, label="优先级"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.priority_choice, 1, wx.EXPAND)

        root.Add(form, 1, wx.ALL | wx.EXPAND, 16)
        button_sizer = wx.StdDialogButtonSizer()
        ok_button = wx.Button(panel, wx.ID_OK)
        cancel_button = wx.Button(panel, wx.ID_CANCEL)
        ok_button.SetLabel("确定")
        cancel_button.SetLabel("取消")
        button_sizer.AddButton(ok_button)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()
        root.Add(button_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 16)
        panel.SetSizer(root)

    def build_item(self) -> ProjectItem:
        return ProjectItem(
            id=self.id_input.GetValue().strip(),
            content=self.content_input.GetValue().strip(),
            status=get_selected_value(self.status_choice, "pending"),
            priority=get_selected_value(self.priority_choice, "medium"),
        )


class RemarkDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, item: ProjectItem) -> None:
        super().__init__(parent, title=f"编辑备注 - {item.id}", size=(620, 420))
        self.item = item

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        summary = wx.StaticText(
            panel,
            label=(
                f"{item.id} ｜ {item.content}\n"
                f"状态：{status_label(item.status)} ｜ 优先级：{priority_label(item.priority)}"
            ),
        )
        self.remark_input = wx.TextCtrl(
            panel, value=item.description, style=wx.TE_MULTILINE
        )
        self.remark_input.SetName("备注内容")
        generate_button = wx.Button(panel, label="生成标准备注")
        generate_button.SetName("生成标准备注")

        button_sizer = wx.StdDialogButtonSizer()
        ok_button = wx.Button(panel, wx.ID_OK)
        cancel_button = wx.Button(panel, wx.ID_CANCEL)
        ok_button.SetLabel("确定")
        cancel_button.SetLabel("取消")
        button_sizer.AddButton(ok_button)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()

        root.Add(summary, 0, wx.ALL | wx.EXPAND, 16)
        root.Add(self.remark_input, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 16)
        root.Add(generate_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        root.Add(button_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 16)
        panel.SetSizer(root)

        generate_button.Bind(wx.EVT_BUTTON, self._on_generate)
        self.remark_input.SetFocus()

    @property
    def remark(self) -> str:
        return self.remark_input.GetValue().strip()

    def _on_generate(self, _event: wx.CommandEvent) -> None:
        description = (
            f"【问题概述】{self.item.content.strip()}\n"
            f"【当前结果】该项检查结果为 {status_label(self.item.status)}。\n"
            f"【影响等级】建议按 {priority_label(self.item.priority)} 优先级跟进修复。\n"
            f"【整改建议】请结合无障碍规范补充语义、键盘可达性、替代文本或状态提示，确保辅助技术可正确识别。"
        )
        self.remark_input.SetValue(description)
