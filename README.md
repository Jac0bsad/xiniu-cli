# xiniu-cli

`xiniu-cli` 是烯牛数据 MCP 服务的命令行客户端，用于在终端中直接查看可用工具、检查参数 schema，并调用远端能力。

它适合下面几类场景：

- 在终端里快速验证某个 MCP 工具是否可用
- 调试工具入参和返回结果
- 配合脚本或自动化流程调用烯牛数据服务
- 作为本地开发和集成测试时的轻量 CLI 封装

默认服务地址为：

```text
http://vip.xiniudata.com/mcp
```

## 功能特性

- 支持列出远端 MCP 工具
- 支持查看单个工具的完整 schema
- 支持通过 JSON 字符串、JSON 文件或 `KEY=VALUE` 形式传参
- 支持把远端工具名直接当作本地子命令调用
- 支持从命令行、环境变量、`.env`、本地配置文件中解析配置
- 支持输出简化结果或完整原始 MCP 响应

## 安装

推荐使用 `uv` 或 `pipx` 安装为全局命令行工具。

### 通过 PyPI 安装

```bash
uv tool install xiniu-cli
```

或：

```bash
pipx install xiniu-cli
```

安装完成后即可使用：

```bash
xiniu --help
```

### 从源码安装

如果你正在本地开发或想直接体验当前仓库版本：

```bash
uv tool install --from . xiniu-cli
```

或：

```bash
pipx install .
```

开发依赖安装：

```bash
uv sync
```

## 快速开始

首先配置 API Key：

```bash
xiniu config set-api-key <your_api_key>
```

查看当前配置是否生效：

```bash
xiniu config show
```

列出远端可用工具：

```bash
xiniu list-tools
```

查看某个工具的参数定义：

```bash
xiniu describe get_company_info
```

调用工具：

```bash
xiniu call get_company_info \
  --json '{"firm_name":"上海烯牛信息技术有限公司","aspect":"企业基本信息"}'

xiniu call get_company_info \
  --json-file ./payloads/company-info.json
```

## 配置说明

CLI 会按以下优先级解析配置：

1. 命令行参数 `--api-key`、`--server-url`
2. 环境变量 `XINIU_API_KEY`、`XINIU_MCP_URL`
3. 当前工作目录中的 `.env`
4. 用户配置文件 `~/.config/xiniu/config.json`
5. 内置默认服务地址

### 写入本地配置文件

保存 API Key：

```bash
xiniu config set-api-key <your_api_key>
```

自定义服务地址：

```bash
xiniu config set-server-url http://vip.xiniudata.com/mcp
```

查看当前解析结果：

```bash
xiniu config show
```

输出 JSON 格式配置：

```bash
xiniu config show --json
```

### 使用环境变量

```bash
export XINIU_API_KEY=your_api_key
export XINIU_MCP_URL=http://vip.xiniudata.com/mcp
```

### 使用 `.env`

在项目根目录创建 `.env` 文件：

```dotenv
XINIU_API_KEY=your_api_key
XINIU_MCP_URL=http://vip.xiniudata.com/mcp
```

如果你只想临时覆盖配置，也可以直接传参：

```bash
xiniu --api-key your_api_key list-tools
```

## 使用示例

### 1. 列出全部工具

```bash
xiniu list-tools
```

输出完整 JSON：

```bash
xiniu list-tools --json
```

### 2. 查看工具 schema

```bash
xiniu describe get_company_info
```

### 3. 推荐：使用 JSON 文件调用工具

当参数结构较复杂时，优先使用 `--json-file`。这样可以避免 shell 转义、换行维护和命令历史复用上的问题。

先准备一个文件，例如 `./payloads/company-info.json`：

```json
{
  "firm_name": "上海烯牛信息技术有限公司",
  "aspect": "企业基本信息"
}
```

然后调用：

```bash
xiniu call get_company_info \
  --json-file ./payloads/company-info.json
```

### 4. 使用 JSON 字符串调用工具

```bash
xiniu call get_company_info \
  --json '{"firm_name":"上海烯牛信息技术有限公司","aspect":"企业基本信息"}'
```

### 5. 使用 `--arg` 传参

```bash
xiniu call get_data \
  --arg 'limit=5' \
  --arg 'req_params=[{"table":"tsb_v2.investor","selected_columns":["name"],"filters":[]}]'
```

其中 `VALUE` 支持普通字符串，也支持 JSON 值。

对于 `get_data` 这类嵌套较深的参数，不建议优先使用 `--arg`，更适合写入 JSON 文件后通过 `--json-file` 传入。

### 6. 直接把工具名当作命令调用

下面命令会被自动转换为 `call` 模式：

```bash
xiniu get_company_info \
  --arg 'firm_name=上海烯牛信息技术有限公司' \
  --arg 'aspect=企业基本信息'
```

### 7. 查看原始 MCP 返回结果

默认情况下，CLI 会尽量输出简化后的结构化结果或文本结果；如果你需要完整响应：

```bash
xiniu call get_company_info \
  --json '{"firm_name":"上海烯牛信息技术有限公司","aspect":"企业基本信息"}' \
  --raw
```

## 命令概览

```text
xiniu list-tools
xiniu describe <tool_name>
xiniu call <tool_name> [--json <payload> | --json-file <path> | --arg KEY=VALUE ...] [--raw]
xiniu config set-api-key <api_key>
xiniu config set-server-url <server_url>
xiniu config show [--json]
```

## 开发与测试

安装开发依赖：

```bash
uv sync
```

运行测试：

```bash
uv run pytest
```

本地入口也可以直接通过以下方式执行：

```bash
uv run python main.py --help
```

## 构建与发布

构建发行包：

```bash
uv build --no-sources
```

构建产物默认位于 `dist/` 目录，包括：

- `*.tar.gz`
- `*.whl`

## 适用环境

- Python 3.12 及以上
- 需要可访问烯牛 MCP 服务
- 需要有效的 API Key

## License

MIT
