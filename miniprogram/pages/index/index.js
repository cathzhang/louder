const app = getApp();

Page({
  data: {
    h5BaseUrl: ''
  },

  onLoad() {
    this.setData({
      h5BaseUrl: app.globalData.h5BaseUrl
    });
  },

  openBook(e) {
    const { book, chapter } = e.currentTarget.dataset;
    const h5Url = `${this.data.h5BaseUrl}/chapter.html?chapter=${chapter}`;

    wx.navigateTo({
      url: `/pages/web/web?url=${encodeURIComponent(h5Url)}`
    });
  }
});
