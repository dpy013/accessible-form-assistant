# accessible-form-assist

信息无障碍表格填写助手首版工程。

## 当前已支持

- 新建工程、打开已有工程、自动恢复最近工程
- 支持从 HTML / Word / Excel / Jira CSV / Markdown 文件直接导入创建工程
- `#413` 风格自动编号与项目目录初始化
- 检查项编辑、手动新增、软删除/还原、隐藏已完成
- 剪贴板截图落盘到 `assets/`
- HTML / Word / Excel / Jira CSV / Markdown 导出
- 5 分钟自动备份与未保存修改提示

## 运行

```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
python -m src.main
```

## 构建检查

```powershell
scons
```

## 打包 Windows 可执行文件

```powershell
.venv\Scripts\activate
python -m pip install pyinstaller
pyinstaller --clean accessible-form-assist.spec
```

生成结果位于 `dist\accessible-form-assist\`。

## GitHub Actions

仓库包含 `.github\workflows\build-binary.yml`，在 `main` 分支 push、pull request 和手动触发时会自动：

- 安装依赖
- 执行源码编译检查
- 使用 PyInstaller 构建 Windows 可执行文件
- 上传 `accessible-form-assist-windows` artifact
