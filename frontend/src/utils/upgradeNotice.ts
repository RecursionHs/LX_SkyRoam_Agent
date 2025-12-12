const UPGRADE_NOTICE_KEY = 'lx_skyroam_upgrade_notice_shown';
const UPGRADE_VERSION = '2.0';
export const hasSeenUpgradeNotice = (): boolean => {
  try {
    const stored = localStorage.getItem(UPGRADE_NOTICE_KEY);
    return stored === UPGRADE_VERSION;
  } catch (error) {
    console.warn('无法访问 localStorage:', error);
    return false;
  }
};

export const markUpgradeNoticeAsSeen = (): void => {
  try {
    localStorage.setItem(UPGRADE_NOTICE_KEY, UPGRADE_VERSION);
  } catch (error) {
    console.warn('无法写入 localStorage:', error);
  }
};

export const resetUpgradeNotice = (): void => {
  try {
    localStorage.removeItem(UPGRADE_NOTICE_KEY);
  } catch (error) {
    console.warn('无法清除 localStorage:', error);
  }
};
