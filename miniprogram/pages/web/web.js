Page({
  data: {
    url: ''
  },

  onLoad(options) {
    if (options.url) {
      this.setData({ url: decodeURIComponent(options.url) });
    } else {
      wx.showToast({ title: '页面参数缺失', icon: 'none' });
    }
  },

  onLoadSuccess() {
    console.log('H5 页面加载成功');
  },

  onLoadError(e) {
    console.error('H5 页面加载失败', e);
    wx.showToast({ title: '页面加载失败', icon: 'none' });
  },

  onMessage(e) {
    // H5 页面通过 wx.miniProgram.postMessage 发送的消息
    console.log('收到 H5 消息', e.detail.data);
  }
});
