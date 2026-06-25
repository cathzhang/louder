Page({
  data: {
    bookId: ''
  },

  onLoad(options) {
    this.setData({ bookId: options.book || '' });
  },

  openChapter(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/player/player?book=${this.data.bookId}&chapter=${id}`
    });
  },

  goBack() {
    wx.navigateBack();
  }
});
