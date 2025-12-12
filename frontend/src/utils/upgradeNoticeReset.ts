import { resetUpgradeNotice } from './upgradeNotice';
// 开发环境下暴露重置功能到 window 对象
if (process.env.NODE_ENV === 'development') {
  (window as any).resetUpgradeNotice = resetUpgradeNotice;
  console.log('升级通知重置功能已添加到 window.resetUpgradeNotice()');
}

export default resetUpgradeNotice;
