# 新概念英语第二册 - CDN 数据

本目录包含《新概念英语第二册》96 课的对齐 JSON 数据，需要上传到腾讯云存储 CDN 后，小程序才能正常播放。

## 文件说明

- `lesson01.json` ~ `lesson96.json`：每课的对齐数据（句子/短语 + 单词时间戳）
- `manifest.json`：上传清单，包含每课对应的 JSON 和音频文件名

## 上传目标

### 1. JSON 数据

上传到：

```
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/data/nce2/
```

即小程序 `app.js` 中配置的 `dataBaseUrl + '/nce2/'`。

需要上传的文件：

```
lesson01.json
lesson02.json
...
lesson96.json
```

### 2. 音频文件

上传到：

```
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio/nce2/
```

即小程序 `app.js` 中配置的 `audioBaseUrl + '/nce2/'`。

需要上传的文件为 `resource/新概念英语（第2册）美音（MP3+LRC）/` 下的 96 个 MP3：

```
01－A Private Conversation.mp3
02－Breakfast or Lunch.mp3
...
96－The Dead Return.mp3
```

文件名必须与 `manifest.json` 中的 `audio_file` 完全一致。

## 上传方式

### 方式一：腾讯云 COS 控制台（推荐）

1. 登录 [腾讯云对象存储控制台](https://console.cloud.tencent.com/cos)；
2. 进入 `prod-d5g5fun3a019d78b1-1447117358` 存储桶；
3. 分别进入 `data/nce2/` 和 `audio/nce2/` 目录（不存在则新建）；
4. 上传对应文件。

### 方式二：腾讯云云开发 CLI

如果已安装 `@cloudbase/cli`，可以使用：

```bash
# 上传 JSON
tcb storage upload ./cdn/nce2/lesson*.json data/nce2/

# 上传音频
tcb storage upload "./resource/新概念英语（第2册）美音（MP3+LRC）/*.mp3" audio/nce2/
```

> 注意：具体命令取决于你的云开发环境配置和 CLI 版本。

### 方式三：腾讯云 COS SDK

可以编写 Python 脚本，使用 `cos-python-sdk-v5` 上传：

```bash
pip install cos-python-sdk-v5
```

然后参考腾讯云 COS 文档编写上传脚本，需要准备：
- SecretId
- SecretKey
- Region
- Bucket

## 验证上传

上传完成后，可以通过浏览器访问以下 URL 验证：

```
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/data/nce2/lesson01.json
https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio/nce2/01－A%20Private%20Conversation.mp3
```

如果返回文件内容或触发下载，说明上传成功。

## 重新生成数据

如果 PDF 或 LRC 有更新，可以重新运行：

```bash
python3 scripts/process_nce2.py
```

脚本会重新生成 `cdn/nce2/` 下的所有 JSON 文件和 `manifest.json`。
