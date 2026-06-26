const books = require('../../data/books.js');

Page({
  data: {
    bookId: '',
    book: null
  },

  onLoad(options) {
    const bookId = options.book || '';
    const book = books.find(b => b.id === bookId) || null;
    this.setData({ bookId, book });
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
