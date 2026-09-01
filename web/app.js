// 大声朗读 - 章节播放页
// 支持：逐句播放、选词播放、单词高亮、播放速度、连续播放

const params = new URLSearchParams(window.location.search);
const chapterId = params.get('chapter') || '1';
const BASE_URL = (window.LOUDER_CONFIG && window.LOUDER_CONFIG.getBaseUrl)
    ? window.LOUDER_CONFIG.getBaseUrl()
    : '';
const isLocal = !BASE_URL;

const state = {
    sentences: [],
    allWords: [],
    currentHighlight: null,
    activeTimeUpdateHandler: null,
    isContinuous: false,
    currentSentenceIndex: -1,
    playbackRate: 1,
    audioUrl: isLocal
        ? '../resource/01.The Boy Who Lived.m4a'
        : `${BASE_URL}/audio/01.The Boy Who Lived.m4a`,
    dataUrl: isLocal
        ? `data/chapter${chapterId}.json`
        : `${BASE_URL}/web/data/chapter${chapterId}.json`
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

        controlsDiv.appendChild(playBtn);

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

function playRange(start, end, onEnded) {
    cleanupPlayback();

    // 首次播放时才设置音频源
    if (!audio.src || audio.src === '') {
        audio.src = state.audioUrl;
    }

    function applyPlaybackRate() {
        audio.playbackRate = state.playbackRate;
    }

    function startPlayback() {
        applyPlaybackRate();
        state.activeTimeUpdateHandler = () => {
            const t = audio.currentTime;
            highlightWord(t);
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
