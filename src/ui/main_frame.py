from __future__ import annotations

import ctypes
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import wx
import wx.dataview as dv

from src.core.app_state import AppStateManager
from src.core.exporter import ProjectExporter
from src.core.importer import ImportedProject, ProjectImporter
from src.core.parser import TemplateRepository
from src.core.project_manager import ProjectItem, ProjectManager, ProjectSession
from src.ui.config_dialog import ProjectConfigDialog
from src.ui.editor import ItemEditorPanel
from src.ui.item_dialog import NewItemDialog, RemarkDialog
from src.ui.labels import priority_label, status_label
from src.ui.wizard import NewProjectWizard

WM_SYSCOMMAND = 0x0112
SC_KEYMENU = 0xF100
GUI_INMENUMODE = 0x00000004
MenuHandler = Callable[[wx.Event | None], None]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("hwndActive", ctypes.c_void_p),
        ("hwndFocus", ctypes.c_void_p),
        ("hwndCapture", ctypes.c_void_p),
        ("hwndMenuOwner", ctypes.c_void_p),
        ("hwndMoveSize", ctypes.c_void_p),
        ("hwndCaret", ctypes.c_void_p),
        ("rcCaret", RECT),
    ]


class MainFrame(wx.Frame):
    def __init__(
        self, workspace: Path, template_repository: TemplateRepository
    ) -> None:
        super().__init__(None, title="信息无障碍表格填写助手", size=(1320, 820))
        self.workspace = workspace
        self.template_repository = template_repository
        self.project_manager = ProjectManager(workspace)
        self.app_state = AppStateManager(workspace)
        self.exporter = ProjectExporter()
        self.importer = ProjectImporter()
        self.session: ProjectSession | None = None
        self.view_items: list[ProjectItem] = []
        self.summary_labels: dict[str, wx.StaticText] = {}
        self._alt_combo_used = False
        self._alt_pressed = False
        self._dirty = False
        self._list_focus_row_before_menu: int | None = None
        self._list_focus_row_before_deactivate: int | None = None
        self._list_focus_restore_pending = False
        self._opening_menu_with_alt = False
        self._restart_pending = False

        self.CreateStatusBar()
        self._build_menu()
        self._build_layout()
        self._bind_alt_hook_recursively(self)
        self._build_timer()
        self._update_project_actions()

        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_MENU_OPEN, self._on_menu_open)
        self.Bind(wx.EVT_MENU_CLOSE, self._on_menu_close)
        self._update_title()
        wx.CallAfter(self._restore_recent_project)

    def _build_menu(self) -> None:
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        new_menu = wx.Menu()
        new_item = new_menu.Append(wx.ID_NEW, "新建工程\tCtrl+N")
        self._append_menu_actions(new_menu, self._new_project_file_actions())
        file_menu.AppendSubMenu(new_menu, "新建")

        open_menu = wx.Menu()
        open_project_item = open_menu.Append(wx.ID_OPEN, "打开已有工程\tCtrl+O")
        self.Bind(wx.EVT_MENU, self.on_open_project, open_project_item)
        open_menu.AppendSeparator()
        self._append_menu_actions(open_menu, self._open_file_actions())
        file_menu.AppendSubMenu(open_menu, "打开")

        export_menu = wx.Menu()
        self._append_menu_actions(export_menu, self._export_actions())
        file_menu.AppendSubMenu(export_menu, "导出")
        file_menu.AppendSeparator()
        close_item = file_menu.Append(wx.ID_CLOSE, "关闭工程\tCtrl+W")
        save_item = file_menu.Append(wx.ID_SAVE, "保存\tCtrl+S")
        config_item = file_menu.Append(wx.ID_PREFERENCES, "自定义配置\tCtrl+,")
        clean_item = file_menu.Append(wx.ID_ANY, "清理工程目录")
        add_issue_item = file_menu.Append(wx.ID_ADD, "新增检查项\tCtrl+I")
        file_menu.AppendSeparator()
        restart_item = file_menu.Append(wx.ID_ANY, "重启\tCtrl+R")
        exit_item = file_menu.Append(wx.ID_EXIT, "退出\tAlt+F4")
        menu_bar.Append(file_menu, "文件")

        self.Bind(wx.EVT_MENU, self.on_new_project, new_item)
        self.Bind(wx.EVT_MENU, self.on_close_project, close_item)
        self.Bind(wx.EVT_MENU, self.on_save, save_item)
        self.Bind(wx.EVT_MENU, self.on_edit_project_config, config_item)
        self.Bind(wx.EVT_MENU, self.on_clean_project_directory, clean_item)
        self.Bind(wx.EVT_MENU, self.on_add_item, add_issue_item)
        self.Bind(wx.EVT_MENU, self.on_restart_app, restart_item)
        self.Bind(wx.EVT_MENU, self.on_exit_app, exit_item)
        self.SetMenuBar(menu_bar)

    def _build_layout(self) -> None:
        self.action_bar = wx.Panel(self)
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.new_button = wx.Button(self.action_bar, label="新建工程")
        self.open_button = wx.Button(self.action_bar, label="打开")
        self.save_button = wx.Button(self.action_bar, label="保存")
        self.config_button = wx.Button(self.action_bar, label="自定义配置")
        self.add_button = wx.Button(self.action_bar, label="新增检查项")
        self.delete_button = wx.Button(self.action_bar, label="删除")
        self.restore_button = wx.Button(self.action_bar, label="还原")
        self.hide_completed = wx.CheckBox(self.action_bar, label="隐藏已完成")
        self.show_trash = wx.CheckBox(self.action_bar, label="显示回收站")

        for control, accessible_name in (
            (self.new_button, "新建工程按钮"),
            (self.open_button, "打开按钮"),
            (self.save_button, "保存按钮"),
            (self.config_button, "自定义配置按钮"),
            (self.add_button, "新增检查项按钮"),
            (self.delete_button, "删除按钮"),
            (self.restore_button, "还原按钮"),
            (self.hide_completed, "隐藏已完成复选框"),
            (self.show_trash, "显示回收站复选框"),
        ):
            control.SetName(accessible_name)
            action_sizer.Add(control, 0, wx.ALL, 6)

        self.action_bar.SetSizer(action_sizer)
        self.new_button.Bind(wx.EVT_BUTTON, self.on_new_project)
        self.open_button.Bind(wx.EVT_BUTTON, self.on_open_menu)
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save)
        self.config_button.Bind(wx.EVT_BUTTON, self.on_edit_project_config)
        self.add_button.Bind(wx.EVT_BUTTON, self.on_add_item)
        self.delete_button.Bind(wx.EVT_BUTTON, self.on_soft_delete)
        self.restore_button.Bind(wx.EVT_BUTTON, self.on_restore)
        self.hide_completed.Bind(wx.EVT_CHECKBOX, self._on_filter_changed)
        self.show_trash.Bind(wx.EVT_CHECKBOX, self._on_filter_changed)

        splitter = wx.SplitterWindow(self)
        left_panel = wx.Panel(splitter)
        right_panel = wx.Panel(splitter)

        left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.project_hint = wx.StaticText(
            left_panel,
            label="当前未打开工程。请使用上方按钮新建、打开工程或打开文件创建工程。",
        )
        self.project_hint.SetName("当前工程说明")
        summary_panel = wx.Panel(left_panel)
        summary_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for key, label in (
            ("total", "总数"),
            ("passed", "通过"),
            ("failed", "失败"),
            ("pending", "待处理"),
            ("deleted", "回收站"),
        ):
            block = wx.BoxSizer(wx.VERTICAL)
            value_label = wx.StaticText(summary_panel, label="0")
            value_label.SetFont(
                wx.Font(
                    12,
                    wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            )
            title_label = wx.StaticText(summary_panel, label=label)
            block.Add(value_label, 0, wx.ALIGN_CENTER_HORIZONTAL)
            block.Add(title_label, 0, wx.ALIGN_CENTER_HORIZONTAL)
            summary_sizer.Add(block, 1, wx.ALL | wx.EXPAND, 8)
            self.summary_labels[key] = value_label
        summary_panel.SetSizer(summary_sizer)
        self.list_ctrl = dv.DataViewListCtrl(
            left_panel, style=dv.DV_ROW_LINES | dv.DV_VERT_RULES
        )
        self.list_ctrl.SetName("检查项列表")
        self.list_ctrl.AppendTextColumn("ID", width=170)
        self.list_ctrl.AppendTextColumn("检查项", width=380)
        self.list_ctrl.AppendTextColumn("状态", width=120)
        self.list_ctrl.AppendTextColumn("优先级", width=100)
        self.list_ctrl.AppendTextColumn("截图", width=220)
        left_sizer.Add(self.project_hint, 0, wx.ALL, 8)
        left_sizer.Add(summary_panel, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        left_sizer.Add(self.list_ctrl, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        left_panel.SetSizer(left_sizer)

        right_sizer = wx.BoxSizer(wx.VERTICAL)
        self.editor = ItemEditorPanel(right_panel)
        self.editor.bind_handlers(
            self._on_editor_changed, self._paste_image_from_clipboard
        )
        right_sizer.Add(self.editor, 1, wx.EXPAND)
        right_panel.SetSizer(right_sizer)

        splitter.SplitVertically(left_panel, right_panel, sashPosition=760)
        splitter.SetMinimumPaneSize(360)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(self.action_bar, 0, wx.ALL | wx.EXPAND, 8)
        frame_sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)

        self.list_ctrl.Bind(
            dv.EVT_DATAVIEW_SELECTION_CHANGED, self._on_selection_changed
        )
        self.list_ctrl.Bind(wx.EVT_CONTEXT_MENU, self._on_list_context_menu)

    def _build_timer(self) -> None:
        self.backup_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_backup_timer, self.backup_timer)
        self.backup_timer.Start(5 * 60 * 1000)

    def _restore_recent_project(self) -> None:
        latest_project = self.app_state.latest_project()
        if latest_project and latest_project.exists():
            try:
                self._load_session(self.project_manager.load_project(latest_project))
                self.SetStatusText(f"已恢复最近工程：{latest_project.name}")
                return
            except Exception:
                try:
                    self.app_state.forget_project(latest_project)
                except Exception:
                    pass
                self.SetStatusText("最近工程恢复失败，请重新选择。")
        self.SetStatusText("当前未打开工程。可按 Alt+F 使用菜单，或使用窗口顶部按钮。")

    def _append_menu_actions(
        self, menu: wx.Menu, actions: list[tuple[str, MenuHandler]]
    ) -> None:
        for label, handler in actions:
            menu_item = menu.Append(wx.ID_ANY, label)
            self.Bind(wx.EVT_MENU, handler, menu_item)

    def _new_project_file_actions(self) -> list[tuple[str, MenuHandler]]:
        return [
            (f"从 {label} 创建工程", import_handler)
            for label, import_handler, _export_handler in self._file_format_actions()
        ]

    def _open_file_actions(self) -> list[tuple[str, MenuHandler]]:
        return [
            (f"打开 {label} 文件创建工程", import_handler)
            for label, import_handler, _export_handler in self._file_format_actions()
        ]

    def _export_actions(self) -> list[tuple[str, MenuHandler]]:
        return [
            (f"导出 {label}", export_handler)
            for label, _import_handler, export_handler in self._file_format_actions()
        ]

    def _file_format_actions(self) -> list[tuple[str, MenuHandler, MenuHandler]]:
        return [
            ("HTML", self.on_import_html, self.on_export_html),
            ("Word", self.on_import_word, self.on_export_word),
            ("Excel", self.on_import_excel, self.on_export_excel),
            ("CSV", self.on_import_jira_csv, self.on_export_jira_csv),
            ("Markdown", self.on_import_markdown, self.on_export_markdown),
        ]

    def on_new_project(self, _event: wx.Event | None = None) -> None:
        if not self._can_discard_or_save_changes():
            return
        dialog = NewProjectWizard(self, self.template_repository)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        template = dialog.selected_template
        items = [
            ProjectItem(
                id=item.id,
                content=item.content,
                status=item.status,
                description=item.description,
                image_path=item.image_path,
                priority=item.priority,
                deleted=item.deleted,
            )
            for item in template.items
        ]
        self.session = self.project_manager.create_project(
            scenario=template.scenario,
            template_name=template.name,
            items=items,
            project_name=dialog.project_name,
        )
        dialog.Destroy()
        self._load_session(self.session)

    def on_open_project(self, _event: wx.Event | None = None) -> None:
        if not self._can_discard_or_save_changes():
            return

        dialog = wx.DirDialog(self, "选择工程目录", defaultPath=str(self.workspace))
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        project_root = Path(dialog.GetPath())
        dialog.Destroy()
        try:
            session = self.project_manager.load_project(project_root)
        except Exception as exc:
            wx.MessageBox(f"打开工程失败：{exc}", "错误", wx.OK | wx.ICON_ERROR, self)
            return
        self._load_session(session)

    def on_open_menu(self, _event: wx.Event | None = None) -> None:
        menu = wx.Menu()
        open_project_item = menu.Append(wx.ID_OPEN, "打开已有工程")
        menu.Bind(wx.EVT_MENU, self.on_open_project, open_project_item)
        menu.AppendSeparator()
        for label, handler in self._open_file_actions():
            menu_item = menu.Append(wx.ID_ANY, label)
            menu.Bind(wx.EVT_MENU, handler, menu_item)

        button_position = self.open_button.GetPosition()
        button_size = self.open_button.GetSize()
        popup_position = wx.Point(
            button_position.x, button_position.y + button_size.height
        )
        self.action_bar.PopupMenu(menu, popup_position)
        menu.Destroy()

    def on_save(self, _event: wx.Event | None = None) -> None:
        if not self.session:
            return
        self._save_session()

    def on_close_project(self, _event: wx.Event | None = None) -> None:
        if not self.session:
            return
        if not self._can_discard_or_save_changes():
            return
        self._unload_session()
        self.SetStatusText("已关闭当前工程")

    def on_clean_project_directory(self, _event: wx.Event | None = None) -> None:
        if not self.session:
            return

        result = wx.MessageBox(
            "将清理当前工程目录中的导出文件和临时文件，并保留 project.json、config.xml、assets、backup，是否继续？",
            "确认清理",
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
            self,
        )
        if result != wx.YES:
            return

        removed = self.project_manager.clean_project_directory(self.session)
        if not removed:
            self.SetStatusText("当前工程目录无需清理")
            return
        self.SetStatusText(f"已清理 {len(removed)} 个项目文件")

    def on_edit_project_config(self, _event: wx.Event | None = None) -> None:
        if not self.session:
            wx.MessageBox(
                "请先新建或打开工程，然后再设置自定义配置。",
                "提示",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return

        dialog = ProjectConfigDialog(self, self.session.config)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        self.session.config = dialog.build_config()
        dialog.Destroy()
        self._apply_project_config()
        self.project_manager.save_config(self.session)
        self._refresh_view(preserve_selection=True)
        self.SetStatusText("已保存自定义配置")

    def on_add_item(self, _event: wx.Event | None = None) -> None:
        if not self.session:
            return

        existing_ids = {item.id for item in self.session.data.items}
        dialog = NewItemDialog(self, suggested_id=self._next_item_id(existing_ids))
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        item = dialog.build_item()
        dialog.Destroy()
        if not item.id or not item.content:
            wx.MessageBox(
                "检查项 ID 和内容不能为空。", "提示", wx.OK | wx.ICON_INFORMATION, self
            )
            return
        if item.id in existing_ids:
            wx.MessageBox(
                "检查项 ID 已存在，请使用新的 ID。",
                "提示",
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return

        self.session.data.items.append(item)
        self._dirty = True
        self._refresh_view(target_item_id=item.id)
        self._save_session(status_message=f"已新增检查项：{item.id}")

    def on_export_html(self, _event: wx.Event) -> None:
        self._export(
            "HTML 文件 (*.html)|*.html", "report.html", self.exporter.export_html
        )

    def on_import_html(self, _event: wx.Event) -> None:
        self._import_project("HTML 文件 (*.html)|*.html", "html")

    def on_import_word(self, _event: wx.Event) -> None:
        self._import_project("Word 文件 (*.docx)|*.docx", "word")

    def on_import_excel(self, _event: wx.Event) -> None:
        self._import_project("Excel 文件 (*.xlsx)|*.xlsx", "excel")

    def on_import_jira_csv(self, _event: wx.Event) -> None:
        self._import_project("CSV 文件 (*.csv)|*.csv", "jira_csv")

    def on_import_markdown(self, _event: wx.Event) -> None:
        self._import_project("Markdown 文件 (*.md)|*.md", "markdown")

    def on_export_word(self, _event: wx.Event) -> None:
        self._export(
            "Word 文件 (*.docx)|*.docx", "report.docx", self.exporter.export_word
        )

    def on_export_excel(self, _event: wx.Event) -> None:
        self._export(
            "Excel 文件 (*.xlsx)|*.xlsx", "report.xlsx", self.exporter.export_excel
        )

    def on_export_jira_csv(self, _event: wx.Event) -> None:
        self._export(
            "CSV 文件 (*.csv)|*.csv", "jira_issues.csv", self.exporter.export_jira_csv
        )

    def on_export_markdown(self, _event: wx.Event) -> None:
        self._export(
            "Markdown 文件 (*.md)|*.md", "report.md", self.exporter.export_markdown
        )

    def on_restart_app(self, _event: wx.Event | None = None) -> None:
        if not self._can_discard_or_save_changes():
            return

        app_root = Path(__file__).resolve().parents[2]
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command.extend(["-m", "src.main"])
        command.extend(["--workspace", str(self.workspace)])

        subprocess.Popen(command, cwd=str(app_root))
        self._restart_pending = True
        self.Close()

    def on_exit_app(self, _event: wx.Event | None = None) -> None:
        self.Close()

    def on_soft_delete(self, _event: wx.Event | None = None) -> None:
        item = self._selected_item()
        if not item:
            return
        item.deleted = True
        self._save_session(status_message=f"已移入回收站：{item.id}")
        self._refresh_view()

    def on_restore(self, _event: wx.Event | None = None) -> None:
        item = self._selected_item()
        if not item:
            return
        item.deleted = False
        self._save_session(status_message=f"已还原：{item.id}")
        self._refresh_view(target_item_id=item.id)

    def _on_filter_changed(self, _event: wx.CommandEvent) -> None:
        self._sync_project_config_from_controls()
        if self.session:
            self.project_manager.save_config(self.session)
        self._refresh_view()

    def _on_selection_changed(self, _event: dv.DataViewEvent) -> None:
        self.editor.load_item(self._selected_item())

    def _on_list_context_menu(self, _event: wx.ContextMenuEvent) -> None:
        item = self._selected_item()
        if not item:
            return

        menu = wx.Menu()
        remark_item = menu.Append(wx.ID_ANY, "编辑备注")
        if item.deleted:
            delete_restore_item = menu.Append(wx.ID_ANY, "还原")
            menu.Bind(wx.EVT_MENU, self.on_restore, delete_restore_item)
        else:
            delete_restore_item = menu.Append(wx.ID_ANY, "删除")
            menu.Bind(wx.EVT_MENU, self.on_soft_delete, delete_restore_item)
        menu.Bind(wx.EVT_MENU, self.on_edit_remark, remark_item)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_edit_remark(self, _event: wx.Event | None = None) -> None:
        item = self._selected_item()
        if not item:
            return

        dialog = RemarkDialog(self, item)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        item.description = dialog.remark
        dialog.Destroy()
        self._dirty = True
        self._save_session(status_message=f"已更新备注：{item.id}")

    def _on_editor_changed(self) -> None:
        if not self.session:
            return
        self.editor.write_back()
        self._dirty = True
        self._refresh_view(preserve_selection=True)
        self.SetStatusText("有未保存修改")

    def _save_session(self, status_message: str = "已保存") -> None:
        if not self.session:
            return
        self.editor.write_back()
        self._sync_project_config_from_controls()
        self.project_manager.save_project(self.session)
        self.app_state.remember_project(self.session.root)
        self._dirty = False
        self._refresh_view(preserve_selection=True)
        self.SetStatusText(status_message)

    def _load_session(self, session: ProjectSession) -> None:
        self.session = session
        self.app_state.remember_project(session.root)
        self._dirty = False
        self._apply_project_config()
        self._update_project_actions()
        self._refresh_view(focus_list=True)
        self._update_title()

    def _unload_session(self) -> None:
        self.session = None
        self.view_items = []
        self._dirty = False
        self.hide_completed.SetValue(False)
        self.show_trash.SetValue(False)
        self._update_project_actions()
        self.list_ctrl.DeleteAllItems()
        self.editor.load_item(None)
        self.project_hint.SetLabel(
            "当前未打开工程。请使用上方按钮新建、打开工程或打开文件创建工程。"
        )
        self._update_summary()
        self._update_title()

    def _refresh_view(
        self,
        preserve_selection: bool = False,
        target_item_id: str | None = None,
        focus_list: bool = False,
    ) -> None:
        if not self.session:
            self.list_ctrl.DeleteAllItems()
            self.editor.load_item(None)
            self._update_summary()
            self._update_title()
            return

        current_focus = wx.Window.FindFocus()
        should_restore_list_focus = focus_list or (
            current_focus is not None
            and (
                current_focus == self.list_ctrl
                or self.list_ctrl.IsDescendant(current_focus)
            )
        )
        current_item = self._selected_item()
        selected_id = target_item_id or (
            current_item.id if preserve_selection and current_item else None
        )
        display_name = self.session.data.meta.project_name or "未命名工程"
        self.project_hint.SetLabel(f"{display_name} ｜ {self.session.root}")
        self.list_ctrl.DeleteAllItems()

        self.view_items = []
        for item in self.session.data.items:
            if self.hide_completed.GetValue() and item.status == "passed":
                continue
            if self.show_trash.GetValue():
                if not item.deleted:
                    continue
            elif item.deleted:
                continue

            self.view_items.append(item)
            self.list_ctrl.AppendItem(
                [
                    item.id,
                    item.content,
                    status_label(item.status),
                    priority_label(item.priority),
                    item.image_path or "-",
                ]
            )

        self._update_summary()
        if not self.view_items:
            self.editor.load_item(None)
            self._update_title()
            return

        target_row = 0
        if selected_id:
            for index, item in enumerate(self.view_items):
                if item.id == selected_id:
                    target_row = index
                    break

        self.list_ctrl.SelectRow(target_row)
        self.editor.load_item(self.view_items[target_row])
        self._update_title()
        if should_restore_list_focus:
            wx.CallAfter(self._focus_list_row, target_row)

    def _selected_item(self) -> ProjectItem | None:
        row = self.list_ctrl.GetSelectedRow()
        if row == wx.NOT_FOUND or row >= len(self.view_items):
            return None
        return self.view_items[row]

    def _apply_project_config(self) -> None:
        if not self.session:
            return
        self.hide_completed.SetValue(self.session.config.tool_settings.hide_completed)
        self.show_trash.SetValue(self.session.config.tool_settings.show_trash)

    def _sync_project_config_from_controls(self) -> None:
        if not self.session:
            return
        self.session.config.tool_settings.hide_completed = (
            self.hide_completed.GetValue()
        )
        self.session.config.tool_settings.show_trash = self.show_trash.GetValue()

    def _update_project_actions(self) -> None:
        has_session = self.session is not None
        for control in (
            self.save_button,
            self.config_button,
            self.add_button,
            self.delete_button,
            self.restore_button,
            self.hide_completed,
            self.show_trash,
        ):
            control.Enable(has_session)

    def _focus_list_row(self, row: int) -> None:
        if row < 0 or row >= len(self.view_items):
            return
        self.list_ctrl.SetFocus()
        self.list_ctrl.SelectRow(row)

    def _has_list_focus(self) -> bool:
        current_focus = wx.Window.FindFocus()
        return bool(
            current_focus is not None
            and (
                current_focus == self.list_ctrl
                or self.list_ctrl.IsDescendant(current_focus)
            )
        )

    def _selected_list_row(self) -> int | None:
        if not self.view_items:
            return None
        row = self.list_ctrl.GetSelectedRow()
        if row == wx.NOT_FOUND:
            return 0
        return row

    def _paste_image_from_clipboard(self) -> str:
        if not self.session:
            return ""

        data = wx.BitmapDataObject()
        if not wx.TheClipboard.Open():
            wx.MessageBox("无法打开剪贴板。", "提示", wx.OK | wx.ICON_WARNING, self)
            return ""
        try:
            if not wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                wx.MessageBox(
                    "剪贴板中没有位图内容。", "提示", wx.OK | wx.ICON_INFORMATION, self
                )
                return ""
            wx.TheClipboard.GetData(data)
        finally:
            wx.TheClipboard.Close()

        return self.project_manager.save_bitmap_asset(self.session, data.GetBitmap())

    def _export(self, wildcard: str, default_name: str, exporter) -> None:
        if not self.session:
            return
        self._save_session()

        dialog = wx.FileDialog(
            self,
            message="选择导出位置",
            defaultDir=str(self.session.root),
            defaultFile=default_name,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        target = Path(dialog.GetPath())
        dialog.Destroy()
        try:
            exporter(self.session, target)
        except Exception as exc:
            wx.MessageBox(str(exc), "导出失败", wx.OK | wx.ICON_ERROR, self)
            return
        wx.MessageBox(
            f"已导出到：{target}", "导出完成", wx.OK | wx.ICON_INFORMATION, self
        )

    def _import_project(self, wildcard: str, format_name: str) -> None:
        if not self._can_discard_or_save_changes():
            return

        dialog = wx.FileDialog(
            self,
            message="选择要导入的文件",
            defaultDir=str(self.workspace),
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        source_path = Path(dialog.GetPath())
        dialog.Destroy()

        try:
            imported = self.importer.import_file(source_path, format_name)
        except Exception as exc:
            wx.MessageBox(f"导入失败：{exc}", "错误", wx.OK | wx.ICON_ERROR, self)
            return

        self._create_project_from_import(imported, source_path)

    def _create_project_from_import(
        self, imported: ImportedProject, source_path: Path
    ) -> None:
        project_name = imported.data.meta.project_name or source_path.stem
        scenario = imported.data.meta.scenario or "导入"
        template_name = imported.data.meta.template or f"{imported.source_format} 导入"
        items = [
            ProjectItem(
                id=item.id,
                content=item.content,
                status=item.status,
                description=item.description,
                image_path=item.image_path,
                priority=item.priority,
                deleted=item.deleted,
            )
            for item in imported.data.items
        ]
        session = self.project_manager.create_project(
            scenario=scenario,
            template_name=template_name,
            items=items,
            project_name=project_name,
        )
        self._load_session(session)
        self.SetStatusText(f"已从 {source_path.name} 创建工程")

    def _on_backup_timer(self, _event: wx.TimerEvent) -> None:
        if not self.session or not self._dirty:
            return
        self._save_session(status_message="已自动保存")
        self.project_manager.backup_project(self.session)

    def _update_title(self) -> None:
        if not self.session:
            self.SetTitle("信息无障碍表格填写助手")
            return
        meta = self.session.data.meta
        dirty_flag = " *" if self._dirty else ""
        name_part = f" {meta.project_name}" if meta.project_name else ""
        self.SetTitle(
            f"当前项目: {meta.project_number}{name_part} [{meta.scenario}] - 信息无障碍表格填写助手{dirty_flag}"
        )

    def _on_close(self, event: wx.CloseEvent) -> None:
        if self._restart_pending:
            event.Skip()
            return
        if not self._can_discard_or_save_changes():
            event.Veto()
            return
        event.Skip()

    def _on_key_down(self, event: wx.KeyEvent) -> None:
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_ALT:
            self._alt_pressed = True
            self._alt_combo_used = False
        elif self._alt_pressed:
            self._alt_combo_used = True
        event.Skip()

    def _on_key_up(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_ALT:
            should_open_menu = self._alt_pressed and not self._alt_combo_used
            self._reset_alt_state()
            if should_open_menu:
                wx.CallAfter(self._open_file_menu_with_alt)
        event.Skip()

    def _bind_alt_hook_recursively(self, window: wx.Window) -> None:
        window.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        window.Bind(wx.EVT_KEY_UP, self._on_key_up)
        for child in window.GetChildren():
            self._bind_alt_hook_recursively(child)

    def _update_summary(self) -> None:
        counts = {"total": 0, "passed": 0, "failed": 0, "pending": 0, "deleted": 0}
        if self.session:
            counts["total"] = len(self.session.data.items)
            for item in self.session.data.items:
                if item.deleted:
                    counts["deleted"] += 1
                if item.status == "passed":
                    counts["passed"] += 1
                elif item.status == "failed":
                    counts["failed"] += 1
                else:
                    counts["pending"] += 1
        for key, control in self.summary_labels.items():
            control.SetLabel(str(counts[key]))

    def _next_item_id(self, existing_ids: set[str]) -> str:
        index = 1
        while True:
            candidate = f"CUSTOM_{index:03d}"
            if candidate not in existing_ids:
                return candidate
            index += 1

    def _can_discard_or_save_changes(self) -> bool:
        if not self.session or not self._dirty:
            return True

        result = wx.MessageBox(
            "当前工程有未保存修改，是否先保存？",
            "提示",
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
            self,
        )
        if result == wx.YES:
            self._save_session()
            return True
        if result == wx.NO:
            return True
        return False

    def _open_file_menu_with_alt(self) -> None:
        if self._opening_menu_with_alt:
            return

        self._opening_menu_with_alt = True
        self._list_focus_row_before_menu = (
            self._selected_list_row() if self._has_list_focus() else None
        )

        if sys.platform == "win32":
            ctypes.windll.user32.PostMessageW(
                self.GetHandle(), WM_SYSCOMMAND, SC_KEYMENU, 0
            )
        wx.CallLater(150, self._reset_alt_menu_flag)

    def _reset_alt_menu_flag(self) -> None:
        self._opening_menu_with_alt = False

    def _on_activate(self, event: wx.ActivateEvent) -> None:
        if event.GetActive():
            if self._list_focus_row_before_deactivate is not None:
                row = self._list_focus_row_before_deactivate
                self._list_focus_row_before_deactivate = None
                wx.CallAfter(self._restore_list_focus_after_activate, row)
        else:
            self._list_focus_row_before_deactivate = (
                self._selected_list_row() if self._has_list_focus() else None
            )
            self._reset_alt_state()
        event.Skip()

    def _on_menu_open(self, event: wx.MenuEvent) -> None:
        event.Skip()

    def _on_menu_close(self, event: wx.MenuEvent) -> None:
        if (
            self._list_focus_row_before_menu is not None
            and not self._list_focus_restore_pending
        ):
            self._list_focus_restore_pending = True
            wx.CallLater(120, self._restore_list_focus_after_menu_if_needed)
        event.Skip()

    def _reset_alt_state(self) -> None:
        self._alt_pressed = False
        self._alt_combo_used = False

    def _restore_list_focus_after_menu_if_needed(self) -> None:
        if self._list_focus_row_before_menu is None:
            self._list_focus_restore_pending = False
            return

        if self._is_in_menu_mode():
            wx.CallLater(120, self._restore_list_focus_after_menu_if_needed)
            return

        row = self._list_focus_row_before_menu
        self._list_focus_row_before_menu = None
        self._list_focus_restore_pending = False
        self._focus_list_row(row)

    def _restore_list_focus_after_activate(self, row: int) -> None:
        if not self.IsActive() or self._has_list_focus():
            return
        current_focus = wx.Window.FindFocus()
        if current_focus is not None and current_focus != self:
            return
        self._focus_list_row(row)

    def _is_in_menu_mode(self) -> bool:
        if sys.platform != "win32":
            return False

        info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
        if not ctypes.windll.user32.GetGUIThreadInfo(0, ctypes.byref(info)):
            return False
        return bool(info.flags & GUI_INMENUMODE)
