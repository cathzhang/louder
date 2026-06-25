Page({
  openBook(e) {
    const { book } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/chapters/chapters?book=${book}`
    });
  }
});
