// H5 全局配置
// 本地开发时留空，部署到线上后填写你的 CDN / 云托管域名

const CONFIG = {
    // 示例：'https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la'
    // 本地开发建议保持空字符串 ''
    CDN_BASE: 'https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la',

    // 是否根据当前 host 自动判断本地/线上
    // true：localhost/127.0.0.1 时使用相对路径，其他使用 CDN_BASE
    // false：始终使用 CDN_BASE
    AUTO_DETECT_LOCAL: true
};

function getBaseUrl() {
    if (!CONFIG.AUTO_DETECT_LOCAL) {
        return CONFIG.CDN_BASE;
    }
    const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
    return isLocal ? '' : CONFIG.CDN_BASE;
}

window.LOUDER_CONFIG = {
    ...CONFIG,
    getBaseUrl
};
