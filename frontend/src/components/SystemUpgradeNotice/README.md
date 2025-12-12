# 系统升级通知组件
## 功能概述

`SystemUpgradeNotice` 是一个用于显示系统升级通知的 React 组件，它会在用户首次访问网站时自动弹出，展示系统升级的详细信息。

## 主要特性

- 🚀 **首次访问自动显示**：用户首次访问时自动弹出升级通知
- 💾 **状态持久化**：使用 localStorage 记住用户是否已查看过通知
- 🎨 **精美设计**：采用 Ant Design 设计风格，视觉效果现代化
- 📱 **响应式布局**：支持桌面端和移动端完美显示
- ⚡ **动态进度条**：模拟升级进度，增强用户体验
- 🔄 **可重复查看**：用户可随时通过头部按钮查看升级详情

## 文件结构

```
SystemUpgradeNotice/
├── SystemUpgradeNotice.tsx    # 主组件
├── SystemUpgradeNotice.css    # 样式文件
└── README.md                  # 说明文档
```

## 使用方法

### 1. 组件集成

组件已集成在 `Layout` 组件中，会在用户首次访问时自动显示：

```tsx
import SystemUpgradeNotice from '../SystemUpgradeNotice/SystemUpgradeNotice';

// 在 Layout 组件中使用
<SystemUpgradeNotice 
  visible={upgradeNoticeVisible} 
  onClose={handleUpgradeNoticeClose} 
/>
```

### 2. 状态管理

使用 `utils/upgradeNotice.ts` 中的工具函数管理通知状态：

```typescript
import { hasSeenUpgradeNotice, markUpgradeNoticeAsSeen, resetUpgradeNotice } from '../../utils/upgradeNotice';

// 检查是否已查看过
const hasSeen = hasSeenUpgradeNotice();

// 标记为已查看
markUpgradeNoticeAsSeen();

// 重置状态（开发时用）
resetUpgradeNotice();
```

### 3. 开发测试

在开发环境下，可以使用以下命令测试：

```javascript
// 在浏览器控制台中
testUpgradeNotice.checkStatus();     // 检查当前状态
testUpgradeNotice.reset();           // 重置状态，重新触发显示
testUpgradeNotice.markAsSeen();      // 手动标记为已查看
window.resetUpgradeNotice();         // 快速重置
```

## 自定义配置

### 修改升级内容

在 `SystemUpgradeNotice.tsx` 中的 `upgradeFeatures` 数组可以修改升级内容：

```typescript
const upgradeFeatures: UpgradeFeature[] = [
  {
    title: '功能名称',
    description: '功能描述',
    status: 'completed' | 'in-progress' | 'upcoming'
  }
];
```

### 修改版本信息

在 `utils/upgradeNotice.ts` 中修改版本号：

```typescript
const UPGRADE_VERSION = '2.0';  // 修改为新版本号
```

### 修改显示延迟

在 `Layout.tsx` 中修改延迟时间：

```typescript
// 延迟1秒显示
const timer = setTimeout(() => {
  setUpgradeNoticeVisible(true);
}, 1000);
```

## 样式定制

组件样式定义在 `SystemUpgradeNotice.css` 中，主要样式类：

- `.system-upgrade-drawer`：抽屉容器样式
- `.upgrade-notice-content`：内容区域样式
- `.upgrade-notice-btn`：头部按钮样式
- `.upgrade-notice-header`：头部样式

## 技术实现

### 核心技术

- **React Hooks**：使用 `useState`、`useEffect` 管理组件状态
- **Ant Design**：使用 Drawer、Timeline、Progress 等组件
- **LocalStorage**：持久化用户访问状态
- **TypeScript**：类型安全和代码提示

### 交互逻辑

1. 用户首次访问网站
2. 检查 localStorage 中是否已查看过升级通知
3. 如果未查看，延迟1秒后显示通知抽屉
4. 用户关闭通知时，标记为已查看并保存到 localStorage
5. 用户可通过头部火箭图标随时查看升级详情

## 注意事项

1. **浏览器兼容性**：需要支持 localStorage 的现代浏览器
2. **开发环境**：开发模式下提供测试工具，生产环境下自动移除
3. **响应式设计**：在不同屏幕尺寸下自动调整布局
4. **性能优化**：组件懒加载，避免不必要的渲染

## 维护说明

- 每次系统大版本更新时，需要修改 `UPGRADE_VERSION` 版本号
- 更新升级内容和进度信息
- 测试在不同设备和浏览器上的显示效果
- 确保关闭逻辑和状态持久化正常工作
