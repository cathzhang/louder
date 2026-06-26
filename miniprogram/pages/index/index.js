const books = require('../../data/books.js');

Page({
  data: {
    books: books
  },

  openBook(e) {
    const { book } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/chapters/chapters?book=${book}`
    });
  }
});
