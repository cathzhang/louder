const app = getApp();

const audioManager = wx.getBackgroundAudioManager();

Page({
  data: {
    bookId: '',
    chapterId: '1',
    sentences: [],
    allWords: [],

    speedOptions: ['0.5x', '0.75x', '1x', '1.25x', '1.5x', '2x'],
    speedIndex: 2,
    playbackRate: 1,
    isContinuous: false,

    currentWordIndex: -1,
    scrollIntoView: '',

    showSplitModal: false,
    splitSentenceIndex: -1,
    splitWords: [],
    splitStart: -1,
    splitEnd: -1,
    splitFragments: []
  },

  timer: null,

  onLoad(options) {
    const bookId = options.book || '';
    const chapterId = options.chapter || '1';

    // 加载本地 JSON 数据（小程序 require 不支持动态路径，目前固定 chapter1）
    const data = require('../../data/chapter1.json');
    const sentences = data.sentences.map(s => ({
      ...s,
      words: s.words.map(w => ({ ...w, highlight: false }))
    }));

    const allWords = [];
    sentences.forEach((sent, sIdx) => {
      sent.words.forEach((w, wIdx) => {
        allWords.push({ ...w, sentenceIndex: sIdx, wordIndex: wIdx });
      });
    });

    this.setData({
      bookId,
      chapterId,
      sentences,
      allWords
    });

    this.setupAudioListeners();
  },

  onUnload() {
    this.stopTimer();
    audioManager.stop();
  },

  setupAudioListeners() {
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

  // ========== 播放控制 ==========

  playSentence(e) {
    const index = e.currentTarget.dataset.index;
    this.playRangeBySentence(index);
  },

  playRangeBySentence(index) {
    if (index < 0 || index >= this.data.sentences.length) return;
    const sent = this.data.sentences[index];
    this.playRange(sent.start, sent.end, () => {
      if (this.data.isContinuous) {
        this.playRangeBySentence(index + 1);
      }
    });
  },

  playFragment(e) {
    const index = e.currentTarget.dataset.index;
    const fragment = this.data.splitFragments[index];
    if (!fragment) return;
    this.playRange(fragment.start, fragment.end, null, fragment.words);
  },

  playRange(start, end, onEnded, fragmentWords) {
    this.stopTimer();
    this.clearHighlight();

    audioManager.title = 'Chapter 1';
    audioManager.epname = 'Harry Potter';
    audioManager.singer = '大声朗读';
    audioManager.src = `${app.globalData.audioBaseUrl}/01.The Boy Who Lived.m4a`;

    // 设置播放速度
    audioManager.playbackRate = this.data.playbackRate;

    // seek 并开始播放
    audioManager.seek(start);
    audioManager.play();

    this.startHighlightTimer(start, end, onEnded, fragmentWords);
  },

  startHighlightTimer(start, end, onEnded, fragmentWords) {
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

      this.highlightWord(currentTime, fragmentWords);
    }, 100);
  },

  stopTimer() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  },

  // ========== 高亮 ==========

  highlightWord(currentTime, fragmentWords) {
    const words = fragmentWords || this.data.allWords;
    const word = words.find(w => currentTime >= w.start && currentTime < w.end);

    if (!word) return;

    const currentIndex = fragmentWords
      ? `frag-${word.start}-${word.end}`
      : `${word.sentenceIndex}-${word.wordIndex}`;

    if (this.data.currentWordIndex === currentIndex) return;

    this.clearHighlight();

    if (fragmentWords) {
      // 高亮浮层片段中的单词
      const fIndex = fragmentWords.indexOf(word);
      const key = `splitFragments[${this.data.splitFragments.findIndex(f => f.words === fragmentWords)}].words[${fIndex}].highlight`;
      this.setData({ [key]: true, currentWordIndex: currentIndex });
    } else {
      // 高亮原文中的单词
      const key = `sentences[${word.sentenceIndex}].words[${word.wordIndex}].highlight`;
      this.setData({
        [key]: true,
        currentWordIndex: currentIndex,
        scrollIntoView: `sentence-${word.sentenceIndex}`
      });
    }
  },

  clearHighlight() {
    const { sentences, splitFragments, currentWordIndex } = this.data;
    if (currentWordIndex === -1) return;

    const updates = { currentWordIndex: -1, scrollIntoView: '' };

    sentences.forEach((sent, sIdx) => {
      sent.words.forEach((w, wIdx) => {
        if (w.highlight) {
          updates[`sentences[${sIdx}].words[${wIdx}].highlight`] = false;
        }
      });
    });

    splitFragments.forEach((frag, fIdx) => {
      frag.words.forEach((w, wIdx) => {
        if (w.highlight) {
          updates[`splitFragments[${fIdx}].words[${wIdx}].highlight`] = false;
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

  goBack() {
    wx.navigateBack();
  },

  onWordTap(e) {
    const { sidx, widx } = e.currentTarget.dataset;
    const word = this.data.sentences[sidx].words[widx];
    // 点击单词播放该单词
    this.playRange(word.start, word.end);
  },

  // ========== 句子拆分 ==========

  openSplitModal(e) {
    const index = e.currentTarget.dataset.index;
    const sent = this.data.sentences[index];
    const splitWords = sent.words.map((w, i) => ({
      ...w,
      index: i,
      selected: false
    }));

    this.setData({
      showSplitModal: true,
      splitSentenceIndex: index,
      splitWords,
      splitStart: -1,
      splitEnd: -1,
      splitFragments: []
    });
  },

  closeSplitModal() {
    this.stopTimer();
    this.clearHighlight();
    this.setData({
      showSplitModal: false,
      splitSentenceIndex: -1,
      splitWords: [],
      splitStart: -1,
      splitEnd: -1,
      splitFragments: []
    });
  },

  selectSplitWord(e) {
    const index = e.currentTarget.dataset.index;
    const { splitStart, splitEnd, splitWords } = this.data;

    let newStart = splitStart;
    let newEnd = splitEnd;

    if (splitStart === -1 || (splitStart !== -1 && splitEnd !== -1)) {
      // 重新选择起点
      newStart = index;
      newEnd = -1;
    } else if (index < splitStart) {
      newStart = index;
    } else {
      newEnd = index;
    }

    // 更新选中状态
    const newSplitWords = splitWords.map((w, i) => ({
      ...w,
      selected: (i >= newStart && newEnd !== -1 ? i <= newEnd : i === newStart)
    }));

    this.setData({
      splitWords: newSplitWords,
      splitStart: newStart,
      splitEnd: newEnd
    });
  },

  splitByComma() {
    const { splitSentenceIndex, sentences } = this.data;
    const words = sentences[splitSentenceIndex].words;
    const fragments = [];
    let current = [];

    words.forEach(w => {
      current.push(w);
      if (w.text.trim().endsWith(',')) {
        fragments.push([...current]);
        current = [];
      }
    });

    if (current.length > 0) {
      fragments.push([...current]);
    }

    this.setFragments(fragments);
  },

  addSelectionFragment() {
    const { splitStart, splitEnd, splitSentenceIndex, sentences } = this.data;
    if (splitStart === -1 || splitEnd === -1) return;

    const words = sentences[splitSentenceIndex].words;
    const from = Math.min(splitStart, splitEnd);
    const to = Math.max(splitStart, splitEnd);
    const selected = words.slice(from, to + 1);

    const fragments = [...this.getFragmentWordArrays(), selected];
    this.setFragments(fragments);

    // 重置选择
    this.setData({
      splitStart: -1,
      splitEnd: -1,
      splitWords: this.data.splitWords.map(w => ({ ...w, selected: false }))
    });
  },

  getFragmentWordArrays() {
    return this.data.splitFragments.map(f => f.words);
  },

  setFragments(wordArrays) {
    const fragments = wordArrays.map(group => ({
      words: group.map((w, i) => ({
        ...w,
        fragmentWordIndex: i,
        highlight: false
      })),
      text: group.map(w => w.text).join(' '),
      start: group[0].start,
      end: group[group.length - 1].end
    }));

    this.setData({ splitFragments: fragments });
  }
});
