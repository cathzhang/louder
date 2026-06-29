const books = require('../data/books.js');

function getBook(bookId) {
  return books.find(b => b.id === bookId) || null;
}

function getChapter(bookId, chapterId) {
  const book = getBook(bookId);
  if (!book) return null;
  return book.chapters.find(c => c.id === chapterId) || null;
}

function makeShareTitle(bookId, chapterId) {
  const book = getBook(bookId);
  const chapter = chapterId ? getChapter(bookId, chapterId) : null;

  if (book && chapter) {
    return `${book.title} · ${chapter.title} - 大声朗读`;
  }
  if (book) {
    return `${book.title} - 大声朗读`;
  }
  return '大声朗读 - 英语听力口语跟读';
}

function makeShareQuery(params) {
  return Object.keys(params)
    .filter(k => params[k] !== undefined && params[k] !== null && params[k] !== '')
    .map(k => `${k}=${encodeURIComponent(params[k])}`)
    .join('&');
}

function makeSharePath(page, params) {
  const query = makeShareQuery(params);
  return query ? `/pages/${page}/${page}?${query}` : `/pages/${page}/${page}`;
}

// ========== 转发给朋友（onShareAppMessage）使用 path ==========

function indexShare() {
  console.log('indexShare')
  return {
    title: '大声朗读 - 英语听力口语跟读',
    path: '/pages/index/index'
  };
}

function chaptersShare(bookId) {
  return {
    title: makeShareTitle(bookId),
    path: makeSharePath('chapters', { book: bookId })
  };
}

function playerShare(bookId, chapterId) {
  return {
    title: makeShareTitle(bookId, chapterId),
    path: makeSharePath('player', { book: bookId, chapter: chapterId })
  };
}

// ========== 分享到朋友圈（onShareTimeline）使用 query ==========

function indexTimeline() {
  console.log('indexTimeline')
  return {
    title: '大声朗读 - 英语听力口语跟读',
    query: ''
  };
}

function chaptersTimeline(bookId) {
  return {
    title: makeShareTitle(bookId),
    query: makeShareQuery({ book: bookId })
  };
}

function playerTimeline(bookId, chapterId) {
  return {
    title: makeShareTitle(bookId, chapterId),
    query: makeShareQuery({ book: bookId, chapter: chapterId })
  };
}

module.exports = {
  makeShareTitle,
  makeSharePath,
  indexShare,
  chaptersShare,
  playerShare,
  indexTimeline,
  chaptersTimeline,
  playerTimeline
};
