# 原始 clone 下 OpenAI 适配是如何跑通的

## 1. 代码已恢复为 clone 状态

- 已用 `git restore` 恢复：`doc/refer.md`、`requirements.txt`、`src/agent/backends/__init__.py`、`src/config/settings.py`
- 已删除本次新增：`litellm_.py`、`scripts/test_litellm_tool_call.py`
- `.env` 未提交过，已保留你当前本机的配置

---

## 2. 原始 OpenAI 后端的实现方式（clone 里的 openai_.py）

- **唯一调用**：`self._client.chat.completions.create(...)`  
  即标准 **OpenAI Chat Completions API**，请求路径为：`{base_url}/chat/completions`。
- **返回解析**：只认 `response.choices[0].message` 的 `content` 和 `tool_calls`（每个 `tool_call` 有 `id`、`function.name`、`function.arguments`），即 **OpenAI Chat Completions 的标准返回格式**。
- **没有**：Azure Responses API、`/openai/responses`、api_version、tool_choice 等任何特殊逻辑。

因此：**只要后端返回的是「Chat Completions 标准结构」，这段代码就能跑通工具调用。**

---

## 3. 你之前在另一台电脑跑通的典型方式：LiteLLM 代理

在「clone 下来就能跑」的前提下，OpenAI 适配能工作的唯一合理方式是：

- **请求不直连 Azure/OpenAI**，而是先发到一个 **OpenAI 兼容的代理**；
- 代理接收 **Chat Completions** 请求（`/chat/completions`），转发到真实后端，再把响应**转成 Chat Completions 格式**返回；
- 这样本项目始终只看到「Chat Completions + message.tool_calls」，无需任何改代码。

最常见的做法就是 **LiteLLM 代理**：

1. 在另一台电脑上运行 LiteLLM（例如 `litellm --port 4000`），并配置好 Azure 或 OpenAI。
2. `.env` 里类似：
   - `LLM_PROVIDER=openai`
   - `OPENAI_BASE_URL=http://localhost:4000`（或那台机器的 LiteLLM 地址）
   - `OPENAI_API_KEY=...`（LiteLLM 若不做校验可填任意）
   - `OPENAI_MODEL=...`（部署名/模型名，和 LiteLLM 配置一致）
3. 本项目的 `OpenAIBackend` 只会向 `http://localhost:4000` 发 `POST .../chat/completions`，收到的一直是标准 Chat Completions 响应，所以工具调用能正常解析、跑通。

也就是说：**之前跑通，是因为 base_url 指向的是 LiteLLM（或同类）代理，而不是 Azure 的直连 URL。**

---

## 4. 为何换环境后「直接跑」会失败？

若在这台电脑的 `.env` 里把 `OPENAI_BASE_URL` 改成了 **Azure 直连**，例如：

```env
OPENAI_BASE_URL=https://xxx.openai.azure.com/openai/responses?api-version=2025-04-01-preview
```

则：

- 本项目仍会请求：`{base_url}/chat/completions`  
  即：`https://xxx.openai.azure.com/openai/responses?api-version=.../chat/completions`
- Azure 的 **Responses API** 的端点却是 **`/openai/responses`**，不是 `/chat/completions`，所以会 404 或行为不符合预期。
- 即使改成 Azure 的 Chat Completions 地址（`/openai/deployments/xxx/chat/completions`），也还涉及 api-version 等细节，和「clone 里这份只认 Chat Completions 标准格式」的代码是两套故事。

所以：**clone 的代码本身没变，能跑与否取决于 base_url 指向谁。指向 LiteLLM → 能跑；指向 Azure 直连（尤其是 /openai/responses）→ 容易挂。**

---

## 5. 结论与建议

- **原始适配方案**：通过 **LiteLLM（或任意 OpenAI 兼容代理）** 把请求转成 Chat Completions 再给本项目用；本项目只实现「Chat Completions + tool_calls」这一种格式，就能跑通。
- **要在这台电脑复现「和之前一样能跑」**：
  - 要么：在这台电脑也起一个 LiteLLM 代理，`.env` 里 `OPENAI_BASE_URL` 指到这个代理（例如 `http://localhost:4000`），其余配置与另一台电脑一致；
  - 要么：继续用另一台电脑的 `.env`（base_url 指向那台的 LiteLLM 地址），保证网络能访问那台机器的代理。

**不改 clone 代码、只靠正确配置 base_url（指向 LiteLLM），就是之前 OpenAI 适配能跑通的原因。**
