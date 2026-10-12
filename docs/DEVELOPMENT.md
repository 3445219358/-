# 开发说明

## 结构

`engine.py` 定义不依赖 pygame 的规则内核 `Game`，`main.py` 定义原生界面 `App`。界面调用内核执行行动，显示状态并接受键盘、鼠标输入。卡牌、流派、普通敌人和首领数据来自 `content.json`；遗物和事件列表目前在 `engine.py`。

运行时 `content.json` 从源码所在目录读取。PyInstaller 打包后改为从 `_MEIPASS` 资源目录读取，因此需要保留构建脚本的 `--add-data` 参数。

## 内容迭代

- 卡牌实例是 `id` 与 `upgraded` 字段；卡牌定义包含名称、流派、类型、稀有度、灵力费用、描述、效果数据、升级数据和风味文本。
- 改数值时同步检查基础效果、升级效果和显示文案。`engine.effects()` 合并升级后的规则数据。
- 新效果需要在 `Game.play()` 或对应状态结算函数中实现，并添加能验证结算结果的回归案例。
- 各流派初始卡组在 `sects` 中定义，每组 12 张；当前回归测试固定 60 张卡牌及稀有度分布，扩展卡池时同步修改数量验收。

## 随机数与存档

地图、抽牌、奖励和敌人选择使用每局独立的 `random.Random`。存档保存随机数状态，读档后沿用相同序列。新功能应使用 `Game.rng`，不要用全局随机数生成影响规则的结果。界面的粒子使用独立随机数，不影响战斗判定。

存档有版本字段 `Game.SAVE_VERSION`。修改已保存字段的结构时增加版本，并处理旧存档迁移。保存使用临时文件替换方式；开发测试使用临时目录或 `--save-dir .local/save`。

## 测试与界面检查

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_engine.py
.\.venv\Scripts\python.exe scripts/verify_ui.py
```

批量渲染现有界面时，使用隔离的存档和 SDL 驱动：

```powershell
$env:SDL_VIDEODRIVER = 'dummy'
$env:SDL_AUDIODRIVER = 'dummy'
.\.venv\Scripts\python.exe main.py --save-dir .local/smoke-save --smoke-dir .local/smoke-images
Remove-Item Env:SDL_VIDEODRIVER
Remove-Item Env:SDL_AUDIODRIVER
```

生成的 PNG 位于 `.local/smoke-images`。截图只检查布局；打包程序的窗口、音频、全屏、输入与读档仍需实际运行验证。

## 构建

`scripts/build.ps1` 可从任意工作目录调用，使用脚本位置解析项目根目录；参数 `-Python` 指向已安装依赖的 Python。构建过程执行测试，然后输出 `dist/` 并将文档加入 Windows 分发包。`build/` 和 `dist/` 默认不进入 Git。

应用使用 Windows 系统自带的中文字体，没有在仓库内分发字体文件。目标平台为 Windows 64 位，CI 使用 Windows 运行器。
