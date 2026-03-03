document.addEventListener('DOMContentLoaded', () => {
    // 元素引用
    const form = document.getElementById('config-form');
    const saveStatus = document.getElementById('save-status');
    const terminal = document.getElementById('terminal-output');
    const reportBox = document.getElementById('report-output');

    // 操作按钮
    const btnExtract = document.getElementById('btn-extract');
    const btnGenerate = document.getElementById('btn-generate');
    const btnOpenDir = document.getElementById('btn-open-dir');
    const btnBrowse = document.getElementById('btn-browse');
    const timePreset = document.getElementById('preset-time');

    // 初始化加载配置
    fetchConfig();

    // 绑定保存配置
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        saveStatus.textContent = '保存中...';

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                saveStatus.style.color = 'var(--primary-color)';
                saveStatus.textContent = '配置已保存';
                setTimeout(() => saveStatus.textContent = '', 3000);
            }
        } catch (err) {
            saveStatus.style.color = '#ff4d4f';
            saveStatus.textContent = '保存失败: ' + err.message;
        }
    });

    // 提取数据
    btnExtract.addEventListener('click', () => runTask('/api/extract', '开始同步最新微信记录...'));

    // 生成通用报告
    btnGenerate.addEventListener('click', () => {
        const timeRange = timePreset.value;
        runTask(`/api/generate?range=${timeRange}`, `开始执行数据分析报告... [范围:${timeRange}]`);
    });

    // 打开目录
    btnOpenDir.addEventListener('click', async () => {
        try {
            await fetch('/api/open_dir', { method: 'POST' });
        } catch (e) {
            console.error("打开目录失败", e);
        }
    });

    // 唤起原生文件夹选中
    const inputDir = document.getElementById('WECHAT_SOURCE_DIR');
    if (btnBrowse || inputDir) {
        const triggerBrowse = async () => {
            if (btnBrowse) {
                btnBrowse.disabled = true;
                btnBrowse.textContent = '请选中文件夹窗...';
            }
            try {
                const res = await fetch('/api/browse');
                const data = await res.json();
                if (data.path && inputDir) {
                    inputDir.value = data.path;
                }
            } catch (e) {
                console.error("浏览文件夹时出错:", e);
            } finally {
                if (btnBrowse) {
                    btnBrowse.disabled = false;
                    btnBrowse.textContent = '浏览...';
                }
            }
        };

        if (btnBrowse) btnBrowse.addEventListener('click', triggerBrowse);
        if (inputDir) inputDir.addEventListener('click', triggerBrowse);
    }

    // 获取配置
    async function fetchConfig() {
        try {
            const res = await fetch('/api/config');
            const conf = await res.json();
            for (let key in conf) {
                const input = document.getElementById(key);
                if (input) input.value = conf[key] || '';
            }
        } catch (e) {
            console.warn("无法加载初始化配置", e);
        }
    }

    // 执行任务并串联 SSE 终端打印
    async function runTask(endpoint, promptMsg) {
        // 重置状态
        btnExtract.disabled = true;
        btnGenerate.disabled = true;
        reportBox.innerHTML = '<div class="empty-state">分析中，请稍候...</div>';
        terminal.innerHTML = '';

        appendTerminal(`> ${promptMsg}`);

        try {
            const res = await fetch(endpoint, { method: 'POST' });
            if (!res.ok) throw new Error("服务器响应异常");

            // 监听日志流
            startLogStream();

        } catch (err) {
            appendTerminal(`[ERROR] ${err.message}`, true);
            restoreButtons();
        }
    }

    // 终端追加器
    function appendTerminal(text, isError = false) {
        const span = document.createElement('span');
        if (isError) span.style.color = '#ff4d4f';
        span.textContent = text + '\n';
        terminal.appendChild(span);
        terminal.scrollTop = terminal.scrollHeight;
    }

    // EventSource 日志流
    let evtSource = null;
    function startLogStream() {
        if (evtSource) evtSource.close();

        evtSource = new EventSource('/api/stream');

        evtSource.onmessage = (e) => {
            const data = JSON.parse(e.data);

            if (data.type === 'log') {
                appendTerminal(data.content);
            } else if (data.type === 'report_done') {
                renderMarkdown(data.content);
                evtSource.close();
                restoreButtons();
                appendTerminal(`[SYSTEM] 执行完毕。`);
            } else if (data.type === 'error') {
                appendTerminal(`[FAILED] ${data.content}`, true);
                evtSource.close();
                restoreButtons();
            }
        };

        evtSource.onerror = () => {
            evtSource.close();
            restoreButtons();
        };
    }

    // Markdown 渲染
    function renderMarkdown(mdText) {
        if (!mdText) return;
        marked.setOptions({ gfm: true, breaks: true });
        reportBox.innerHTML = marked.parse(mdText);
    }

    function restoreButtons() {
        btnExtract.disabled = false;
        btnGenerate.disabled = false;
    }
});
