# accessible-form-assist

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

输出目录：

```text
dist\accessible-form-assist\
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

构建产物命名格式：

```text
accessible-form-assist-windows-run-<run_number>
```

### 建议的 PR 合并保护

仅靠 workflow 存在还不够；如果希望 **PR 有问题时管理员和所有者也不能点 Merge**，需要在 GitHub 仓库设置里为 `main` 配置 **Ruleset** 或 **Branch protection rule**，至少启用这些项：

1. **Require a pull request before merging**
2. **Require status checks to pass before merging**，并把 `ruff`、`build-windows`、`review-guard` 设为 required
3. **Require conversation resolution before merging**
4. **Require approvals**（建议至少 1 个）
5. **Do not allow bypassing the above settings**

仓库内已补充 `.github\workflows\pr-review-guard.yml`，它会在 PR 有未解决 review 线程或存在 `CHANGES_REQUESTED` 审查时失败；再配合上面的 Ruleset，才能真正把危险合并挡在外面。

## License

本项目采用 [MIT License](LICENSE)。
