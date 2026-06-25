# 大声朗读 - 微信小程序

本项目是「大声朗读」的微信小程序端，采用 **web-view 嵌入 H5** 的方案实现。小程序本身只提供入口页面和 web-view 容器，阅读、播放、句子拆分等核心功能均由 H5 页面承载。

## 目录结构

```
miniprogram/
├── app.js                  # 小程序全局逻辑
├── app.json                # 小程序页面与窗口配置
├── app.wxss                # 小程序全局样式
├── project.config.json     # 微信开发者工具项目配置
├── sitemap.json            # 小程序索引配置
├── pages/
│   ├── index/              # 书目列表入口页
│   │   ├── index.js
│   │   ├── index.json
│   │   ├── index.wxml
│   │   └── index.wxss
│   └── web/                # web-view 容器页
│       ├── web.js
│       ├── web.json
│       ├── web.wxml
│       └── web.wxss
└── README.md
```

## 如何运行

1. 打开 **微信开发者工具**；
2. 选择「导入项目」；
3. 选择本 `miniprogram` 目录；
4. 填写你的小程序 AppID（测试阶段可使用测试号）；
5. 点击「编译」。

## 配置 H5 服务地址

在 `app.js` 中修改 `h5BaseUrl` 为你部署后的 H5 服务地址：

```javascript
App({
  globalData: {
    h5BaseUrl: 'https://your-cloudbase-domain.com/web'
  }
});
```

如果你使用微信云托管，部署后通常会得到一个类似以下的地址：

```
https://<服务名>-<环境ID>.service.tcloudbase.com
```

则 H5 基础地址为：

```
https://<服务名>-<环境ID>.service.tcloudbase.com/web
```

## 页面说明

### pages/index/index

- 展示书目列表；
- 用户点击书籍后，拼接 H5 URL 并跳转到 `pages/web/web`。

### pages/web/web

- 使用 `<web-view>` 加载 H5 页面；
- 通过 URL 参数 `?chapter=1` 指定要打开的章节；
- 可通过 `bindmessage` 接收 H5 发来的消息（可选）。

## 与 H5 的交互（可选）

如果 H5 页面需要通知小程序（例如播放开始、播放结束、跳转其他章节），可以在 H5 中引入微信 JSSDK：

```html
<script src="https://res.wx.qq.com/open/js/jweixin-1.6.0.js"></script>
```

然后调用：

```javascript
wx.miniProgram.postMessage({
  data: { action: 'playStarted', chapter: 1 }
});
```

小程序端在 `pages/web/web.js` 的 `onMessage` 方法中接收处理。

## 注意事项

1. **web-view 只能加载线上 HTTPS 地址**，本地 `start_server.py` 启动的服务无法用于小程序；
2. 部署 H5 后，需要把 H5 域名配置到小程序后台的「开发管理 → 开发设置 → 服务器域名」的 **request 合法域名** 和 **业务域名** 中；
3. 音频文件建议放到 CDN 或云存储，H5 中通过绝对 URL 访问；
4. web-view 内的音频在锁屏或切后台时可能会暂停，这是微信 web-view 的限制。

---

# 微信云托管接入指南

## 一、云托管能做什么

微信云托管可以部署你的 H5 页面，并提供一个 HTTPS 访问地址。你不需要自己买服务器、配域名、配 HTTPS。

你需要托管的内容：
- `web/` 目录下的 H5 页面（HTML / JS / CSS / JSON 数据）
- 可选：音频文件（也可以单独放云存储 CDN）

## 二、部署前需要调整的内容

### 1. H5 资源路径改为绝对 URL

当前 `web/app.js` 中使用了相对路径：

```javascript
audioUrl: '../resource/01.The Boy Who Lived.m4a',
dataUrl: `data/chapter${chapterId}.json`
```

部署到云托管后，需要改成绝对 URL：

```javascript
const CDN_BASE = 'https://your-cdn-or-cloudbase-domain.com';

const state = {
  audioUrl: `${CDN_BASE}/resource/01.The Boy Who Lived.m4a`,
  dataUrl: `${CDN_BASE}/web/data/chapter${chapterId}.json`
};
```

建议做法：把 `web/app.js` 改成根据当前 host 自动判断：

```javascript
const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
const BASE_URL = isLocal ? '' : 'https://your-cloudbase-domain.com';

const state = {
  audioUrl: `${BASE_URL}/resource/01.The Boy Who Lived.m4a`,
  dataUrl: `${BASE_URL}/web/data/chapter${chapterId}.json`
};
```

这样本地开发和云托管都能跑。

### 2. 音频文件放到哪里

云托管可以托管静态文件，但音频文件较大（30MB+），建议：

**方案 A：放云存储（推荐）**
- 上传到微信云开发的「云存储」；
- 获取文件的 HTTPS 下载链接；
- 在 `app.js` 中使用该链接。

**方案 B：放云托管静态服务**
- 直接把 `resource/` 目录一起部署到云托管；
- 适合文件不多、访问量不大的情况。

### 3. JSON 数据文件放哪里

`web/data/chapter1.json` 建议：
- 和 H5 页面一起部署到云托管；
- 通过 `/web/data/chapter1.json` 访问。

## 三、云托管部署步骤

### 方式一：通过云开发控制台上传（最简单）

1. 登录 [微信云开发控制台](https://console.cloud.tencent.com/tcb)；
2. 创建环境，进入「云托管」；
3. 创建服务，选择「静态网站」或「静态托管」；
4. 把 `web/` 目录打包成 zip 上传；
5. 部署成功后，复制访问 URL；
6. 把 URL 填到 `miniprogram/app.js` 的 `h5BaseUrl` 中。

### 方式二：通过 CLI / GitHub Actions 自动部署

如果你后续经常更新 H5，可以配置 CI/CD：

```yaml
# .github/workflows/deploy-cloudbase.yml 示例
name: Deploy to CloudBase
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy web to CloudBase
        uses: TencentCloudBase/cloudbase-action@v2
        with:
          secretId: ${{ secrets.TCB_SECRET_ID }}
          secretKey: ${{ secrets.TCB_SECRET_KEY }}
          envId: your-env-id
          staticSrcPath: ./web
```

> 具体配置请参考微信云托管官方文档。

## 四、小程序后台配置

部署完成后，必须在小程序后台配置域名：

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)；
2. 进入「开发 → 开发管理 → 开发设置」；
3. 在「服务器域名」中添加：
   - **request 合法域名**：你的云托管域名
   - **downloadFile 合法域名**：音频/图片资源域名（如果用云存储也要加）
   - **业务域名**：在「业务域名」中添加你的云托管域名（web-view 要求）
4. 保存后，在微信开发者工具中「详情 → 本地设置」刷新项目配置。

## 五、可能遇到的问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 小程序打开 H5 空白 | 域名未配置到业务域名 | 去小程序后台添加业务域名 |
| H5 中音频无法播放 | 音频域名未配置 downloadFile | 添加音频 CDN 域名到 downloadFile 合法域名 |
| H5 无法加载 data/chapter1.json | request 域名未配置或路径错误 | 检查请求 URL 和 request 合法域名 |
| 本地开发正常，小程序不行 | 小程序只能访问线上 HTTPS | 确保所有资源都是 HTTPS |
| 锁屏后音频暂停 | web-view 限制 | 如必须后台播放，需改用原生小程序音频 |

## 六、费用参考

- 微信云托管有免费额度，一般个人项目足够；
- 云存储按流量和容量计费，音频文件多/访问量大时需要关注；
- 具体以微信云开发官方计费说明为准。
