// 大声朗读 - 章节播放页
// 支持：逐句播放、选词播放、单词高亮、播放速度、连续播放、句子拆分

const params = new URLSearchParams(window.location.search);
const chapterId = params.get('chapter') || '1';

const state = {
    sentences: [],
    allWords: [],
    currentHighlight: null,
    currentFragmentRow: null,
    activeTimeUpdateHandler: null,
    isContinuous: false,
    currentSentenceIndex: -1,
    playbackRate: 1,
    audioUrl: `../resource/01.The Boy Who Lived.m4a`,
    dataUrl: `data/chapter${chapterId}.json`,
    splitSentenceIndex: -1,
    splitFragments: []
};

const audio = document.getElementById('audio');

async function init() {
    try {
        const res = await fetch(state.dataUrl);
        if (!res.ok) throw new Error(`无法加载章节数据: ${state.dataUrl}`);
        const data = await res.json();
        state.sentences = data.sentences;

        document.getElementById('loading').style.display = 'none';
        render();
        setupSelection();
        setupGlobalPlayback();
        setupControls();
        setupSplitModal();
    } catch (err) {
        document.getElementById('loading').textContent = '加载失败: ' + err.message;
        console.error(err);
    }
}

function render() {
    const content = document.getElementById('content');
    let wordId = 0;

    state.sentences.forEach((sent, idx) => {
        const block = document.createElement('div');
        block.className = 'sentence-block';
        block.dataset.index = idx;

        const textDiv = document.createElement('div');
        textDiv.className = 'sentence-text';

        sent.words.forEach(w => {
            const span = document.createElement('span');
            span.className = 'word';
            span.id = `w-${wordId++}`;
            span.dataset.start = w.start;
            span.dataset.end = w.end;
            span.textContent = w.text;
            span.appendChild(document.createTextNode(' '));
            textDiv.appendChild(span);

            state.allWords.push({
                start: w.start,
                end: w.end,
                element: span
            });
        });

        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'sentence-controls';

        const playBtn = document.createElement('button');
        playBtn.className = 'play-btn';
        playBtn.innerHTML = '▶';
        playBtn.title = '播放本句';
        playBtn.onclick = (e) => {
            e.stopPropagation();
            playSentence(idx);
        };

        const splitBtn = document.createElement('button');
        splitBtn.className = 'split-btn';
        splitBtn.innerHTML = '✂';
        splitBtn.title = '拆分句子';
        splitBtn.onclick = (e) => {
            e.stopPropagation();
            openSplitModal(idx);
        };

        controlsDiv.appendChild(playBtn);
        controlsDiv.appendChild(splitBtn);

        block.appendChild(textDiv);
        block.appendChild(controlsDiv);
        content.appendChild(block);
    });
}

function setupControls() {
    const speedSelect = document.getElementById('speed-select');
    if (speedSelect) {
        speedSelect.value = '1';
        speedSelect.addEventListener('change', (e) => {
            state.playbackRate = parseFloat(e.target.value);
            audio.playbackRate = state.playbackRate;
        });
    }

    const continuousBtn = document.getElementById('continuous-btn');
    if (continuousBtn) {
        continuousBtn.addEventListener('click', () => {
            state.isContinuous = !state.isContinuous;
            continuousBtn.classList.toggle('active', state.isContinuous);
            continuousBtn.setAttribute('aria-pressed', state.isContinuous);
        });
    }
}

// ========== 句子拆分浮层 ==========

function setupSplitModal() {
    const modal = document.getElementById('split-modal');
    const closeBtn = document.getElementById('split-modal-close');
    const backdrop = modal.querySelector('.modal-backdrop');
    const splitByCommaBtn = document.getElementById('split-by-comma');
    const addSelectionBtn = document.getElementById('split-add-selection');

    closeBtn.addEventListener('click', closeSplitModal);
    backdrop.addEventListener('click', closeSplitModal);

    splitByCommaBtn.addEventListener('click', () => {
        if (state.splitSentenceIndex >= 0) {
            splitByCommas(state.splitSentenceIndex);
        }
    });

    addSelectionBtn.addEventListener('click', () => {
        addSelectionFragment();
    });

    // 监听浮层内的文本选择，决定是否启用"添加选中片段"
    modal.addEventListener('mouseup', () => {
        updateAddSelectionButton();
    });
    modal.addEventListener('selectionchange', () => {
        updateAddSelectionButton();
    });
}

function updateAddSelectionButton() {
    const addSelectionBtn = document.getElementById('split-add-selection');
    const sel = window.getSelection();
    const isValid = sel && !sel.isCollapsed && getSelectedWordsInModal().length > 0;
    addSelectionBtn.disabled = !isValid;
}

function openSplitModal(sentenceIndex) {
    state.splitSentenceIndex = sentenceIndex;
    state.splitFragments = [];

    const sent = state.sentences[sentenceIndex];
    const sentenceEl = document.getElementById('split-modal-sentence');
    sentenceEl.innerHTML = '';

    // 在浮层中重新渲染可选择的单词
    sent.words.forEach((w, i) => {
        const span = document.createElement('span');
        span.className = 'word';
        span.dataset.index = i;
        span.dataset.start = w.start;
        span.dataset.end = w.end;
        span.textContent = w.text;
        span.appendChild(document.createTextNode(' '));
        sentenceEl.appendChild(span);
    });

    renderFragments();
    document.getElementById('split-modal').classList.remove('hidden');
    document.getElementById('split-add-selection').disabled = true;
}

function closeSplitModal() {
    cleanupPlayback();
    state.splitSentenceIndex = -1;
    state.splitFragments = [];
    document.getElementById('split-modal').classList.add('hidden');
}

function getSelectedWordsInModal() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return [];

    const range = sel.getRangeAt(0);
    const startWord = range.startContainer.parentElement.closest('#split-modal-sentence .word');
    const endWord = range.endContainer.parentElement.closest('#split-modal-sentence .word');

    if (!startWord || !endWord) return [];

    const startIdx = parseInt(startWord.dataset.index, 10);
    const endIdx = parseInt(endWord.dataset.index, 10);

    if (isNaN(startIdx) || isNaN(endIdx)) return [];

    const sent = state.sentences[state.splitSentenceIndex];
    const words = sent.words;
    const from = Math.min(startIdx, endIdx);
    const to = Math.max(startIdx, endIdx);

    return words.slice(from, to + 1);
}

function splitByCommas(sentenceIndex) {
    const sent = state.sentences[sentenceIndex];
    const words = sent.words;
    const fragments = [];
    let current = [];

    words.forEach(w => {
        current.push(w);
        if (w.text.trim().endsWith(',')) {
            fragments.push(current);
            current = [];
        }
    });

    if (current.length > 0) {
        fragments.push(current);
    }

    state.splitFragments = fragments.map(group => ({
        words: group,
        start: group[0].start,
        end: group[group.length - 1].end
    }));

    renderFragments();
}

function addSelectionFragment() {
    const selectedWords = getSelectedWordsInModal();
    if (selectedWords.length === 0) return;

    state.splitFragments.push({
        words: selectedWords,
        start: selectedWords[0].start,
        end: selectedWords[selectedWords.length - 1].end
    });

    renderFragments();
    window.getSelection().removeAllRanges();
    document.getElementById('split-add-selection').disabled = true;
}

function renderFragments() {
    const container = document.getElementById('split-fragments');
    container.innerHTML = '';

    if (state.splitFragments.length === 0) {
        container.innerHTML = '<p class="fragments-empty">点击上方按钮拆分句子，或选中一段文字后点击"添加选中片段"</p>';
        return;
    }

    state.splitFragments.forEach((frag, idx) => {
        const row = document.createElement('div');
        row.className = 'fragment-row';
        row.dataset.start = frag.start;
        row.dataset.end = frag.end;

        const text = document.createElement('span');
        text.className = 'fragment-text';
        text.appendChild(document.createTextNode(`${idx + 1}. `));

        frag.words.forEach(w => {
            const span = document.createElement('span');
            span.className = 'word';
            span.dataset.start = w.start;
            span.dataset.end = w.end;
            span.textContent = w.text;
            span.appendChild(document.createTextNode(' '));
            text.appendChild(span);
        });

        const playBtn = document.createElement('button');
        playBtn.className = 'fragment-play-btn';
        playBtn.innerHTML = '▶';
        playBtn.title = '播放此片段';
        playBtn.onclick = () => {
            playRange(frag.start, frag.end, null, { highlightSource: false, fragmentWords: frag.words, fragmentRow: row });
        };

        row.appendChild(text);
        row.appendChild(playBtn);
        container.appendChild(row);
    });
}

// ========== 播放逻辑 ==========

function playSentence(index) {
    if (index < 0 || index >= state.sentences.length) return;
    const sent = state.sentences[index];
    state.currentSentenceIndex = index;
    playRange(sent.start, sent.end, () => {
        if (state.isContinuous) {
            playSentence(index + 1);
        }
    });
}

function playRange(start, end, onEnded, options = {}) {
    const { highlightSource = true, fragmentRow = null, fragmentWords = null } = options;
    cleanupPlayback();

    // 首次播放时才设置音频源
    if (!audio.src || audio.src === '') {
        audio.src = state.audioUrl;
    }

    function applyPlaybackRate() {
        audio.playbackRate = state.playbackRate;
    }

    function highlightCurrent(t) {
        if (fragmentWords) {
            highlightFragmentWord(t, fragmentWords, fragmentRow);
        } else if (fragmentRow) {
            if (state.currentFragmentRow && state.currentFragmentRow !== fragmentRow) {
                state.currentFragmentRow.classList.remove('highlight');
            }
            fragmentRow.classList.add('highlight');
            state.currentFragmentRow = fragmentRow;
        } else if (highlightSource) {
            highlightWord(t);
        }
    }

    function highlightFragmentWord(currentTime, words, row) {
        if (state.currentHighlight) {
            state.currentHighlight.classList.remove('highlight');
            state.currentHighlight = null;
        }

        const word = words.find(w => currentTime >= w.start && currentTime < w.end);
        if (!word || !row) return;

        const span = row.querySelector(
            `.word[data-start="${word.start}"][data-end="${word.end}"]`
        );
        if (!span) return;

        span.classList.add('highlight');
        state.currentHighlight = span;

        const rect = span.getBoundingClientRect();
        const modalBody = document.querySelector('.modal-body');
        if (modalBody) {
            const modalRect = modalBody.getBoundingClientRect();
            if (rect.top < modalRect.top + 40 || rect.bottom > modalRect.bottom - 40) {
                span.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }

    function startPlayback() {
        applyPlaybackRate();
        state.activeTimeUpdateHandler = () => {
            const t = audio.currentTime;
            highlightCurrent(t);
            if (t >= end) {
                audio.pause();
                cleanupPlayback();
                if (onEnded) onEnded();
            }
        };
        audio.addEventListener('timeupdate', state.activeTimeUpdateHandler);
        audio.play();
    }

    function doSeek() {
        // 如果已经在目标位置附近，直接播放
        if (Math.abs(audio.currentTime - start) < 0.5) {
            startPlayback();
            return;
        }

        audio.currentTime = start;

        // 轮询确认 seek 到位
        let attempts = 0;
        const timer = setInterval(() => {
            attempts++;
            const current = audio.currentTime;
            const ready = audio.readyState >= 2;

            if ((ready && Math.abs(current - start) < 1.0) || attempts > 20) {
                clearInterval(timer);
                startPlayback();
            }
        }, 50);
    }

    if (audio.readyState >= 1) {
        // 元数据已加载，直接 seek
        doSeek();
    } else {
        // 元数据未加载，先加载
        audio.addEventListener('loadedmetadata', function handler() {
            audio.removeEventListener('loadedmetadata', handler);
            applyPlaybackRate();
            doSeek();
        });
        applyPlaybackRate();
        audio.load();
    }
}

function cleanupPlayback() {
    if (state.activeTimeUpdateHandler) {
        audio.removeEventListener('timeupdate', state.activeTimeUpdateHandler);
        state.activeTimeUpdateHandler = null;
    }
    if (state.currentHighlight) {
        state.currentHighlight.classList.remove('highlight');
        state.currentHighlight = null;
    }
    if (state.currentFragmentRow) {
        state.currentFragmentRow.classList.remove('highlight');
        state.currentFragmentRow = null;
    }
}

function highlightWord(currentTime) {
    if (state.currentHighlight) {
        state.currentHighlight.classList.remove('highlight');
        state.currentHighlight = null;
    }

    // 二分查找当前时间所在的 word
    let left = 0, right = state.allWords.length - 1;
    while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        const w = state.allWords[mid];
        if (currentTime >= w.start && currentTime < w.end) {
            w.element.classList.add('highlight');
            state.currentHighlight = w.element;

            // 仅在需要时滚动
            const rect = w.element.getBoundingClientRect();
            if (rect.top < 80 || rect.bottom > window.innerHeight - 80) {
                w.element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }
        if (currentTime < w.start) {
            right = mid - 1;
        } else {
            left = mid + 1;
        }
    }
}

function setupSelection() {
    const floatDiv = document.getElementById('float-play');
    const floatBtn = document.getElementById('float-btn');
    let selectionRange = null;

    document.addEventListener('mouseup', () => {
        const sel = window.getSelection();
        if (!sel.rangeCount || sel.isCollapsed) {
            floatDiv.classList.add('hidden');
            return;
        }

        const range = sel.getRangeAt(0);
        const startNode = range.startContainer.parentElement.closest('.word');
        const endNode = range.endContainer.parentElement.closest('.word');

        if (!startNode || !endNode) {
            floatDiv.classList.add('hidden');
            return;
        }

        selectionRange = {
            start: parseFloat(startNode.dataset.start),
            end: parseFloat(endNode.dataset.end)
        };

        const rect = range.getBoundingClientRect();
        floatDiv.style.left = Math.max(10, rect.left + rect.width / 2 - 60) + 'px';
        floatDiv.style.top = Math.max(10, rect.top - 50) + 'px';
        floatDiv.classList.remove('hidden');
    });

    floatBtn.onclick = () => {
        if (selectionRange) {
            // 选区播放不走连续播放逻辑
            playRange(selectionRange.start, selectionRange.end);
            floatDiv.classList.add('hidden');
            window.getSelection().removeAllRanges();
        }
    };
}

function setupGlobalPlayback() {
    audio.addEventListener('ended', cleanupPlayback);
    audio.addEventListener('pause', () => {
        if (!audio.ended && state.activeTimeUpdateHandler) {
            cleanupPlayback();
        }
    });
}

init();
