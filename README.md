# 🚀 OpenSwap Guide - 开源替代方案指南

一个专注于开源软件替代方案、自托管解决方案和本地 AI 部署的技术内容站。

## 📁 项目结构

```
├── content/          # 文章内容 (Markdown)
├── layouts/          # 自定义模板
├── themes/           # PaperMod 主题
├── public/           # 生成的静态文件
├── hugo.toml         # 站点配置
└── .github/          # GitHub Actions 工作流
```

## 🛠️ 本地开发

```bash
# 安装 Hugo Extended (需要 0.146.0+)
# Ubuntu/Debian:
wget https://github.com/gohugoio/hugo/releases/download/v0.147.4/hugo_extended_0.147.4_linux-amd64.deb
sudo dpkg -i hugo_extended_0.147.4_linux-amd64.deb

# 克隆主题
git submodule update --init --recursive

# 启动开发服务器
hugo server -D
```

## 🚀 部署到 GitHub Pages

### 方法 1: 一键部署（推荐）

1. **创建新仓库**
   - 访问 https://github.com/new
   - 仓库名：`开源替代指南.github.io`（替换为你的用户名）

2. **推送代码**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/opensource-alternatives.git
   git push -u origin main
   ```

3. **启用 Pages**
   - 进入仓库 Settings → Pages
   - Source 选择 "GitHub Actions"
   - 等待部署完成

### 方法 2: 直接上传 public 目录

如果你不想用 Hugo，可以直接上传 `public/` 目录到任何静态托管服务：
- GitHub Pages
- Cloudflare Pages
- Netlify
- Vercel
- Surge.sh

## 💰 广告变现

### A-Ads (Anonymous Ads)
无需 KYC 的加密货币广告网络：

1. 访问 https://anonymousads.com
2. 创建广告单元
3. 替换 `hugo.toml` 中的 `a_ads_id`
4. 重新构建站点

### 其他无 KYC 广告选项
- **Coinzilla**: 加密货币广告
- **Adsterra**: 支持加密货币支付
- **PopAds**: 低门槛

## 📝 已生成内容

| 文章 | 主题 |
|------|------|
| Google Drive 替代方案 | 云存储对比 |
| Jellyfin vs Plex vs Emby | 媒体服务器 |
| Ollama vs LM Studio vs LocalAI | 本地 AI 运行 |
| 密码管理器对比 | 安全工具 |
| AdGuard Home vs Pi-hole | DNS 广告拦截 |
| 自托管 AI 栈 | Docker 部署指南 |
| 反向代理对比 | 网络基础设施 |
| Git 服务器对比 | 开发工具 |
| Docker Compose 指南 | 入门教程 |
| Nextcloud vs ownCloud | 云办公套件 |
| 项目管理工具 | Jira 替代方案 |
| 隐私栈指南 | 去 Google 化 |
| 自动化指南 | Watchtower + Ansible |

## 🤖 自动化内容管线

使用 `generate_content.py` 批量生成新文章：

```bash
python generate_content.py --topic "New Topic" --count 5
```

## 📊 SEO/GEO 优化

- JSON-LD 结构化数据
- FAQ 页面优化
- 对比表格生成
- 内部链接网络
- 快速加载（静态 HTML）

## ⚖️ 免责声明

本站内容仅供技术参考，不构成任何商业建议。软件功能可能随版本更新而变化。
