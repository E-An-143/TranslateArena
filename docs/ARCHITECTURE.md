# Translate Arena · 当前架构

## 组成

`main.py` 加载字体、数据目录、Bridge 与 QML。`arena/worker.py` 在独立线程运行 asyncio；Qt Signal 将进度返回主线程。Bridge 负责配置、状态、凭据读取、任务启动与历史保存。

`arena/models.py` 定义配置与任务快照，`arena/services/prompt_builder.py` 构造翻译和多维评审提示词，`translation_orchestrator.py` 编排并行任务，`judge_validation.py` 验证评审结果，`judge_scoring.py` 保存维度、权重与精确计算。

## 数据模型

| 模型 | 字段 |
| --- | --- |
| AgentConfig | id、route、cultural_direction、style |
| Settings | appearance、三份 AgentConfig |
| Candidate | id、status、text、reasoning、preview、error、usage |
| TranslationRecord | id、created_at、source、target_language、agents、candidates、stage、judge、final、Judge 思考与预览、耗时及用量 |

任务和候选均不含翻译模式、轮次或第二份译文。只有完整成功的模型输出写入 `Candidate.text`；增量思考与回答分别追加到 `reasoning` 和 `preview`。

## 唯一执行流程

1. A/B/C 同时收到原文、目标语言及各自的配置提示词，独立生成译文。
2. 等待当前候选任务全部完成，只将完整且非空的 `text` 提交 Judge。
3. Judge 对照原文及候选配置，返回忠实性、语言表达、术语、文体四项评分和最终译文。
4. 本地按 50/25/15/10 权重计算总分，确定胜者，从原候选中原样提取终稿。

正常为 4 次请求。阶段为 `ready`、`translating`、`judging`、`completed`，另有 `error`、`judge_error`、`cancelled` 与历史恢复时的 `interrupted`。

术语维度的适用性必须对所有候选一致；统一不适用时移除该项并归一化权重。Decimal 保证比较前不舍入总分，同分按各维度优先级和输入顺序处理。评分或候选不合法时最多请求一次 JSON 格式修复，失败则保留候选，可重新生成一路译文后自动评审。

## 流式、重试和取消

Provider 解析 Chat Completions SSE，将 reasoning_content 与 content 分开处理。必须同时满足 stop、DONE 和非空文本才提交结果。每路最多每 80 毫秒发布一次增量，完成后立即发布。

编排器为每个译者保存独立 Task。单路重试先关闭旧任务，再清空该路译文、思考、预览与用量并重新生成；其他任务继续。Judge 运行时换稿会取消旧评审，待新候选就绪后自动评审，旧裁决不能覆盖新结果。

所有评审都随翻译生成或单路重新生成自动执行。取消传播到正在运行的译者与 Judge 请求，保留已完成译文及未完成预览。

所有角色使用 `arena/config.py` 的统一模型与思考强度，不提供模型或温度配置。Provider 共用请求负载构造，格式修复、重试和重新生成均保持相同参数。

## 界面

QML 工作区依次展示原文、三位译者配置、三份预览、左侧四维评审与右侧最终译文。翻译者标题没有操作按钮。窄窗口可切换 Agent，没有模式或轮次选择。

CandidateCard 生成时显示思考，完成后显示完整译文。展开阅读同时呈现思考与译文／预览。JudgeReview 在主页与展开面板共用四维分数、术语不适用状态及胜出标记；主页生成中显示“正在评审”与 Judge 思考，正文和状态文字左侧对齐，不再重复显示“思考过程”标题。

JudgeAnalysis 与译者展开阅读一样，将思考与输出分区展示并独立滚动。思考实时更新，完成后继续保留，恢复历史后也可查看；输出区在生成中显示 API 预览，完成后显示结构化评审结果。

所有放大按钮都由对应内容控制启用状态，空白或仅有占位状态时置灰禁用。翻译记录标题保持不变，多选入口在选择期间显示“退出多选模式”。只保留多选删除和对应确认弹窗，单条垃圾桶、直接清空历史及其后台入口均已移除。

## 存储

SQLite schema 6 仅保留 settings、history。旧版本升级在事务内清理停用表、保留并清理设置、删除旧历史，并在升级前保存快照；无需转换旧任务。当前 schema 的历史在再次启动时保留。凭据在独立目录使用 Windows DPAPI 加密。

Bridge 每 500 毫秒合并保存流式快照，在阶段或候选状态变化时立即保存；完成、错误和取消都会保存。恢复未完成任务时将其标记为 interrupted，运行候选标记为 cancelled，允许单路重试。

数据目录迁移使用 SQLite backup 包含 WAL 中的已提交数据，再复制凭据、日志与备份，原子更新启动指针；已有目标数据不被覆盖。
