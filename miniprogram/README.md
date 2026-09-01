# 大声朗读 - 微信小程序（原生版）

本项目是「大声朗读」的微信小程序原生实现，不再使用 web-view 嵌入 H5。

## 目录结构

```
miniprogram/
├── app.js                  # 小程序全局逻辑
├── app.json                # 小程序页面与窗口配置
├── app.wxss                # 小程序全局样式
├── project.config.json     # 微信开发者工具项目配置
├── sitemap.json            # 小程序索引配置
├── data/
│   ├── books.js            # 书目与章节配置
│   └── chapter1-data.js    # Harry Potter 第 1 章对齐数据（包内）
├── pages/
│   ├── index/              # 书目列表页
│   ├── chapters/           # 章节目录页
│   └── player/             # 播放页（核心）
├── utils/
│   └── audio.js            # 音频管理器封装
└── README.md
```

## 如何运行

1. 打开 **微信开发者工具**；
2. 选择「导入项目」；
3. 选择本 `miniprogram` 目录；
4. 填写你的小程序 AppID（测试阶段可使用测试号）；
5. 点击「编译」。

## 数据来源

- 书目与章节列表配置在 `data/books.js`；
- **Harry Potter**：对齐数据放在 `miniprogram/data/chapter1-data.js`，随小程序包一起发布；
- **新概念英语第二册**：对齐 JSON 和音频均从云存储 CDN 下载，不在小程序包内；
- 音频文件通过 `wx.getBackgroundAudioManager()` 从云存储 CDN 播放。

## 音频与数据配置

在 `app.js` 中配置基础地址：

```javascript
App({
  globalData: {
    audioBaseUrl: 'https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio',
    dataBaseUrl: 'https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/data'
  }
});
```

完整音频 URL 示例：

```
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio/01.The Boy Who Lived.m4a
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio/nce2/01－A Private Conversation.mp3
```

完整数据 URL 示例：

```
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/data/nce2/lesson01.json
```

## 页面说明

### pages/index/index

- 展示书目列表；
- 点击书籍后跳转到 `pages/chapters/chapters`。

### pages/chapters/chapters

- 展示书的章节列表；
- 点击章节后跳转到 `pages/player/player`。

### pages/player/player

核心播放页，包含：
- 逐句播放：每句话旁的 ▶ 按钮；
- 单词高亮：播放时当前单词高亮显示；
- 点击单词播放：点击任意单词可单独播放该词；
- 播放速度：0.5x / 0.75x / 1x / 1.25x / 1.5x / 2x；
- 连续播放：开启后，播放一句自动播放下一句；
- 选段播放：开启“选段”后，在同一句中先后点选两个单词作为起止点，选中的片段会自动播放；
- 阅读位置记忆：退出页面时自动保存当前读到的句子，下次进入自动回到该位置。

## 小程序后台配置

需要在微信公众平台 → 开发管理 → 开发设置 → 服务器域名中添加：

- **request 合法域名**（新概念英语 JSON 数据下载）：
  ```
  https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la
  ```
- **downloadFile 合法域名**（音频播放）：
  ```
  https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la
  ```

## 新增书籍/章节的步骤

1. 生成对齐数据（参考根目录 `scripts/process_nce2.py`）；
2. 把数据放到 CDN 对应目录，或在 `miniprogram/data/` 中新增本地 JS 模块；
3. 在 `data/books.js` 中添加书籍与章节信息；
4. 在 `pages/player/player.js` 中确保数据加载方式（本地/远程）与 `books.js` 中的 `dataType` 一致；
5. 如果有新音频，上传到你的云存储，并确保 `app.js` 中的 `audioBaseUrl` 正确。

## 上传新概念英语数据到 CDN

生成数据后，把 `cdn/nce2/` 下的 96 个 `lessonNN.json` 上传至：

```
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/data/nce2/
```

同时把 96 个 MP3 音频上传至：

```
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio/nce2/
```

上传清单见 `cdn/nce2/manifest.json`。

## 注意事项

1. 音频文件较大，**不能放在小程序包内**，必须通过 CDN/云存储播放；
2. 新概念英语第二册数据量较大（约 1.7MB），**不能放在小程序主包内**，通过 `wx.request` 从 CDN 下载；
3. 使用 `BackgroundAudioManager` 支持锁屏/切后台继续播放；
4. 当前 `currentTime` 更新频率有限，高亮会有 100~200ms 的轻微延迟；
5. 小程序主包总体积不超过 2MB，注意控制包内 JSON 数据大小。
