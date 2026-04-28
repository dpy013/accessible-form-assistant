# accessible-form-assistant

信息无障碍表格填写助手桌面应用工程。

## 功能概览

- 新建工程、打开已有工程、打开文件创建工程、自动恢复最近工程
- 支持从 HTML、Word、Excel、CSV、Markdown 导入创建工程
- 各格式统一走通用解析流程，专用模板也通过表头规则接入同一套解析器
- 普通文档若不符合专用模板，也会按段落或表格行兜底导入为项目列表
- GB/T 37668 指标表可通过 HTML、Word、Excel、CSV、Markdown 导入，并统一转换为检查项
- 使用 `#413` 风格自动生成工程编号并初始化目录
- 支持检查项编辑、手动新增、软删除/还原、隐藏已完成
- 支持独立项目配置，工具设置和自定义键值配置保存到 `config.xml`
- 支持将剪贴板截图保存到 `assets\`
- 支持导出 HTML、Word、Excel、CSV、Markdown
- 支持 5 分钟自动备份和未保存修改提示

## 本地运行

建议使用 Python 3.14.4。

```powershell
uv venv --python 3.14.4
.venv\Scripts\activate
uv pip install -r requirements.txt
python -m src.main
```

## 本地检查

```powershell
scons
```

## 打包 Windows 可执行文件

建议使用 Python 3.14.4。

```powershell
.venv\Scripts\activate
python -m pip install pyinstaller
pyinstaller --clean --noconfirm accessible-form-assist.spec
```

默认输出目录：

```text
dist\accessible-form-assistant-0.1.0\
```

如果希望本地构建也带上类似 `260427s` 的构建标识，可先设置：

```powershell
$env:BUILD_LABEL = "260427s"
pyinstaller --clean --noconfirm accessible-form-assist.spec
```

此时输出目录和可执行文件会包含版本与构建标识，例如：

```text
dist\accessible-form-assistant-0.1.0-260427s\
accessible-form-assistant-0.1.0-260427s.exe
```

## GitHub Actions

仓库内置 `.github\workflows\build-binary.yml`，会在以下场景自动构建 Windows 二进制：

- `main` 分支 push
- pull request
- 手动触发 `workflow_dispatch`

工作流会自动执行：

1. 安装依赖
2. 执行源码编译检查
3. 使用 PyInstaller 构建 Windows 可执行文件
4. 上传构建产物

构建产物命名格式会按工作流运行号动态生成，避免同一天内重复：

```text
accessible-form-assistant-0.1.0-<yymmdd>r<run-number>[-a<attempt>]-windows-x64
```

## License

本项目采用 [MIT License](LICENSE)。
