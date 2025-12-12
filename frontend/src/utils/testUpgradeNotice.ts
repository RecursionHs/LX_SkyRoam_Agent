// 测试升级通知功能的工具函数
import { hasSeenUpgradeNotice, markUpgradeNoticeAsSeen, resetUpgradeNotice } from './upgradeNotice';
export const testUpgradeNotice = {
  // 检查当前状态
  checkStatus: () => {
    console.log('升级通知状态:', hasSeenUpgradeNotice() ? '已查看' : '未查看');
  },
  
  // 重置状态
  reset: () => {
    resetUpgradeNotice();
    console.log('升级通知状态已重置');
  },
  
  // 标记为已查看
  markAsSeen: () => {
    markUpgradeNoticeAsSeen();
    console.log('升级通知已标记为已查看');
  }
};

// 开发环境下暴露到全局
if (process.env.NODE_ENV === 'development') {
  (window as any).testUpgradeNotice = testUpgradeNotice;
  console.log('升级通知测试工具已添加到 window.testUpgradeNotice');
  console.log('可用方法:');
  console.log('- testUpgradeNotice.checkStatus() // 检查状态');
  console.log('- testUpgradeNotice.reset() // 重置状态');
  console.log('- testUpgradeNotice.markAsSeen() // 标记为已查看');
}

export default testUpgradeNotice;
