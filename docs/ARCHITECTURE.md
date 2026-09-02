# 架构设计

## 设计目标

1. LangGraph业务节点不依赖DeepSeek、OpenAI或其他具体供应商。
2. 外部数据采集、模型生成和确定性校验职责分离。
3. 模型失败、JSON失败和业务规则失败都能在图状态中被观察和处理。
4. 测试可以注入Fake Chat Model和Stub Context Builder，不消耗真实API。

## LangGraph状态机

```text
START
  │
  ▼
collect_context ── 高德/本地候选采集
  │
  ▼
build_prompt ───── PlannerContext压缩与提示构造
  │
  ▼
generate_candidate ── BaseChatModel + 结构化策略
  │
  ▼
validate_candidate ── Pydantic、日期、餐饮、酒店、POI规则
  │
  ├─ 未达到上限/候选数 ───────────────┐
  │                                   │
  │                                   ▼
  │                         generate_candidate
  │
  ├─ 有合法候选 → select_best_candidate → END
  │
  └─ 无合法候选且达到上限 → create_fallback → END
```

`PlannerState`只保存一次运行中会变化的数据。模型对象、配置、上下文构造器等依赖放在`PlannerRuntime`，通过LangGraph runtime context注入。

## 模型网关

`ModelFactory`把环境变量转换为LangChain `BaseChatModel`：

```text
LLM_PROVIDER + LLM_MODEL + LLM_BASE_URL
                    │
                    ▼
             init_chat_model
                    │
                    ▼
              BaseChatModel
```

`openai_compatible`会映射到OpenAI集成并保留自定义`base_url`。其他provider名称直接传给LangChain，因此新增已安装的集成通常不需要修改图代码。

## 结构化输出兼容

不同供应商支持的结构化能力不同，调用层按配置选择：

```text
json_schema → function_calling → json_mode → prompt JSON parser
```

默认顺序是保守的供应商能力提示。显式设置`LLM_STRUCTURED_OUTPUT_MODE`可以锁定策略。只有能力不支持或解析失败时才降级；普通网络和认证错误不会被误判成能力问题。

## 可观测性

API响应的`metadata`可包含：

- provider / model
- structured_strategy
- attempts / selected_attempt / candidate_count
- rerank_score
- usage / response_metadata

密钥不会进入图状态、API响应或日志。
