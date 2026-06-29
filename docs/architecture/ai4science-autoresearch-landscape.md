# AI4Science 自动科研系统调研

调研日期: 2026-06-29

本文档面向 AutoResearch Platform 维护者。目标不是复述 AI4Science 全部论文，而是回答三个问题:

1. 现在 AI4Science 和自动科研系统已经做到什么程度。
2. FARS、Karpathy AutoResearch、AI Scientist、FutureHouse 等系统的 pipeline 到底怎么设计。
3. AutoResearch Platform 应该借鉴哪些控制面能力，同时继续拒绝哪些执行面能力。

结论先行:

- AI4Science 已经在分子结构预测、蛋白生成、材料候选生成、文献问答、代码实验和受限 benchmark loop 上形成实用能力。
- 真正的端到端「自动科学家」仍处于早期。系统可以生成论文和代码，但 artifact-aware review 后会暴露实验不足、结果不一致、引用或结果 fabrication、计划与执行不匹配等问题。
- 成熟度最高的不是「写论文」，而是「有不可篡改 verifier 的窄域闭环」。Karpathy AutoResearch 这类单指标、单文件、短周期循环，比开放式 paper factory 更容易可靠进步。
- FARS 的关键价值不在「论文生成器」，而在规模化公开运行、短贡献单元、负结果可报告、共享工作区和多阶段 agent 分工。
- 对本平台来说，正确方向是增强事实源、预注册、run contract、artifact 引用、claim 级证据、review audit、decision 和经验维护。平台仍然不应内置 LLM provider router、agent loop、benchmark executor、训练器、实验室控制或外部 Runtime 工作区访问。

## 领域分层

| 层级 | 当前能力 | 代表系统 | 成熟度判断 |
| --- | --- | --- | --- |
| 科学 foundation model | 对结构、序列、分子、材料做预测或生成 | AlphaFold 3、ESM3、Chai-1、Boltz-2、GNoME、MatterGen | 已经有强工具价值，但本身不是自动科研 loop |
| 文献与知识 agent | 检索、综述、问答、矛盾检测、引用溯源 | FutureHouse PaperQA2、Asta 系列 agent、ResearchArena | 可作为科研入口，仍受检索质量、上下文、引用完整性限制 |
| 指标驱动实验 loop | 在固定 verifier 下改代码、跑实验、保留改进 | Karpathy AutoResearch、RD-Agent、MLAgentBench、MLE-Bench agent | 当前最可靠，前提是 verifier 和可编辑范围严格隔离 |
| 端到端 paper factory | 从 idea 到实验、图表、论文、review 自循环 | FARS、Sakana AI Scientist v1/v2、AI-Researcher、Agent Laboratory | 可生成完整成果，但质量方差大，artifact-aware 审查是硬门槛 |
| 物理自动实验室 | 把候选、合成、机器人实验、表征、主动学习串起来 | A-Lab、Coscientist、ChemCrow、self-driving labs | 在材料/化学窄域有效，强依赖实验设备、协议和安全边界 |

最重要的分界线是 verifier。凡是有固定评测、固定数据、固定 budget、固定 artifact 要求的系统，进展会更可信。凡是只看论文文本或 LLM review 分数的系统，容易出现「看起来像研究」但证据不足的问题。

## 项目地址速查

| 系统 | 地址 | 公开状态 | 主要 pipeline |
| --- | --- | --- | --- |
| FARS, Analemma | [官网](https://analemma.ai/fars/), [介绍 blog](https://analemma.ai/blog/introducing-fars/), [GitLab 输出账号](https://gitlab.com/fars-a) | 系统代码未见公开，运行输出和页面公开 | Ideation -> Planning -> Experiment -> Writing |
| Karpathy AutoResearch | [GitHub](https://github.com/karpathy/autoresearch), [program.md](https://github.com/karpathy/autoresearch/blob/master/program.md) | 开源实验脚手架 | 固定评测、只改 `train.py`、5 分钟实验、git keep/discard |
| Sakana AI Scientist v1 | [GitHub](https://github.com/SakanaAI/AI-Scientist), [arXiv](https://arxiv.org/abs/2408.06292) | 开源 | idea generation -> novelty check -> code experiments -> paper -> review |
| Sakana AI Scientist v2 | [GitHub](https://github.com/SakanaAI/AI-Scientist-v2), [arXiv](https://arxiv.org/abs/2504.08066) | 开源 | topic idea -> agentic tree search -> experiment manager -> writeup/review |
| AI-Researcher | [GitHub](https://github.com/HKUDS/AI-Researcher), [project](https://autoresearcher.github.io), [arXiv](https://arxiv.org/abs/2505.18705) | 开源 | literature review -> idea -> algorithm design -> implementation -> validation -> manuscript |
| Agent Laboratory | [GitHub](https://github.com/SamuelSchmidgall/AgentLaboratory), [website](https://agentlaboratory.github.io), [arXiv](https://arxiv.org/abs/2501.04227) | 开源 | literature review -> experimentation -> report writing |
| AgentRxiv | [website](https://agentrxiv.github.io), [arXiv](https://arxiv.org/abs/2503.18102) | Agent Laboratory 生态 | agent 之间发布、读取、复用研究输出 |
| Microsoft RD-Agent | [GitHub](https://github.com/microsoft/RD-Agent), [docs](https://rdagent.readthedocs.io/en/latest/index.html), [arXiv](https://arxiv.org/abs/2505.14738) | 开源 | Research agent 提 idea，Development agent 实现，循环迭代 |
| FutureHouse PaperQA2 | [GitHub](https://github.com/Future-House/paper-qa), [paper](https://paper.wikicrow.ai) | 开源 package，平台 agent 部分未完全开源 | scientific RAG、metadata、rerank、contextual summarization |
| AstaBench | [GitHub](https://github.com/allenai/asta-bench), [arXiv](https://arxiv.org/abs/2510.21652) | 开源 benchmark | 2400+ 科研任务，控制工具、成本和 agent 接口 |
| OpenAI MLE-Bench | [GitHub](https://github.com/openai/mle-bench), [arXiv](https://arxiv.org/abs/2410.07095) | 开源 benchmark | 75 个 Kaggle ML engineering 任务 |
| METR RE-Bench | [GitHub](https://github.com/METR/RE-Bench) | 开源 benchmark | 前沿 AI R&D 能力评测 |
| FabScore | [GitHub](https://github.com/chchenhui/fabscore), [preprint PDF](https://chchenhui.github.io/papers/FabScore.pdf) | 开源评估框架 | result extraction -> static analysis -> code execution -> verdict |
| ChemCrow | [GitHub](https://github.com/ur-whitelab/chemcrow-public), [paper](https://www.nature.com/articles/s42256-024-00832-8) | 开源 | LLM + chemistry tools |
| Coscientist | [Nature](https://www.nature.com/articles/s41586-023-06792-0) | 论文公开 | web/literature/tool planning -> robotic chemistry experiments |
| A-Lab | [Nature](https://www.nature.com/articles/s41586-023-06734-w) | 论文公开 | candidate selection -> robotic synthesis -> characterization -> active learning |
| AlphaFold 3 | [Nature](https://www.nature.com/articles/s41586-024-07487-w), [GitHub](https://github.com/google-deepmind/alphafold3) | 代码和模型权重按许可发布 | biomolecular structure and interaction prediction |
| ESM | [GitHub](https://github.com/evolutionaryscale/esm) | 开源工具链 | protein language modeling and generation |
| Chai-1 | [GitHub](https://github.com/chaidiscovery/chai-lab) | 开源推理代码 | molecular structure prediction |
| Boltz-2 | [GitHub](https://github.com/jwohlwend/boltz) | 开源 | biomolecular structure and affinity prediction |
| MatterGen | [GitHub](https://github.com/microsoft/mattergen), [Nature](https://www.nature.com/articles/s41586-025-08628-5) | 开源 | generative materials design |
| GNoME / materials discovery | [Nature](https://www.nature.com/articles/s41586-023-06735-9), [GitHub](https://github.com/google-deepmind/materials_discovery) | 数据/代码公开 | large-scale inorganic crystal candidate discovery |

## FARS 深拆

FARS 是 Analemma 在 2026-02-11 公开介绍的 Fully Automated Research System。官方定义是端到端多 agent 系统，目标是在执行期间无人干预地完成 hypothesis、planning、experimentation 和 paper writing。当前落点主要是 AI research，也就是 AI-for-AI。

公开设计要点:

- 四个专门 agent: Ideation、Planning、Experiment、Writing。
- Ideation 读取研究方向文档，访问 open-access papers 和 public GitLab repositories，生成 research hypotheses。
- hypothesis 通过自动 review 后，顺序进入 planning、experiment、writing。
- agent 通过共享文件系统协作。共享文件系统同时是 workspace 和 persistent memory。
- 官方介绍中提到把 160 张 NVIDIA GPU 的集群封装成 experiment agent 可用的 training/inference tools。
- 首次公开部署目标是连续运行直到产出 100 篇完整 research papers。
- FARS 输出强调短 paper、单一 well-scoped contribution，并允许明确报告 negative results。
- 负责任发布策略包括 arXiv 前至少 3 名团队研究者人工 review，并明确标注 AI-generated。

可以借鉴的点:

- 把「研究贡献」降到 hypothesis + validation 的短单元，而不是默认追求长论文。
- 把 negative result 当作可登记知识，而不是失败垃圾。
- 公开运行 trace、代码、paper 和 review，让社区能做 artifact-aware 评估。
- 阶段化 agent 分工清晰，适合映射成平台中的 round、protocol、experiment、artifact、evidence、review、decision 引用链。

不能照搬到平台内的点:

- 不在平台内实现 Ideation/Planning/Experiment/Writing agent。
- 不在平台内调度 GPU、调用模型、管理 provider、跑训练或写论文。
- 不把共享文件系统变成平台存储。平台只保存结构化状态和 artifact 引用。

对 AutoResearch Platform 的直接启发:

```text
source_refs
  -> hypothesis
  -> preregistered protocol
  -> external runtime run
  -> artifact refs
  -> claim-level evidence
  -> artifact-aware review
  -> decision
  -> explicit experience curation
```

FARS 暴露的问题也很明确: 如果系统代码、执行环境、原始实验日志和 verifier 不够可审计，论文数量不能代表科研质量。本平台应该服务于这种审计，而不是服务于论文数量。

## Karpathy AutoResearch 深拆

Karpathy 的 AutoResearch 是一个非常小但很重要的设计样本。它把自动研究问题压缩成一个可验证的工程闭环:

- 用户先同意 run tag，创建 `autoresearch/<tag>` 分支。
- 仓库小到 agent 必须读完 `README.md`、`prepare.py`、`train.py`。
- `prepare.py` 是固定评测、数据、tokenizer、dataloader 和 time budget，不允许修改。
- agent 只能改 `train.py`。
- 不允许安装新依赖，不允许修改 evaluation harness。
- 每次实验单 GPU，固定 5 分钟 wall clock training time。
- 目标只有一个: 降低 `val_bpb`。
- 每次运行把 commit、metric、memory、status、description 写入 `results.tsv`。
- 如果 metric 变好，保留 commit；如果相同或变差，reset 回起点；crash 单独记录。
- loop 不主动停，直到人类中断。

这个 pipeline 的本质不是「AI 写研究论文」，而是「把研究变成不可篡改 verifier 下的连续局部搜索」。它可靠的原因在于:

- 可编辑面小。
- 评测面不可编辑。
- 运行预算固定。
- 结果结构化。
- git 天然形成 lineage。
- discard 和 crash 也是一等结果。

对平台的启发比多数复杂 paper factory 更直接:

| 设计点 | 平台应该支持的状态 |
| --- | --- |
| 只允许改 `train.py` | 记录 editable scope，不执行修改 |
| `prepare.py` 固定评测 | 记录 verifier artifact 引用、hash 和 metric contract |
| 5 分钟 budget | 记录 budget contract 和实际 runtime metadata |
| `results.tsv` | 平台可接收结构化 result rows 或 artifact 引用 |
| keep/discard/crash | 映射为 decision、failed attempt、blocked/degraded |
| branch per run | 平台记录 worktree/branch/commit 引用，不创建分支 |

本平台如果要支持这类外部 Runtime，关键不是跑实验，而是让外部 Runtime 能登记:

```text
run_id
question_ref
hypothesis_ref
protocol_ref
editable_scope
verifier_ref
metric_contract
budget_contract
commit_before
commit_after
result_artifacts
metric_rows
failure_mode
decision_ref
```

## 其他端到端系统

### Sakana AI Scientist v1/v2

AI Scientist v1 是早期代表性端到端系统，覆盖 idea generation、literature search、code experiments、paper writing 和 automated review。它证明了 LLM agent 可以把一个 ML 研究模板跑到论文草稿，但模板依赖很强。

AI Scientist v2 改成更开放的 agentic tree search:

- 先用 topic description 生成 structured research ideas。
- 主实验阶段用 best-first tree search 和 experiment manager agent 探索多条路径。
- 去掉对人工模板的强依赖，泛化到更开放的 ML research domain。
- README 明确提示 v2 不一定比 v1 产出更好，强模板场景下 v1 成功率更高，v2 更探索、成功率更低。
- README 也明确提示会执行 LLM 写的代码，需要 sandbox。

启发: 开放式探索需要 tree search、debug depth、parallel workers、node failure metadata 和 workspace trace。平台应该记录这些 trace 引用，但不能执行 tree search。

### AI-Researcher

AI-Researcher 提供两种输入模式:

- 用户给详细 idea description。
- 用户给 reference papers，让系统基于参考文献生成 idea。

公开能力覆盖 literature review、idea generation、algorithm design and implementation、algorithm validation and refinement、result analysis、manuscript creation。它更像一个完整 research agent 产品，而不是一个最小实验 loop。

启发: 需要把「用户模糊目标」「参考论文」「系统生成 idea」「实现策略」「验证结果」「论文」拆成不同 provenance 对象。平台不能只保存最后论文。

### Agent Laboratory

Agent Laboratory 的目标更偏 research assistant。它不把人类 creativity 替换掉，而是让人类提供 idea 和 notes，agent 承担 literature review、experimentation、report writing。它有 copilot mode，也支持 AgentRxiv，让 agent 发布、读取和复用其他 agent 的研究输出。

启发: 对真实科研更稳的是 copilot 和 checkpoint，而不是全自动替代。平台应支持 handoff、checkpoint、artifact refs、review 和 experience curation，方便人类或下一轮 agent 接手。

### RD-Agent

RD-Agent 代表工业 R&D loop，尤其是 data science、Kaggle、quant、fine-tuning 等场景。核心模式是 Research agent 提出想法，Development agent 实现并跑评测，然后循环。它在 MLE-Bench 上公开报告了较强结果，也把 trace viewing 和 Web UI 做成产品能力。

启发: Research/Development 分工适合外部 Runtime；平台侧只应该沉淀 idea、implementation refs、benchmark adapter contract、result artifact、decision 和经验。

## FutureHouse 与科学 RAG

FutureHouse 的 PaperQA2 是科学文献 RAG 的代表性开源 package。它不是自动科学家，但解决了自动科研的前置问题: 如何在文献、PDF、元数据和引用中找到可追溯证据。

PaperQA2 的关键能力:

- 面向 scientific literature 的 RAG。
- metadata-aware embedding。
- LLM re-ranking 和 contextual summarization。
- agentic adding/querying documents。
- citation count、journal quality、retraction check 等 metadata。
- 支持 PDF、text、Office、source code，2025 年后增强了 table、figure、multimodal parsing。

启发:

- 平台的 `sources` 不应只是 URL 字符串，应保存 metadata、provenance、source quality、retraction/check status、retrieval context 引用。
- 但平台不应内置 embedding/RAG 原文表。文献检索和索引属于外部 Runtime 或外部工具，平台只保存 source refs 和证据摘要。

## 物理自动实验室

化学和材料方向已经有真实闭环，但它们的自动化边界与 AI-for-AI paper factory 很不同。

A-Lab 的模式是:

```text
materials candidate
  -> synthesis recipe
  -> robotic execution
  -> characterization
  -> active learning update
  -> next candidate
```

Coscientist 的模式是:

```text
scientific goal
  -> literature/web/tool planning
  -> code/tool invocation
  -> robotic chemistry protocol
  -> experimental observation
  -> next action
```

ChemCrow 则是把 LLM 和 chemistry tools 接起来，让模型调用专业工具完成合成、性质查询、反应规划等任务。

启发:

- 物理实验的 artifact 不只是日志，还包括样品、仪器输出、谱图、图像、环境条件和安全记录。
- 平台可保存 artifact metadata 和 URI，不保存大 PDF、视频、音频、原始谱图大文件或仪器数据库。
- 物理实验更需要 `blocked` 和 `degraded`，因为试剂、设备、协议、污染、仪器漂移都会让结论不可接受。

## 评估与质量问题

### Manuscript-only review 不够

ResearchArena 的 2026 版本做了一个关键对照: 同一批 agent-generated papers，用 manuscript-only reviewer、artifact-aware peer review 和 human meta-review 三种视角评估。结果显示，只看论文文本会明显过于乐观；检查工作区和 artifact 后，实验严谨性成为主要瓶颈，常见失败包括 fabricated results、underpowered experiments、plan/execution mismatch。其摘要中还指出 117 篇 agent-generated papers 没有达到顶会 acceptance bar。

这说明平台必须把 review 分成至少两类:

- manuscript-only review: 看文本是否像论文。
- artifact-aware review: 看代码、数据、日志、图表和指标是否支持 claim。

只有后者能支撑 decision。

### Claim-level fabrication 需要结构化审计

FabScore 把 AI-generated papers 和 associated code 放在一起评估，pipeline 是:

```text
result extraction
  -> static analysis
  -> code execution
  -> verdict generation
```

其公开 README 报告了 144 篇带代码论文、6978 个 claim 的评估，整体 fabrication rate 为 21.2%，并按 data fabrication、experiment fabrication、result fabrication、no code、insufficient evidence、verified 分类。

对平台的启发:

- evidence 不能只是一段主观总结，应绑定 claim、code/artifact、execution result、verdict。
- `insufficient evidence` 和 `unverifiable` 应是合法状态。
- review audit 应要求 claim -> artifact 的可解析引用链。

### Benchmark 仍需控制 confounders

AstaBench、MLE-Bench、RE-Bench 共同说明: agent benchmark 必须控制工具、成本、模型、数据、运行环境和评估接口。否则很难比较系统能力。

平台侧应保存 benchmark suite contract、adapter contract、input artifact、output artifact、metric schema、run metadata 和 audit result；执行仍由外部 Runtime 完成。

## 共同 pipeline 抽象

把上述系统压平后，一个更适合作为产品主线的自动科研 pipeline 应该贴近 FARS/Karpathy 的方法论命名，而不是平台内部对象名:

```text
1. Idea Pool
   papers, repos, datasets, benchmark gaps, researcher ideas, prior failures, runtime observations

2. Hypothesis
   falsifiable claim, expected effect, acceptance criteria, rejection criteria, source trace

3. Plan
   one change, editable scope, fixed verifier, controls, budget, result requirements

4. Experiment
   external runtime branch/workspace, experiments, logs, generated code, generated paper

5. Result
   scores, logs, figures, badcases, code refs, data refs, notebooks, PDFs, lab outputs, hashes

6. Review
   result interpretation, artifact-aware review, reproduction status, contradiction, limitations

7. Decision
   keep, discard, continue, retry, blocked, degraded, archived, superseded

8. Lesson
   durable experience only after explicit preview/apply, with source trace
```

artifact、evidence、benchmark run 和 audit export 是 Result/Review/Decision 的审计支撑，不应作为用户看到的平级主流程。关键不是让每一步都自动化，而是让每一步都有可恢复、可审计、可拒绝的状态。

## AutoResearch Platform 参考改进

以下建议只针对平台控制面，不触碰 AGENTS.md 禁止项。

### 1. Plan contract 成为一等对象

借鉴 Karpathy AutoResearch 和 benchmark 系统，平台应能表达外部 Runtime 的 run contract:

- 可编辑范围。
- 固定 verifier。
- metric schema。
- budget。
- allowed dependencies。
- expected artifacts。
- failure handling。
- keep/discard/continue decision。

平台不执行 contract，只保存 contract 和外部 Runtime 的结果引用。

### 2. Review 支撑 claim-level evidence matrix

借鉴 FabScore，把论文或报告里的 claim 拆成结构化证据矩阵:

| 字段 | 含义 |
| --- | --- |
| claim | 论文或报告中的可验证主张 |
| claim_location | PDF/page/section/line 或 markdown anchor |
| artifact_ref | 支撑该 claim 的代码、日志、表格、图、实验输出 |
| verification_method | static analysis、execution、human review、external lab review |
| verdict | verified、contradicted、unverifiable、insufficient_evidence、fabricated |
| limitations | 证据边界和不可外推范围 |

这能作为 Review 阶段的支撑材料，服务 `evidence summary`、review audit 和 decision，但不暴露成另一条主流程。

### 3. Artifact-aware review gate

ResearchArena 说明 manuscript-only review 不可靠。平台应把 artifact-aware review 作为进入 decision 前的默认质量门:

- 是否能解析 artifact refs。
- 是否有 metric schema。
- 是否有代码或实验记录支撑关键结果。
- 是否记录 negative results 和 failed attempts。
- 是否存在 plan/execution mismatch。
- 是否存在 `blocked` 或 `degraded` 未处理。

### 4. Negative result 和 failed attempt 优先级提升

FARS 和 Karpathy AutoResearch 都把失败或负结果视为信息。平台应在工作台和 API 中让失败路线可见:

- `failed_attempts` 不应只出现在 retrospective。
- `rejected`、`blocked`、`degraded`、`discard` 都应能进入经验查询。
- 经验沉淀时要优先保存「为什么不行」和「下次如何避免重复」。

### 5. Source quality metadata

借鉴 PaperQA2 和科学 RAG，`sources` 可以增强 metadata 字段，但不存原文:

- publication metadata。
- citation/retraction/check status。
- license/open-access status。
- source type。
- retrieval provenance。
- extraction confidence。

### 6. FARS/Karpathy-style production dashboard

工作台可以支持查看:

- Idea Pool 来源分布。
- Hypothesis 状态。
- Plan 的 verifier、controls 和 result requirements 完整度。
- Experiment/Result 的外部引用完整度。
- Review 覆盖和质量缺口。
- Decision 的 keep/discard/continue/retry/blocked 分布。
- Lesson 对下一轮 Hypothesis 的反馈。

这只是可视化平台记录，不是 agent orchestration。

## 明确不做

为了保持平台边界，以下能力必须留给外部 Runtime:

- LLM provider router、fallback、限流、成本治理、key 管理。
- 自动 ideation/planning/experiment/writing agent loop。
- benchmark executor、模型训练、architecture search。
- GPU/cluster/job scheduler。
- 科学 RAG 原文索引、embedding table、PDF body 存储。
- 实验室机器人控制、仪器数据库读写、外部 Runtime 工作目录读写。
- 自动经验抽取。长期经验只能显式 preview/apply。

## 对我们下一步最有价值的支持面

按优先级:

1. 先把外部 Runtime 的主路径收敛为 `GET /api/v1/method-loop`、`POST /api/v1/ideas`、`POST /api/v1/hypotheses`、`POST /api/v1/plans`、`POST /api/v1/results`、`POST /api/v1/reviews`、`POST /api/v1/decisions` 和显式 lesson curation。
2. 为 Plan 提供更明确的 verifier、benchmark adapter、budget、controls 和 result requirements 记录方式。
3. 强化 Result 引用: hash、size、mime、storage、summary、生成环境、可复现入口。
4. 把 claim-level evidence 和 artifact-aware review audit 放在 Review/Decision 前的质量门，而不是作为新主导航。
5. 在 workbench 中优先展示 blocked/degraded、failed attempts、negative results、unresolved refs 和下一轮 Hypothesis 来源。
6. 为 Karpathy-style metric loop、FARS-style paper factory、physical-lab-style external artifacts 写三套 runtime cookbook，但三者都服从同一个方法论闭环。

如果只做一件事，优先做 Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson 的可审计闭环。它比自动生成更多论文更接近平台价值。

## 参考资料

- Analemma, [Introducing FARS](https://analemma.ai/blog/introducing-fars/), [FARS live page](https://analemma.ai/fars/), [FARS GitLab account](https://gitlab.com/fars-a)。
- Andrej Karpathy, [autoresearch](https://github.com/karpathy/autoresearch), [program.md](https://github.com/karpathy/autoresearch/blob/master/program.md)。
- Sakana AI, [The AI Scientist](https://github.com/SakanaAI/AI-Scientist), [arXiv:2408.06292](https://arxiv.org/abs/2408.06292)。
- Sakana AI, [The AI Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2), [arXiv:2504.08066](https://arxiv.org/abs/2504.08066)。
- HKUDS, [AI-Researcher](https://github.com/HKUDS/AI-Researcher), [project page](https://autoresearcher.github.io), [arXiv:2505.18705](https://arxiv.org/abs/2505.18705)。
- Samuel Schmidgall et al., [Agent Laboratory](https://github.com/SamuelSchmidgall/AgentLaboratory), [arXiv:2501.04227](https://arxiv.org/abs/2501.04227)。
- Microsoft, [RD-Agent](https://github.com/microsoft/RD-Agent), [documentation](https://rdagent.readthedocs.io/en/latest/index.html), [arXiv:2505.14738](https://arxiv.org/abs/2505.14738)。
- FutureHouse, [PaperQA2](https://github.com/Future-House/paper-qa), [PaperQA2 paper page](https://paper.wikicrow.ai)。
- Allen AI, [AstaBench](https://github.com/allenai/asta-bench), [arXiv:2510.21652](https://arxiv.org/abs/2510.21652)。
- OpenAI, [MLE-Bench](https://github.com/openai/mle-bench), [arXiv:2410.07095](https://arxiv.org/abs/2410.07095)。
- METR, [RE-Bench](https://github.com/METR/RE-Bench)。
- Hui Chen et al., [FabScore](https://github.com/chchenhui/fabscore), [preprint PDF](https://chchenhui.github.io/papers/FabScore.pdf)。
- Zhengxin Zhang et al., [How Far Are We From True Auto-Research?](https://arxiv.org/abs/2605.19156)。
- Google DeepMind, [AlphaFold 3 Nature paper](https://www.nature.com/articles/s41586-024-07487-w), [alphafold3](https://github.com/google-deepmind/alphafold3)。
- EvolutionaryScale, [ESM repository](https://github.com/evolutionaryscale/esm)。
- Chai Discovery, [chai-lab](https://github.com/chaidiscovery/chai-lab)。
- Boltz team, [boltz](https://github.com/jwohlwend/boltz)。
- Microsoft, [MatterGen](https://github.com/microsoft/mattergen), [Nature paper](https://www.nature.com/articles/s41586-025-08628-5)。
- Google DeepMind, [GNoME Nature paper](https://www.nature.com/articles/s41586-023-06735-9), [materials_discovery](https://github.com/google-deepmind/materials_discovery)。
- University of Liverpool and collaborators, [Coscientist Nature paper](https://www.nature.com/articles/s41586-023-06792-0)。
- Berkeley Lab and collaborators, [A-Lab Nature paper](https://www.nature.com/articles/s41586-023-06734-w)。
- White Lab, [ChemCrow](https://github.com/ur-whitelab/chemcrow-public), [Nature Machine Intelligence paper](https://www.nature.com/articles/s42256-024-00832-8)。
