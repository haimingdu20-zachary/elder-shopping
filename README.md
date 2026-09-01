# 老人购物｜第六阶段受控 Tool Calls 原型

这是第六阶段的可操作原型：手机网页 + FastAPI 模拟商城服务。它在前五阶段基础上增加了 DeepSeek 原生 Tool Calls、有限多轮上下文和助手审计；DeepSeek 负责理解，商品/订单/知识数据仍由后端服务提供，不产生真实资金交易。

## 当前范围

- 已实现：商品首页、分类/文字搜索、商品详情、购物车、收货地址、确认订单、模拟支付、订单列表/详情、确认收货、退款/退货申请、客服提示页。
- 已实现：演示家人关系和权限、家人共享订单、家人代买、老人生成代付链接、家人确认模拟代付、家人协助售后请求。
- 已实现：首页语音/文字助手、浏览器语音转文字、固定演示意图解析和受控页面跳转。
- 已实现：DeepSeek 可选接入、本地退货/配送/家人协助 FAQ 检索、知识来源显示、商品/订单/FAQ 三个受控只读 Tool Calls、最近 8 条多轮上下文和助手审计。
- 已实现：商品、购物车、订单和售后使用本地 JSON 持久化；家人关系和协助请求使用 SQLite 持久化。
- 暂不实现：真实支付、物流、商城、客服、短信/OIDC 登录、通知、高风险 Tool Calls、多轮循环/长期记忆、向量数据库、云端 ASR/TTS 和微信小程序。

## 环境

- 推荐：Python 3.11.x、Node.js 22 LTS、npm。
- 本机已验证：Python 3.11.13（`/Users/mac/.local/bin/python3.11`）、Node.js 24.19.0、npm 11.17.0。
- Node.js 24 是本机现有版本，本阶段已用它完成前端类型检查、ESLint 和生产构建；正式环境仍建议按技术文档准备 Node.js 22 LTS。

## 启动后端

在项目根目录执行：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

后端地址：<http://127.0.0.1:8001>

接口文档：<http://127.0.0.1:8001/docs>

健康检查：<http://127.0.0.1:8001/api/v1/health>

家人协助页：<http://127.0.0.1:3000/family>

语音助手入口：<http://127.0.0.1:3000/>

## 启动前端

另开一个终端：

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001/api/v1 npm run dev
```

前端地址：<http://127.0.0.1:3000>

如果后端不是默认地址，可设置：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 npm run dev
```

## 自动化检查

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
cd frontend
npm run typecheck
npm run lint
npm run build
```

本地未配置 `DEEPSEEK_API_KEY` 时不会访问 DeepSeek，助手结果会显示“演示规则”。配置 Key 后，后端才会调用 DeepSeek，并在页面显示实际 provider。

配置方式（只在后端终端或部署环境设置，不要提交 `.env`）：

```bash
export DEEPSEEK_API_KEY='你的密钥'
export DEEPSEEK_BASE_URL='https://api.deepseek.com'
export DEEPSEEK_MODEL='deepseek-v4-pro'
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

DeepSeek API 适配使用 OpenAI 兼容的 `/chat/completions`，输出采用 JSON 约束。真实模型测试与规则测试分开记录。

## 测试环境上线准备

当前项目是前后端两个独立应用：后端运行 FastAPI，前端运行 Next.js standalone。两者需要分别部署；前端生产构建时设置 `NEXT_PUBLIC_API_BASE_URL=/api/v1` 和 `BACKEND_URL=https://你的后端域名`，由 Next.js 同源代理转发 `/api/*`，避免前端继续访问 localhost。

前端生产构建：

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_BASE_URL=/api/v1 BACKEND_URL=https://你的后端域名 npm run build
cp -R .next/static .next/standalone/.next/static
cp -R public .next/standalone/public
cd .next/standalone
PORT=3000 node server.js
```

后端生产启动：

```bash
APP_ENV=production BACKEND_HOST=0.0.0.0 BACKEND_PORT=8000 \
CORS_ORIGINS=https://你的前端域名 \
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

生产环境必须在部署平台密钥管理中设置 `DEEPSEEK_API_KEY`，不能提交 `.env`。当前 JSON/SQLite 数据层适合演示和小规模测试，不适合作为正式多用户生产数据库。

详细上线清单见 [`Docs/上线适配说明.md`](./Docs/上线适配说明.md) 和 [`Docs/部署上线技术文档.md`](./Docs/部署上线技术文档.md)。

## 第二阶段人工验收路径

1. 打开“家人协助”页，确认看到“女儿（演示）”、王阿姨和查看订单、帮忙下单、代为付款、协助售后四项权限。
2. 在“家人代买”中选择商品和地址，生成订单，确认订单显示为家人代买且状态为待付款。
3. 打开老人订单中的 `order-demo-pending`，点击“让家人帮我付款”，复制页面生成的演示链接。
4. 打开家人协助页的待处理请求，进入请求详情，核对商品、数量、金额、地址和预计送达信息。
5. 点击“确认模拟付款”，确认订单变为“已付款/待发货”；重复点击不会重复付款。
6. 对 `order-demo-delivered` 发起“请家人协助售后”，确认请求出现在家人协助页。

第二阶段接口文档：[`第二阶段技术开发文档.md`](./第二阶段技术开发文档.md)

第三阶段文档：[`第三阶段技术适配声明.md`](./第三阶段技术适配声明.md)、[`第三阶段技术开发文档.md`](./第三阶段技术开发文档.md)

第四阶段文档：[`第四阶段技术适配声明.md`](./第四阶段技术适配声明.md)、[`第四阶段技术开发文档.md`](./第四阶段技术开发文档.md)

第五阶段文档：[`第五阶段技术适配声明.md`](./第五阶段技术适配声明.md)、[`第五阶段技术开发文档.md`](./第五阶段技术开发文档.md)

第六阶段文档：[`第六阶段技术适配声明.md`](./第六阶段技术适配声明.md)、[`第六阶段技术开发文档.md`](./第六阶段技术开发文档.md)

## 第三阶段人工验收路径

1. 打开首页，在“想说什么？”输入“查牛奶”，点击发送，确认商品列表切换为牛奶结果。
2. 输入“查订单”或“查物流”，确认进入订单列表。
3. 输入“申请售后”或“让家人付款”，确认只进入订单入口，不直接执行退款或付款。
4. 在支持浏览器语音识别的环境点击“点击说话”，说“查牛奶”；如果浏览器不支持，确认文字输入仍可用。

## 第五阶段知识与工具验收路径

1. 输入“退货怎么申请”，确认回答来自本地 FAQ，并显示参考说明来源。
2. 输入“家人怎么代付”，确认回答家人协助规则，不触发支付。
3. 输入“查牛奶”，确认商品 ID 仍由本地商品服务校验。
4. 打开 [`知识检索接口`](http://127.0.0.1:8001/docs)，可以查看 `GET /api/v1/knowledge/search`。

## 第六阶段 Tool Calls 验收路径

1. 输入“帮我找牛奶”，确认返回结果的 provider 为 DeepSeek，商品 ID 仍由本地商品服务校验，并能看到 `search_products` 工具调用。
2. 输入“退货怎么申请”，确认回答来自本地 FAQ，并显示参考说明来源。
3. 输入“查我的订单”，确认只能查询订单摘要；付款、退款、改地址和确认收货不会被模型直接执行。
4. 传入多轮 `history` 时，后端最多使用最近 8 条用户/助手消息；审计记录写入 `data/assistant_audit.json`，不保存 API Key。

## 第四阶段 AI 验收路径

1. 不配置 Key 运行项目，输入“查牛奶”，确认结果标记为“演示规则”。
2. 配置后端 Key 后重启后端，输入相同指令，确认结果标记为 DeepSeek，并且商品 ID 仍由本地商品服务校验。
3. 输入“让家人付款”或“申请售后”，确认模型只能返回确认入口，不直接调用付款或售后写入。

## 人工验收路径

1. 打开首页，搜索“牛奶”或点击“食品饮料”。
2. 打开“伊利纯牛奶”，数量改为 2，加入购物车。
3. 进入购物车和确认订单，检查商品、金额、地址和预计送达信息。
4. 点击确认，检查二次确认弹层；取消确认时不应创建订单。
5. 确认生成订单，在订单详情中分别试用模拟失败、取消和模拟成功。
6. 刷新页面，确认订单状态没有丢失。
7. 在订单页打开“已送达”的演示订单，进入申请售后。
8. 选择售后原因和退货方式，查看退款确认，再确认提交。
9. 打开手机宽度检查：主要文字不小于 18px，主要按钮至少 48px 高，页面不应横向滚动。

## 登录与数据备份

生产环境必须设置 `AUTH_SECRET` 和 `INVITE_CODES`。邀请码格式支持 `elder:老人邀请码,family:家人邀请码`，也支持 `用户ID:角色:显示名:邀请码`。开发环境默认提供 `elder-demo` 和 `family-demo` 两个测试邀请码。

配置 TOS 后执行备份：

```bash
BACKUP_PROVIDER=tos DATA_DIR=/tmp/data PYTHONPATH=backend python backend/scripts/backup_data.py
```

本地恢复前设置 `RESTORE_CONFIRM=YES`；完整配置见 [`Docs/上线适配说明.md`](./Docs/上线适配说明.md)。

## 数据说明

模拟数据位于 `data/`，由后端首次启动时自动生成。写入采用临时文件 + 原子替换，并包含 `schema_version`。这是单进程、单演示用户、低并发原型，不适合作为生产数据库。

## 安全边界

- 本阶段没有真实支付和模型 Key，不能产生真实扣款。
- 前端不读取数据文件，所有业务操作通过 `/api/v1`。
- 金额由后端根据商品快照计算，不信任前端传入的金额。
- 付款、确认收货和售后提交受后端状态机控制。
- 用户上传照片和真实客服入口暂缓，页面不会伪造处理结果。
