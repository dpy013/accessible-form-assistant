from __future__ import annotations

import wx

from src.core.project_manager import ProjectConfig, ToolSettings


class ProjectConfigDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, config: ProjectConfig) -> None:
        super().__init__(parent, title="自定义配置", size=(620, 460))
        self.result_config = config

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        description = wx.StaticText(
            panel,
            label="工具设置和自定义配置会保存到当前工程目录的 config.xml 文件中。",
        )
        self.hide_completed = wx.CheckBox(panel, label="默认隐藏已完成")
        self.show_trash = wx.CheckBox(panel, label="默认显示回收站")
        self.custom_config_input = wx.TextCtrl(panel, style=wx.TE_MULTILINE)

        self.hide_completed.SetValue(config.tool_settings.hide_completed)
        self.show_trash.SetValue(config.tool_settings.show_trash)
        self.custom_config_input.SetValue(self._serialize_custom_settings(config))

        self.hide_completed.SetName("默认隐藏已完成")
        self.show_trash.SetName("默认显示回收站")
        self.custom_config_input.SetName("自定义配置")
        self.custom_config_input.SetHint("每行一个 key=value，例如 export.author=Alice")

        root.Add(description, 0, wx.ALL | wx.EXPAND, 16)
        root.Add(self.hide_completed, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        root.Add(self.show_trash, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        root.Add(
            wx.StaticText(panel, label="自定义配置（每行一个 key=value）"),
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM,
            16,
        )
        root.Add(self.custom_config_input, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 16)

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
        self.custom_config_input.SetFocus()
        ok_button.Bind(wx.EVT_BUTTON, self._on_confirm)

    def build_config(self) -> ProjectConfig:
        return self.result_config

    def _on_confirm(self, _event: wx.CommandEvent) -> None:
        try:
            self.result_config = ProjectConfig(
                tool_settings=ToolSettings(
                    hide_completed=self.hide_completed.GetValue(),
                    show_trash=self.show_trash.GetValue(),
                ),
                custom_settings=self._parse_custom_settings(),
            )
        except ValueError as exc:
            wx.MessageBox(str(exc), "配置格式错误", wx.OK | wx.ICON_WARNING, self)
            return
        self.EndModal(wx.ID_OK)

    def _parse_custom_settings(self) -> dict[str, str]:
        settings: dict[str, str] = {}
        for line_number, raw_line in enumerate(
            self.custom_config_input.GetValue().splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line:
                continue
            if "=" not in line:
                raise ValueError(f"第 {line_number} 行缺少 = ：{raw_line}")
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                raise ValueError(f"第 {line_number} 行的键不能为空。")
            settings[key] = value
        return settings

    def _serialize_custom_settings(self, config: ProjectConfig) -> str:
        return "\n".join(
            f"{key}={value}" for key, value in config.custom_settings.items()
        )
