# 把本地应用变成可打开的网址

代码已经配置为 Render 免费服务。你只需要完成托管账号登录和创建服务。

1. 点击 [Deploy to Render](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fgengtong0601-hub%2Fprocurement-audit-planner)。
2. 选择用 GitHub 登录或注册 Render；授权访问 `gengtong0601-hub/procurement-audit-planner`。
3. 创建页面会读取仓库根目录的 `render.yaml`。确认分支为 `main`，服务计划为 **Free**，然后点击创建/部署按钮。
4. 等待部署完成并显示 **Live**，点击 Render 显示的 HTTPS 服务地址。这才是可以分享和打开的实际网站链接。

如果部署入口没有自动选中仓库：在 Render 中选择新建 Blueprint，连接上述仓库，
选择 `main` 分支，使用根目录的 `render.yaml` 创建服务。

首次访问选择 **Prepared evidence demonstration**，再点 **Start review**。
它使用朋友项目中的真实公开证据和准备好的判断；不需要 API 密钥，也不会发起模型调用。
审计风险仍由你逐项批准、修改或拒绝，最后的签字也由你完成。

免费服务可能在空闲后休眠，首次打开可能较慢。没有挂载付费磁盘，运行记录会随实例
重启或重新部署而丢失；完成后点击 **Download evidence & pack** 保存。

如之后需要启用 Live Claude API 模式，在 Render 的环境变量设置中安全填写
`ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`、`HARNESS_ACCESS_TOKEN`，然后重新部署。
不要把密钥填入聊天、网页前端或提交到 GitHub。公开网址能打开与真实模型流程通过验证
是两件不同的事；当前免费部署默认提供 prepared 模式。

发布后请把实际网址填入 README 的 Deployed website URL，并按 DEPLOYMENT.md
完成公网冒烟测试。仓库链接和部署按钮都不能代替实际应用网址。
