# 烯牛数据官方 CLI 工具

这个项目把远端 `streamablehttp` MCP 服务包装成一个本地 CLI，方便你直接在命令行里列出工具、查看参数 schema、调用具体工具。

项目采用标准 `src/` 布局，核心代码位于 `src/xiniu_cli/`。
默认 MCP 地址基础路径是：

`http://vip.xiniudata.com/mcp`

API key 不再写死在代码里。CLI 会按下面的优先级解析配置：

1. 命令行参数 `--api-key` / `--server-url`
2. 环境变量 `XINIU_API_KEY` / `XINIU_MCP_URL`
3. 当前工作目录的 `.env`
4. 用户配置文件 `~/.config/xiniu/config.json`
5. 内置默认 MCP 基础地址

## 安装

发布到 PyPI 后，推荐直接安装成命令行工具：

```bash
uv tool install xiniu-cli
```

如果你更习惯 `pipx`，也可以：

```bash
pipx install xiniu-cli
```

如果你是在当前仓库里本地体验，还可以直接从源码安装：

```bash
uv tool install --from . xiniu-cli
```

或者：

```bash
pipx install .
```

开发阶段如果只想补齐本地依赖，再执行：

```bash
uv sync
```

## 构建与发布

本项目使用 `uv` 的现代打包/发布流程：

```bash
uv build --no-sources
```

构建产物会输出到 `dist/` 目录，包括 `.tar.gz` 和 `.whl`。

仓库内置了 GitHub Actions 发布工作流，推荐使用 PyPI Trusted Publishing。配置好 PyPI 的 trusted publisher 后，发布 GitHub Release 即可自动执行：

1. `uv build --no-sources`
2. `uv publish`

## 配置 API Key

最适合普通用户的方式是写入本地配置文件：

```bash
xiniu config set-api-key <your_api_key>
```

如果你还想自定义服务地址：

```bash
xiniu config set-server-url http://vip.xiniudata.com/mcp
```

查看当前生效配置：

```bash
xiniu config show
```

## 开发环境配置

开发时推荐在项目根目录放一个 `.env` 文件：

```dotenv
XINIU_API_KEY=your_api_key
XINIU_MCP_URL=http://vip.xiniudata.com/mcp
```

这样你在仓库里直接运行 `xiniu ...` 或本地调试时都会自动读取。

如果你临时想覆盖配置，也可以直接在命令行上传：

```bash
xiniu --api-key your_api_key list-tools
```

## 常用命令

列出所有远端工具：

```bash
xiniu list-tools
```

查看某个工具的完整 schema：

```bash
xiniu describe get_company_info
```

用 JSON 调用工具：

```bash
xiniu call get_company_info \
  --json '{"firm_name":"上海烯牛信息技术有限公司","aspect":"企业基本信息"}'
```

用 `KEY=VALUE` 形式调用工具：

```bash
xiniu call get_data \
  --arg 'limit=5' \
  --arg 'req_params=[{"table":"tsb_v2.investor","selected_columns":["name"],"filters":[]}]'
```

也支持直接把工具名当作命令来调用，下面这条和 `call` 等价：

```bash
xiniu get_company_info \
  --arg 'firm_name=上海烯牛信息技术有限公司' \
  --arg 'aspect=企业基本信息'
```

如果你希望看到完整的 MCP 返回结构，而不是简化后的文本/结构化输出，可以加上 `--raw`：

```bash
xiniu call get_company_info \
  --json '{"firm_name":"上海烯牛信息技术有限公司","aspect":"企业基本信息"}' \
  --raw
```
