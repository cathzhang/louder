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
│   └── chapter1.json       # 章节对齐数据（放小程序包内）
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

- 对齐 JSON 数据放在 `miniprogram/data/chapter1.json`，随小程序包一起发布；
- 音频文件通过 `wx.getBackgroundAudioManager()` 从云存储 CDN 播放；
- 目前只有 Chapter 1 数据，后续新增章节时，在 `data/` 下添加 `chapter2.json` 等，并在 `pages/player/player.js` 中修改加载逻辑。

## 音频配置

在 `app.js` 中配置音频基础地址：

```javascript
App({
  globalData: {
    audioBaseUrl: 'https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio'
  }
});
```

完整音频 URL 为：

```
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio/01.The Boy Who Lived.m4a
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
- 句子拆分：✂ 按钮打开浮层，支持按逗号拆分或手动选择片段；
- 片段播放：拆分后的每个片段可单独播放，并高亮片段内单词。

## 小程序后台配置

需要在微信公众平台 → 开发管理 → 开发设置 → 服务器域名中添加：

- **downloadFile 合法域名**：
  ```
  https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la
  ```

> 因为使用原生小程序，不需要配置 request 合法域名和业务域名（JSON 数据在包内）。

## 新增章节的步骤

1. 把新章节的对齐 JSON 放到 `miniprogram/data/chapterN.json`；
2. 在 `pages/chapters/chapters.wxml` 中添加新章节入口；
3. 在 `pages/player/player.js` 的 `onLoad` 中，根据 `chapterId` 加载对应 JSON；
4. 如果有新音频，上传到你的云存储，并确保 `app.js` 中的 `audioBaseUrl` 正确。

## 注意事项

1. 音频文件较大，**不能放在小程序包内**，必须通过 CDN/云存储播放；
2. 使用 `BackgroundAudioManager` 支持锁屏/切后台继续播放；
3. 当前 `currentTime` 更新频率有限，高亮会有 100~200ms 的轻微延迟；
4. 小程序包总体积不超过 2MB，JSON 数据多的时候注意分包。
