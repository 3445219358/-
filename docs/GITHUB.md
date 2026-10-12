# 上传 GitHub

## 文件范围

仓库上传项目目录内的源码、JSON、图标、截图、文档、依赖文件、测试、脚本、根目录的 `TaixuAscension.exe` 和 `.github/workflows/windows.yml`。保留目录层级，并确认以点开头的文件也上传。

网页上传的是解压后的内容。把 ZIP 单独上传到仓库不会展开源码，也不会触发其中的工作流。若系统隐藏了点文件，使用 Git 或 GitHub Desktop 上传本目录。

项目包附带可直接运行的 Windows 64 位程序。完整解压后双击根目录的 `TaixuAscension.exe`，无需安装 Python。该程序小于 GitHub 网页单文件上传的 25 MiB 限制，可与源码一并上传。

此项目包不含玩家存档、个人路径、虚拟环境、Git 凭据、构建缓存或旧网页。`.gitignore` 允许上传根目录的 `TaixuAscension.exe`，同时排除 `build/`、`dist/` 和其他本地生成的程序。修改源码后需重新构建并替换根目录程序。

## 自动构建

`Windows 原生构建` 在推送、拉取请求和手动运行时执行，使用 Windows 和 Python 3.14。流程只使用读取仓库权限，不推送代码，也不自动创建 Release。

检查顺序为：安装依赖 → 27 项规则回归 → SDL 界面校验 → PyInstaller 打包 → 上传构建产物。构建产物名为 `TaixuAscension-Windows`，保留 14 天。

在 GitHub 运行页面下载 Artifacts 后，会得到 GitHub 生成的外层 ZIP；其中的 `TaixuAscension-Windows.zip` 是游戏分发包。再次解压游戏分发包，双击 `TaixuAscension.exe`。

## 手动发布版本

1. 确认 Actions 成功，并下载和解压产物。
2. 在仓库 **Releases → Draft a new release** 创建 `v0.2.0` 标签，选择要发布的提交。
3. 标题填写 `太虚问道 0.2.0 · Windows 原生原型`。
4. 上传产物中的 `TaixuAscension-Windows.zip`；说明当前包含 5 个流派、60 张卡牌和三重流程，仍处于原型阶段。
5. 勾选预发布版本后，根据自己的发布安排提交。

项目维护者自行决定仓库可见性和项目许可证；本项目包未替维护者指定开源许可证。
