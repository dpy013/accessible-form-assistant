from __future__ import annotations

import wx

from src.core.parser import TemplateDefinition, TemplateRepository
from src.core.utils import generate_project_number


class NewProjectWizard(wx.Dialog):
    def __init__(
        self, parent: wx.Window, template_repository: TemplateRepository
    ) -> None:
        super().__init__(parent, title="新建工程", size=(520, 320))
        self.template_repository = template_repository

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        description = wx.StaticText(
            panel,
            label="请依次输入工程名称、选择场景和模板。工程编号会自动生成并用于文件夹命名。",
        )
        form = wx.FlexGridSizer(cols=2, vgap=10, hgap=10)
        form.AddGrowableCol(1, 1)

        self.number_hint = wx.StaticText(
            panel, label=f"工程编号：{generate_project_number()}（自动生成）"
        )
        self.project_name_input = wx.TextCtrl(panel)
        self.scenario_choice = wx.ComboBox(
            panel,
            choices=self.template_repository.list_scenarios(),
            style=wx.CB_READONLY,
        )
        self.template_choice = wx.ComboBox(panel, style=wx.CB_READONLY)

        name_label = wx.StaticText(panel, label="工程名称")
        scenario_label = wx.StaticText(panel, label="场景")
        template_label = wx.StaticText(panel, label="模板")

        self.project_name_input.SetHint("可选，用于读屏和导出标题显示")
        self.project_name_input.SetName("工程名称")
        self.scenario_choice.SetName("场景选择")
        self.template_choice.SetName("模板选择")
        self.number_hint.SetName("自动生成工程编号")

        form.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.project_name_input, 1, wx.EXPAND)
        form.Add(scenario_label, 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.scenario_choice, 1, wx.EXPAND)
        form.Add(template_label, 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.template_choice, 1, wx.EXPAND)

        sizer.Add(description, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 16)
        sizer.Add(self.number_hint, 0, wx.ALL, 16)
        sizer.Add(form, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 16)
        button_sizer = wx.StdDialogButtonSizer()
        ok_button = wx.Button(panel, wx.ID_OK)
        cancel_button = wx.Button(panel, wx.ID_CANCEL)
        ok_button.SetLabel("确定")
        cancel_button.SetLabel("取消")
        button_sizer.AddButton(ok_button)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()
        sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 16)
        panel.SetSizer(sizer)

        self.scenario_choice.Bind(wx.EVT_COMBOBOX, self._on_scenario_changed)
        if self.scenario_choice.GetCount():
            self.scenario_choice.SetSelection(0)
            self._populate_templates()
        self.project_name_input.SetFocus()

    def _on_scenario_changed(self, _event: wx.CommandEvent) -> None:
        self._populate_templates()

    def _populate_templates(self) -> None:
        self.template_choice.Clear()
        for template in self.template_repository.list_templates(self.selected_scenario):
            self.template_choice.Append(template.name, clientData=template)
        if self.template_choice.GetCount():
            self.template_choice.SetSelection(0)

    @property
    def selected_scenario(self) -> str:
        return self.scenario_choice.GetStringSelection()

    @property
    def selected_template(self) -> TemplateDefinition:
        selection = self.template_choice.GetSelection()
        if selection == wx.NOT_FOUND:
            raise RuntimeError("当前场景下没有可用模板。")
        return self.template_choice.GetClientData(selection)

    @property
    def project_name(self) -> str:
        return self.project_name_input.GetValue().strip()
