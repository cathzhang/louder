let sentences = [];
let allWords = [];          // 所有 word span 的引用，按时间排序
let audio = document.getElementById('audio');
let currentHighlight = null;
let activeTimeUpdateHandler = null;

const AUDIO_URL = '../resource/01.The Boy Who Lived.m4a';

async function init() {
    try {
        const res = await fetch('data.json');
        const data = await res.json();
        sentences = data.sentences;

        document.getElementById('loading').style.display = 'none';
        render();
        setupSelection();
        setupGlobalPlayback();
        // 音频 src 延迟到首次播放时再设置，避免页面加载慢
    } catch (err) {
        document.getElementById('loading').textContent = '加载失败: ' + err.message;
        console.error(err);
    }
}

function render() {
    const content = document.getElementById('content');
    let wordId = 0;

    sentences.forEach((sent, idx) => {
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

            allWords.push({
                start: w.start,
                end: w.end,
                element: span
            });
        });

        const btn = document.createElement('button');
        btn.className = 'play-btn';
        btn.innerHTML = '▶';
        btn.title = '播放本句';
        btn.onclick = (e) => {
            e.stopPropagation();
            playRange(sent.start, sent.end);
        };

        block.appendChild(textDiv);
        block.appendChild(btn);
        content.appendChild(block);
    });
}

function playRange(start, end) {
    cleanupPlayback();

    // 首次播放时才设置音频源
    if (!audio.src || audio.src === '') {
        audio.src = AUDIO_URL;
    }

    function startPlayback() {
        activeTimeUpdateHandler = () => {
            const t = audio.currentTime;
            highlightWord(t);
            if (t >= end) {
                audio.pause();
                cleanupPlayback();
            }
        };
        audio.addEventListener('timeupdate', activeTimeUpdateHandler);
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
            doSeek();
        });
        audio.load();
    }
}

function cleanupPlayback() {
    if (activeTimeUpdateHandler) {
        audio.removeEventListener('timeupdate', activeTimeUpdateHandler);
        activeTimeUpdateHandler = null;
    }
    if (currentHighlight) {
        currentHighlight.classList.remove('highlight');
        currentHighlight = null;
    }
}

function highlightWord(currentTime) {
    if (currentHighlight) {
        currentHighlight.classList.remove('highlight');
        currentHighlight = null;
    }

    // 二分查找当前时间所在的 word
    let left = 0, right = allWords.length - 1;
    while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        const w = allWords[mid];
        if (currentTime >= w.start && currentTime < w.end) {
            w.element.classList.add('highlight');
            currentHighlight = w.element;

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
            playRange(selectionRange.start, selectionRange.end);
            floatDiv.classList.add('hidden');
            window.getSelection().removeAllRanges();
        }
    };
}

function setupGlobalPlayback() {
    audio.addEventListener('ended', cleanupPlayback);
    audio.addEventListener('pause', () => {
        if (!audio.ended && activeTimeUpdateHandler) {
            cleanupPlayback();
        }
    });
}

init();
