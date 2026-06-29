const books = require('../../data/books.js');
const share = require('../../utils/share.js');

Page({
  data: {
    books: books
  },

  openBook(e) {
    const { book } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/chapters/chapters?book=${book}`
    });
  },

  onShareAppMessage() {
    return share.indexShare();
  },

  onShareTimeline() {
    return share.indexTimeline();
  }
});
