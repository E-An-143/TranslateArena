# DeepSeek 接口依据 · 2026-10-07

本次核对官方 [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/) 与 [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/) 文档。模型保留 `deepseek-flash`，使用 `POST https://api.deepseek.com/chat/completions`。

## 所有生成请求的统一参数

```json
{
  "model": "deepseek-flash",
  "thinking": {"type": "enabled"},
  "reasoning_effort": "max",
  "stream": true,
  "stream_options": {"include_usage": true}
}
```

项目直接使用 httpx 发送 JSON，因此 thinking 和 reasoning_effort 放在请求体顶层，无需 OpenAI SDK 的 extra_body 包装。翻译、重新生成、Judge、裁决重试和 JSON 格式修复均保持相同思考强度。Judge 额外发送 response_format: {type: json_object}，prompt 明确要求 JSON。

不发送 temperature 等采样覆盖参数；不指定 max_tokens，避免旧版 Judge 的 8192 token 限制占满思考预算。根据核对时的官方文档，max 思考模式的默认输出预算为 128K；该预算是上限而不是固定生成量。保留读取超时 180 秒、连接超时调整为 30 秒，限流/部分服务错误最多自动重试两次。尚未收到模型增量的临时网络错误也最多重试两次；已收到模型输出的断流保留预览，提供单路手动重试。连接测试仅调用 /models，不生成文本。

## 返回字段与完成条件

| API 字段 | 应用处理 |
| --- | --- |
| `choices[0].delta.reasoning_content` | 逐块追加到Candidate.reasoning 字段；Judge 使用 judge_reasoning |
| `choices[0].delta.content` | 逐块追加到译文预览或 Judge JSON 预览 |
| `choices[0].finish_reason` | 只有 stop 可提交；length、过滤、资源不足等原因均拒绝采用 |
| `usage` | 读取最终块统计，并兼容 choices 为空的独立统计块 |
| `data: [DONE]` | 确认流正常结束；缺失时即使已经看到完整文本也拒绝提交 |

两种增量字段分别处理，同一块同时出现两种字段时均读取。支持 UTF-8 跨传输分片、SSE 多行数据、保活注释和不带末尾空行的 DONE 标记。接口没有返回思考文本时保留空值，不自行补写。失败或取消保留预览；预览和思考不会作为候选译文提交Judge。

Judge 只有在 stop、DONE、非空完整 content 和本地 JSON/评分/候选校验全部成功后才写入裁决与终稿；最多一次格式修复，修复请求仍为 max。格式修复的上一轮 assistant 消息只传 content，没有 tools，因此无需回传 reasoning_content。UI 展示译者思考与裁判评审结果；Judge 生成期间展示实时思考和 JSON 预览，完整结束并校验后才显示四维评审结果。

保留的非流式 complete 入口同样发送 thinking enabled 与 max，分开读取 message.reasoning_content/content，并要求 stop 和非空最终内容。

## 验证范围

使用真实 DeepSeek HTTP 适配器与 httpx MockTransport 验证请求负载、延迟流分片、两种增量字段、结束标记、断流、截断、取消、JSON 修复与重试；通过真实 Qt/QML 控件验证设置变动进入实际 HTTP 请求。详细测试见 test_streaming.py、test_provider.py、test_orchestrator.py、test_prompt_api_revision.py 与 test_qml_integration.py。

本次没有真实 API Key，未进行付费在线调用。上述验证证明客户端的构造、解析、状态流转和显示行为；真实服务的可用性、延迟、翻译质量和服务端实际思考行为需要账号在线验证。
