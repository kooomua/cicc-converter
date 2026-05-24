# 本地浏览器版使用说明

这个版本是在你自己的电脑上运行，不需要服务器，也不需要打开 Codex 对话框。

## 原理

当前版本已经还原为稳定的单一路线：

```text
浏览器上传 input 文件
→ Inspector 检查输入文件
→ Converter 调用 DeepSeek/OpenAI-compatible API 生成完整 CiCC LaTeX
→ Evaluator 本地检查并编译 pdflatex/bibtex
→ 如果 PDF 编译失败，AI Repairer 根据编译错误修 tex
→ 如果 Evaluator 发现 equation/figure/table 布局 warning，AI Layout Repairer 局部修 tex
→ 浏览器下载 output.zip
```

## 第一次安装

在项目目录运行：

```bash
bash scripts/setup_local.sh
```

它会创建 `.venv`，安装依赖，并生成 `.env`。

然后打开 `.env`，把这一行：

```text
CICC_LLM_API_KEY=replace_me
```

改成你的 API key。

DeepSeek 配置示例：

```text
CICC_LLM_BASE_URL=https://api.deepseek.com
CICC_LLM_MODEL=deepseek-chat
CICC_LLM_API_STYLE=chat
CICC_LLM_THINKING=enabled
CICC_LLM_REASONING_EFFORT=max
CICC_MAX_OUTPUT_TOKENS=32768
CICC_MAX_CONVERSION_ATTEMPTS=5
```

`CICC_MAX_CONVERSION_ATTEMPTS=5` 表示最多自动跑 5 轮：

```text
converter_attempt_1 → evaluator_attempt_1
converter_attempt_2 → evaluator_attempt_2
...
```

## 每次启动

```bash
bash scripts/start_local.sh
```

然后打开浏览器：

```text
http://localhost:8000
```

## 怎么上传

推荐上传一个 zip，里面放：

```text
manuscript.tex 或 manuscript.docx
figures/
ref.bib
其他图片文件
```

也可以直接多选文件上传。

如果同时有 `.docx` 和 `.tex`，在网页里的 Primary source 选择一个：

- 使用 docx
- 使用 tex

## 结果在哪里

网页会显示任务状态。完成后点击下载。

本地文件也会保存在：

```text
jobs/JOB_ID/output/
jobs/JOB_ID/run_log/
```

特殊图片会同时保留可编译版本和原始候补文件：

```text
jobs/JOB_ID/output/figures/              # LaTeX 使用的 png/pdf 图片
jobs/JOB_ID/output/original_figures/     # 原始 tif/tiff/emf/wmf 候补文件
jobs/JOB_ID/output/IMAGE_CONVERSION_NOTES.txt
```

`.tif/.tiff` 会转成 `.png`，`.emf/.wmf` 会转成 `.pdf`。

如果失败，先看：

```text
jobs/JOB_ID/status.json
jobs/JOB_ID/run_log/error.txt
jobs/JOB_ID/run_log/latest_eval_report.json
```

## 当前流程状态

现在没有 IR、没有 route-only、没有 local baseline。

网页上传后只会走：

```text
Inspector → Converter → postprocess → Evaluator
如果编译失败：AI Repairer → Evaluator
如果 Evaluator 发现 equation/figure/table 布局 warning：AI Layout Repairer → Evaluator
Package
```

## Layout Repair 配置

`.env` 里相关配置：

```text
CICC_MAX_LAYOUT_REPAIR_ATTEMPTS=1
CICC_EVAL_LAYOUT_REPAIR_ENABLED=true
```

`CICC_EVAL_LAYOUT_REPAIR_ENABLED=true` 表示即使 PDF 编译通过，只要 evaluator/static checker 报告 equation、figure、table 相关布局 warning，也会自动进入一轮 AI Layout Repairer。
