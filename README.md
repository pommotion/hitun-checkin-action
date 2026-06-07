# hitun-checkin-action

每天自动登录 [hitun.io](https://hitun.io/) 签到领流量的 GitHub Action 脚本。

> 设计参考：[beyond-motion/wxread](https://github.com/beyond-motion/wxread) 的 "抓包 → 存 Secret → Action 回放" 模式。

---

## ⚠️ 重要提醒：为什么这个项目跟 wxread 不一样

| 项目 | 后端 | Cloudflare | 抓包后能否直接 requests 回放 |
|---|---|---|---|
| [wxread](https://github.com/beyond-motion/wxread) | weread.qq.com | 无 | ✅ 直接可用，cookie 几周有效 |
| **本项目** | hitun.io | ✅ 有 | ⚠️ **能用，但 cookie 几天就过期** |

**根本原因**：hitun.io 接了 Cloudflare Turnstile，登录后会下发一个 `cf_clearance` cookie，这个 cookie：
- 默认有效期 30 分钟 ~ 几小时（取决于站点配置）
- 跟 IP + User-Agent 绑定
- GitHub Action runner 的 IP 跟用户本地 IP 不同，会直接失效

**所以本项目可以工作，但需要你定期重新抓包**（通常每 1-7 天重新登录一次浏览器、复制 curl、更新 Secret）。如果想要一劳永逸，请参考末尾的 [进阶方案](#进阶方案-需要绝对稳定)。

---

## 🚀 快速开始（推荐流程）

### 第 1 步：Fork 本仓库

点击右上角 **Use this template** 或 Fork 到你自己的 GitHub 账户。

### 第 2 步：浏览器登录 hitun.io + 抓包

1. 用 Chrome / Edge 打开 [https://hitun.io/auth/login](https://hitun.io/auth/login) 并登录
2. 登录成功后会跳转到 [https://hitun.io/user](https://hitun.io/user)
3. 按 `F12` 打开 DevTools，切到 **Network** 面板
4. ✅ 勾选 **Preserve log**（保留日志）
5. 在用户页面找到 **「签到」** 按钮并点击
6. 在 Network 列表里找到 `checkin`（通常是 `https://hitun.io/user/checkin`）
   - Method: `POST`
   - Status: `200`
   - 响应大概是 `{"ret":1,"msg":"签到成功"}` 或 `{"ret":0,"msg":"今日已签到"}`
7. 在那条请求上 **右键 → Copy → Copy as cURL (bash)**
8. 得到的会是这样一段（**保留所有 header 和 cookie**）：
   ```bash
   curl 'https://hitun.io/user/checkin' \
     -H 'authority: hitun.io' \
     -H 'accept: application/json, text/javascript, */*; q=0.01' \
     -H 'cookie: cf_clearance=xxx; PHPSESSID=yyy; ...' \
     -H 'origin: https://hitun.io' \
     -H 'referer: https://hitun.io/user' \
     -H 'user-agent: Mozilla/5.0 ...' \
     -H 'x-requested-with: XMLHttpRequest' \
     --data-raw ''
   ```

### 第 3 步：把 curl 存到 GitHub Secret

1. 进入你 fork 后的仓库
2. **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
3. 添加：
   - **Name**: `HITUN_CURL_BASH`
   - **Value**: 把第 2 步整段 curl 命令贴进去（多行也行）
4. （可选）再加推送相关 Secret：
   - `PUSH_METHOD`：`pushplus` / `wxpusher` / `telegram` / `serverchan` 四选一
   - 对应渠道的 token（详见下方「通知渠道」一节）

### 第 4 步：手动跑一次测试

1. 进入仓库 **Actions** 标签
2. 左侧选 **hitun-checkin** workflow
3. 点 **Run workflow** → 绿色 **Run workflow** 按钮
4. 等待 1-2 分钟，展开最新一次运行查看日志
5. 日志里应该看到：
   ```
   ✅ 签到成功 — 签到成功获得 100MB
   或
   ✅ 今日已签到 — ...
   或
   ❌ Cookie 失效 — 请浏览器重新登录 hitun.io 后抓包更新 HITUN_CURL_BASH
   ```

### 第 5 步：等待每天自动跑

工作流配置的是 `cron: '0 0 * * *'`（UTC 0:00 = 北京时间 8:00）。GitHub Action 定时任务有 5-15 分钟漂移，正常。

---

## 📢 通知渠道（可选）

| 渠道 | 需要的 Secret | 说明 |
|---|---|---|
| `pushplus` | `PUSHPLUS_TOKEN` | 微信推送，[pushplus.plus](https://www.pushplus.plus/) 扫码拿 token |
| `wxpusher` | `WXPUSHER_SPT` | 微信推送，格式 `appToken\|uid`，[wxpusher.zjiecode.com](https://wxpusher.zjiecode.com/) |
| `telegram` | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | TG 机器人通知 |
| `serverchan` | `SERVERCHAN_SPT` | Server 酱 [sct.ftqq.com](https://sct.ftqq.com/) 的 SendKey |

不配置 `PUSH_METHOD` 也能跑，只是没有推送，看 GitHub Action 日志即可。

---

## 🛠️ 本地调试

```bash
git clone <your-fork>
cd hitun-checkin-action
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 把抓到的 curl 命令存到环境变量（注意用单引号包裹，多行也可以）
export HITUN_CURL_BASH='curl ...'
export PUSH_METHOD='serverchan'      # 可选
export SERVERCHAN_SPT='SCT...'        # 可选

python main.py
```

退出码：`0` = 签到成功，`1` = 失败（看日志或推送内容）。

---

## 🔁 Cookie 过期怎么办

Cookie 过期是必然会遇到的，常见表现：

1. Action 日志显示 `❌ Cookie 失效 — ...`
2. 或者 `❌ Cloudflare 拦截 — ...`

**解决方案**（任选一个）：

- **方案 A（简单）**：每天定时跑之前，人工 30 秒更新一次 Secret
  - 浏览器登录 hitun.io → 抓包 → 更新 Secret → 完成
  - 适合：每天有空刷一下手机的人
- **方案 B（半自动）**：把抓包脚本跑在本地机器上
  - 用 [HitunCheckin](https://github.com/orange23qi/HitunCheckin) 跑在 NAS/Mac mini 上
  - 适合：手头有 NAS/服务器的人
- **方案 C（彻底）**：见下方「进阶方案」

---

## 进阶方案（需要绝对稳定）

如果你不想维护 Secret，参考以下三条路：

### 1. undetected-chromedriver 模式（最稳）
改造 `main.py`，换成 Selenium + Chrome + `undetected-chromedriver`，自动过 CF、自动登录、自动点签到。  
参考实现：[orange23qi/HitunCheckin](https://github.com/orange23qi/HitunCheckin)。  
缺点：Action 装包大（~300MB）、慢（2-3 分钟）、CF 越来越严可能某天被识破。

### 2. 自托管 GitHub Runner
在 Mac mini / NAS / VPS 上跑 [self-hosted runner](https://docs.github.com/en/actions/hosting-your-own-runners)，固定 IP，CF 不再是问题。  
适合：手头有 7x24 设备的同学。

### 3. 直接 cron 跑本地脚本
最古老的方案：在 Mac mini / NAS 上用 `cron` / `launchd` 直接跑 `python main.py`，不要 Action 反而最稳。

---

## 📁 项目结构

```
hitun-checkin-action/
├── .github/workflows/checkin.yml   # 定时任务 workflow
├── main.py                          # 主逻辑：解析 curl → 发请求 → 判定结果
├── config.py                        # 读取环境变量 / Secret
├── push.py                          # 4 种推送渠道
├── log_utils.py                     # 日志初始化
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 📜 License

MIT
