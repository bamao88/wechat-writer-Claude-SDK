# NotebookLM Skill 登录步骤（逐步执行）

在 **NotebookLM skill 目录** 下完成以下步骤后，主项目里的 `search_notebooklm` 工具调用才会通过认证。

---

## 第一步：进入 Skill 目录

在终端执行（项目根目录为 `wechat-writer-Claude-SDK` 时）：

```bash
cd /Users/fl/WXP/IP_ZH/wechat-writer-Claude-SDK/notebooklm_skill
```

确认当前目录下有 `scripts/auth_manager.py` 和 `requirements.txt`。

---

## 第二步：创建并激活虚拟环境（若尚未创建）

若目录下还没有 `.venv`，执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

（Windows 用 `.venv\Scripts\activate`。）

若已有 `.venv`，只需激活：

```bash
source .venv/bin/activate
```

---

## 第三步：安装依赖

```bash
pip install -r requirements.txt
```

---

## 第四步：安装 Chrome（供 patchright 使用）

Skill 使用 **patchright** 控制 **Chrome**（非 Chromium），需安装浏览器驱动：

```bash
patchright install chrome
```

请确保本机已安装 [Chrome 浏览器](https://www.google.com/chrome/)。若命令报错，可先装 Chrome 再重试。

---

## 第五步：执行登录 setup

在 **当前仍为 `notebooklm_skill` 目录、且已激活 `.venv`** 的情况下执行：

```bash
python scripts/auth_manager.py setup
```

会弹出 **Chrome 窗口** 并打开 https://notebooklm.google.com：

1. 若未登录 Google，按提示在浏览器里完成登录（选择账号、输入密码等）。
2. 登录成功后，页面停留在 NotebookLM 即可。
3. 脚本检测到已登录后会自动保存登录状态并退出，终端会看到类似：
   - `✅ Login successful!`
   - `💾 Saved browser state to: ...`
   - `✅ Authentication setup complete!`

等待时间默认最多 10 分钟；若需更长可加参数，例如：

```bash
python scripts/auth_manager.py setup --timeout 15
```

---

## 第六步：确认认证状态（可选）

```bash
python scripts/auth_manager.py status
```

应看到 `Authenticated: Yes`。

验证是否真的可用（会再次打开浏览器做一次检查）：

```bash
python scripts/auth_manager.py validate
```

显示 `Authentication is valid and working` 即表示认证成功。

---

## 若主项目未指定 Skill 目录

主项目默认会找 **当前项目下的 `notebooklm_skill`**（即 `wechat-writer-Claude-SDK/notebooklm_skill`），一般无需改配置。

若你把 Skill 放在别处，需在 **主项目** 的 `.env` 里设置：

```env
NOTEBOOKLM_SKILL_DIR=/你的/notebooklm_skill/绝对路径
```

---

## 完成后

回到主项目根目录，重新跑写作流程即可，例如：

```bash
cd /Users/fl/WXP/IP_ZH/wechat-writer-Claude-SDK
LLM_PROVIDER=openai .venv/bin/python main.py "你的选题"
```

此时「私域挖掘员」等步骤中的 NotebookLM 搜索应不再报 `Not authenticated`。
