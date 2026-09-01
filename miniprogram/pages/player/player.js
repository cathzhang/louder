const app = getApp();
const books = require('../../data/books.js');
const share = require('../../utils/share.js');

const audioManager = wx.getBackgroundAudioManager();

Page({
  data: {
    bookId: '',
    chapterId: '1',
    book: null,
    currentChapter: null,
    sentences: [],
    allWords: [],
    loading: true,
    loadError: '',
    audioFile: '',
    speedOptions: ['0.5x', '0.75x', '1x', '1.25x', '1.5x', '2x'],
    speedIndex: 2,
    playbackRate: 1,
    isContinuous: false,
    selectMode: false,
    selectionStart: null,
    selectionEnd: null,
    currentWordIndex: -1,
    scrollIntoView: '',
    resumeSentenceIndex: -1
  },

  timer: null,
  pendingSeekStart: null,
  lastReadSentenceIndex: -1,
  lastReadTime: 0,

  onLoad(options) {
    const bookId = options.book || '';
    const chapterId = options.chapter || '1';
    const book = books.find(b => b.id === bookId) || null;
    const currentChapter = book
      ? book.chapters.find(c => c.id === chapterId) || book.chapters[0]
      : null;

    this.setData({ bookId, chapterId, book, currentChapter });
    this.loadChapterData(bookId, chapterId);
    this.setupAudioListeners();
  },

  onUnload() {
    this.saveLastRead();
    this.stopTimer();
    audioManager.stop();
  },

  onHide() {
    this.saveLastRead();
  },

  getLastReadKey() {
    return `lastRead_${this.data.bookId}_${this.data.chapterId}`;
  },

  saveLastRead() {
    if (this.lastReadSentenceIndex < 0) return;
    const key = this.getLastReadKey();
    wx.setStorageSync(key, {
      sentenceIndex: this.lastReadSentenceIndex,
      time: this.lastReadTime || 0
    });
  },

  loadLastRead() {
    try {
      const key = this.getLastReadKey();
      const saved = wx.getStorageSync(key);
      if (
        saved &&
        typeof saved.sentenceIndex === 'number' &&
        saved.sentenceIndex >= 0 &&
        saved.sentenceIndex < this.data.sentences.length
      ) {
        this.setData({
          scrollIntoView: `sentence-${saved.sentenceIndex}`,
          resumeSentenceIndex: saved.sentenceIndex
        });
        wx.showToast({ title: '已回到上次阅读位置', icon: 'none' });
      }
    } catch (e) {
      console.error('读取阅读位置失败', e);
    }
  },

  loadChapterData(bookId, chapterId) {
    const book = this.data.book;
    if (!book) {
      this.setData({ loading: false, loadError: '未找到书籍' });
      return;
    }

    if (book.dataType === 'local') {
      // 本地数据：按 chapterId 加载对应 JS module
      const data = chapterId === '2'
        ? require('../../data/chapter2-data.js')
        : require('../../data/chapter1-data.js');
      this.initSentences(data);
    } else {
      // 远程数据：从 CDN 下载 JSON
      const url = `${app.globalData.dataBaseUrl}/${bookId}/lesson${chapterId.padStart(2, '0')}.json`;
      wx.showLoading({ title: '加载中' });
      wx.request({
        url,
        method: 'GET',
        success: (res) => {
          wx.hideLoading();
          if (res.statusCode === 200 && res.data) {
            this.initSentences(res.data);
          } else {
            this.setData({ loading: false, loadError: '数据加载失败' });
          }
        },
        fail: (err) => {
          wx.hideLoading();
          console.error('下载数据失败', err);
          this.setData({ loading: false, loadError: '网络错误' });
        }
      });
    }
  },

  initSentences(data) {
    const audioFile = data.meta && data.meta.audio_file ? data.meta.audio_file : '';
    const sentences = (data.sentences || []).map(s => ({
      ...s,
      words: s.words.map(w => ({ ...w, highlight: false, selected: false }))
    }));

    const allWords = [];
    sentences.forEach((sent, sIdx) => {
      sent.words.forEach((w, wIdx) => {
        allWords.push({ ...w, sentenceIndex: sIdx, wordIndex: wIdx });
      });
    });

    this.setData({
      loading: false,
      audioFile,
      sentences,
      allWords
    }, () => {
      this.loadLastRead();
    });
  },

  setupAudioListeners() {
    audioManager.onPlay(() => {
      this.applyPlaybackRate();
      if (this.pendingSeekStart !== null) {
        const start = this.pendingSeekStart;
        this.pendingSeekStart = null;
        audioManager.seek(start);
      }
    });

    audioManager.onEnded(() => {
      this.stopTimer();
      this.clearHighlight();
    });

    audioManager.onPause(() => {
      this.stopTimer();
      this.clearHighlight();
    });

    audioManager.onStop(() => {
      this.stopTimer();
      this.clearHighlight();
    });

    audioManager.onWaiting(() => {
      // 缓冲中
    });

    audioManager.onError((err) => {
      console.error('音频播放错误', err);
      wx.showToast({ title: '音频播放失败', icon: 'none' });
    });
  },

  applyPlaybackRate() {
    const rate = this.data.playbackRate;
    if (rate && audioManager.playbackRate !== rate) {
      audioManager.playbackRate = rate;
    }
  },

  getAudioUrl() {
    const book = this.data.book;
    const fileName = this.data.audioFile;
    if (!book || !fileName) return '';

    const encodedFileName = encodeURIComponent(fileName);
    const path = book.audioPath ? `${book.audioPath}/${encodedFileName}` : encodedFileName;
    return `${app.globalData.audioBaseUrl}/${path}`;
  },

  // ========== 播放控制 ==========

  playSentence(e) {
    const index = e.currentTarget.dataset.index;
    this.playRangeBySentence(index);
  },

  playRangeBySentence(index) {
    if (index < 0 || index >= this.data.sentences.length) return;
    this.clearSelection();
    const sent = this.data.sentences[index];
    this.lastReadSentenceIndex = index;
    this.lastReadTime = sent.start;
    this.playRange(sent.start, sent.end, () => {
      if (this.data.isContinuous) {
        this.playRangeBySentence(index + 1);
      }
    });
  },

  playRange(start, end, onEnded) {
    this.stopTimer();
    this.clearHighlight();

    const book = this.data.book;
    const chapter = book && book.chapters.find(c => c.id === this.data.chapterId);

    audioManager.title = chapter ? chapter.title : '朗读';
    audioManager.epname = book ? book.title : '大声朗读';
    audioManager.singer = '大声朗读';
    audioManager.src = this.getAudioUrl();

    this.pendingSeekStart = start;
    this.lastReadTime = start;
    audioManager.play();

    this.startHighlightTimer(start, end, onEnded);
  },

  startHighlightTimer(start, end, onEnded) {
    this.stopTimer();

    this.timer = setInterval(() => {
      const currentTime = audioManager.currentTime;

      if (currentTime >= end) {
        audioManager.pause();
        this.stopTimer();
        this.clearHighlight();
        if (onEnded) onEnded();
        return;
      }

      this.highlightWord(currentTime);
    }, 100);
  },

  stopTimer() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  },

  // ========== 高亮 ==========

  highlightWord(currentTime) {
    const word = this.data.allWords.find(w => currentTime >= w.start && currentTime < w.end);
    if (!word) return;

    const currentIndex = `${word.sentenceIndex}-${word.wordIndex}`;
    if (this.data.currentWordIndex === currentIndex) return;

    this.lastReadSentenceIndex = word.sentenceIndex;
    this.lastReadTime = currentTime;

    this.clearHighlight();

    const key = `sentences[${word.sentenceIndex}].words[${word.wordIndex}].highlight`;
    this.setData({
      [key]: true,
      currentWordIndex: currentIndex
    });
  },

  clearHighlight() {
    const { sentences, currentWordIndex } = this.data;
    if (currentWordIndex === -1) return;

    const updates = { currentWordIndex: -1 };

    sentences.forEach((sent, sIdx) => {
      sent.words.forEach((w, wIdx) => {
        if (w.highlight) {
          updates[`sentences[${sIdx}].words[${wIdx}].highlight`] = false;
        }
      });
    });

    this.setData(updates);
  },

  // ========== 速度 / 连续播放 ==========

  onSpeedChange(e) {
    const index = parseInt(e.detail.value, 10);
    const rate = parseFloat(this.data.speedOptions[index]);
    audioManager.playbackRate = rate;
    this.setData({ speedIndex: index, playbackRate: rate });
  },

  toggleContinuous() {
    this.setData({ isContinuous: !this.data.isContinuous });
  },

  onShareAppMessage() {
    return share.playerShare(this.data.bookId, this.data.chapterId);
  },

  onShareTimeline() {
    return share.playerTimeline(this.data.bookId, this.data.chapterId);
  },

  onWordTap(e) {
    const { sidx, widx } = e.currentTarget.dataset;

    if (this.data.selectMode) {
      this.handleSelectionTap(sidx, widx);
      return;
    }

    this.clearSelection();
    const word = this.data.sentences[sidx].words[widx];
    this.lastReadSentenceIndex = sidx;
    this.lastReadTime = word.start;
    this.playRange(word.start, word.end);
  },

  // ========== 选段播放 ==========

  toggleSelectMode() {
    const newMode = !this.data.selectMode;
    if (!newMode) {
      this.clearSelection();
    }
    this.setData({ selectMode: newMode });
  },

  clearSelection() {
    const updates = {
      selectionStart: null,
      selectionEnd: null
    };
    this.data.sentences.forEach((sent, sIdx) => {
      sent.words.forEach((w, wIdx) => {
        if (w.selected) {
          updates[`sentences[${sIdx}].words[${wIdx}].selected`] = false;
        }
      });
    });
    this.setData(updates);
  },

  updateSelection(start, end = null) {
    const updates = {
      selectionStart: start,
      selectionEnd: end
    };

    // 先清除所有选中态
    this.data.sentences.forEach((sent, sIdx) => {
      sent.words.forEach((w, wIdx) => {
        if (w.selected) {
          updates[`sentences[${sIdx}].words[${wIdx}].selected`] = false;
        }
      });
    });

    // 设置新的起点
    updates[`sentences[${start.sidx}].words[${start.widx}].selected`] = true;

    // 如果终点已选，设置区间
    if (end) {
      const sidx = start.sidx;
      const from = Math.min(start.widx, end.widx);
      const to = Math.max(start.widx, end.widx);
      for (let i = from; i <= to; i++) {
        updates[`sentences[${sidx}].words[${i}].selected`] = true;
      }
    }

    this.setData(updates);
  },

  handleSelectionTap(sidx, widx) {
    const start = this.data.selectionStart;

    if (!start || this.data.selectionEnd) {
      // 没有起点，或已有完整选择：重置并设置新起点
      this.updateSelection({ sidx, widx });
      return;
    }

    if (start.sidx !== sidx) {
      // 只能选同一句
      wx.showToast({ title: '请选择同一句中的单词', icon: 'none' });
      this.updateSelection({ sidx, widx });
      return;
    }

    this.updateSelection(start, { sidx, widx });
    this.playSelection();
  },

  playSelection() {
    const start = this.data.selectionStart;
    const end = this.data.selectionEnd;
    if (!start || !end) return;

    const sentence = this.data.sentences[start.sidx];
    const from = Math.min(start.widx, end.widx);
    const to = Math.max(start.widx, end.widx);
    const startWord = sentence.words[from];
    const endWord = sentence.words[to];

    this.lastReadSentenceIndex = start.sidx;
    this.lastReadTime = startWord.start;
    this.playRange(startWord.start, endWord.end);
  }
});
