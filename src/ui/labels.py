from __future__ import annotations

import wx


STATUS_OPTIONS: list[tuple[str, str]] = [
    ("待处理", "pending"),
    ("通过", "passed"),
    ("失败", "failed"),
    ("不适用", "not_applicable"),
]

PRIORITY_OPTIONS: list[tuple[str, str]] = [
    ("低", "low"),
    ("中", "medium"),
    ("高", "high"),
]

STATUS_LABELS = {value: label for label, value in STATUS_OPTIONS}
PRIORITY_LABELS = {value: label for label, value in PRIORITY_OPTIONS}


def append_options(control: wx.ItemContainer, options: list[tuple[str, str]]) -> None:
    control.Clear()
    for label, value in options:
        control.Append(label, value)


def set_selected_value(control: wx.ItemContainer, value: str) -> None:
    for index in range(control.GetCount()):
        if control.GetClientData(index) == value:
            control.SetSelection(index)
            return
    control.SetSelection(wx.NOT_FOUND)


def get_selected_value(control: wx.ItemContainer, default: str) -> str:
    selection = control.GetSelection()
    if selection == wx.NOT_FOUND:
        return default
    value = control.GetClientData(selection)
    return value or default


def status_label(value: str) -> str:
    return STATUS_LABELS.get(value, value)


def priority_label(value: str) -> str:
    return PRIORITY_LABELS.get(value, value)
