// 小程序后台音频管理器封装
const audioManager = wx.getBackgroundAudioManager();

function setAudioInfo({ title, epname, singer, coverImgUrl }) {
  audioManager.title = title || '大声朗读';
  audioManager.epname = epname || '';
  audioManager.singer = singer || '大声朗读';
  if (coverImgUrl) {
    audioManager.coverImgUrl = coverImgUrl;
  }
}

function playFromUrl(url, startTime = 0, playbackRate = 1) {
  audioManager.src = url;
  audioManager.startTime = startTime;
  audioManager.playbackRate = playbackRate;
  audioManager.play();
}

function seekAndPlay(time) {
  audioManager.seek(time);
  audioManager.play();
}

function pause() {
  audioManager.pause();
}

function stop() {
  audioManager.stop();
}

module.exports = {
  audioManager,
  setAudioInfo,
  playFromUrl,
  seekAndPlay,
  pause,
  stop
};
