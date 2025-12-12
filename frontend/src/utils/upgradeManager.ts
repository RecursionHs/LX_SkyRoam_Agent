// 升级通知管理器
export interface UpgradeConfig {
  version: string;
  enabled: boolean;
  status: 'upcoming' | 'in-progress' | 'completed';
  title: string;
  description: string;
  startTime?: string;
  endTime?: string;
  features: UpgradeFeature[];
  showProgress: boolean;
  progress: number;
}
export interface UpgradeFeature {
  title: string;
  description: string;
  status: 'completed' | 'in-progress' | 'upcoming';
}

export interface UpgradeNoticeState {
  lastSeenVersion: string;
  dismissedVersions: string[];
  preferences: {
    autoShow: boolean;
    showNotifications: boolean;
  };
}

class UpgradeManager {
  private static readonly STORAGE_KEYS = {
    CONFIG: 'lx_upgrade_config',
    STATE: 'lx_upgrade_state',
    TEMP_DISABLE: 'lx_upgrade_temp_disabled'
  };

  private static readonly DEFAULT_CONFIG: UpgradeConfig = {
    version: '2.0',
    enabled: true,
    status: 'completed',
    title: '系统升级完成',
    description: '洛曦云旅Agent已完成重大版本升级',
    features: [
      {
        title: '🚀 AI 智能引擎升级',
        description: '基于深度学习的全新推荐算法，规划准确率提升30%，响应速度提升50%',
        status: 'completed'
      },
      {
        title: '📊 实时数据同步',
        description: '景点信息、价格数据、用户评价等关键信息实时更新，确保信息准确',
        status: 'completed'
      },
      {
        title: '📱 移动端完美适配',
        description: '全新响应式设计，支持手机、平板完美体验，随时随地规划旅行',
        status: 'completed'
      },
      {
        title: '🌍 多语言全球化',
        description: '新增英文、日文、韩文等8种语言界面支持，服务全球用户',
        status: 'upcoming'
      },
      {
        title: '👥 社交互动功能',
        description: '旅行计划分享、评论、点赞、收藏等完整社交功能即将上线',
        status: 'upcoming'
      }
    ],
    showProgress: false,
    progress: 100
  };

  private static readonly DEFAULT_STATE: UpgradeNoticeState = {
    lastSeenVersion: '',
    dismissedVersions: [],
    preferences: {
      autoShow: true,
      showNotifications: true
    }
  };

  // 获取当前升级配置
  static getCurrentConfig(): UpgradeConfig {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEYS.CONFIG);
      return stored ? { ...this.DEFAULT_CONFIG, ...JSON.parse(stored) } : this.DEFAULT_CONFIG;
    } catch (error) {
      console.warn('获取升级配置失败:', error);
      return this.DEFAULT_CONFIG;
    }
  }

  // 更新升级配置
  static updateConfig(config: Partial<UpgradeConfig>): void {
    try {
      const current = this.getCurrentConfig();
      const updated = { ...current, ...config };
      localStorage.setItem(this.STORAGE_KEYS.CONFIG, JSON.stringify(updated));
      this.notifyConfigChange(updated);
    } catch (error) {
      console.warn('更新升级配置失败:', error);
    }
  }

  // 获取用户状态
  static getUserState(): UpgradeNoticeState {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEYS.STATE);
      return stored ? { ...this.DEFAULT_STATE, ...JSON.parse(stored) } : this.DEFAULT_STATE;
    } catch (error) {
      console.warn('获取用户状态失败:', error);
      return this.DEFAULT_STATE;
    }
  }

  // 更新用户状态
  static updateUserState(state: Partial<UpgradeNoticeState>): void {
    try {
      const current = this.getUserState();
      const updated = { ...current, ...state };
      localStorage.setItem(this.STORAGE_KEYS.STATE, JSON.stringify(updated));
    } catch (error) {
      console.warn('更新用户状态失败:', error);
    }
  }

  // 检查是否应该显示通知
  static shouldShowNotice(): boolean {
    const config = this.getCurrentConfig();
    const state = this.getUserState();
    const tempDisabled = localStorage.getItem(this.STORAGE_KEYS.TEMP_DISABLE);

    // 临时禁用
    if (tempDisabled) {
      const disabledTime = parseInt(tempDisabled);
      if (Date.now() - disabledTime < 24 * 60 * 60 * 1000) { // 24小时内
        return false;
      } else {
        localStorage.removeItem(this.STORAGE_KEYS.TEMP_DISABLE);
      }
    }

    // 用户偏好设置
    if (!state.preferences.autoShow || !state.preferences.showNotifications) {
      return false;
    }

    // 升级功能未启用
    if (!config.enabled) {
      return false;
    }

    // 已经看过这个版本
    if (state.lastSeenVersion === config.version || state.dismissedVersions.includes(config.version)) {
      return false;
    }

    return true;
  }

  // 标记通知为已查看
  static markNoticeAsSeen(version?: string): void {
    const config = this.getCurrentConfig();
    const targetVersion = version || config.version;
    
    this.updateUserState({
      lastSeenVersion: targetVersion,
      dismissedVersions: [...this.getUserState().dismissedVersions, targetVersion]
    });
  }

  // 重置特定版本的通知状态
  static resetNoticeForVersion(version: string): void {
    const state = this.getUserState();
    this.updateUserState({
      dismissedVersions: state.dismissedVersions.filter(v => v !== version),
      lastSeenVersion: state.lastSeenVersion === version ? '' : state.lastSeenVersion
    });
  }

  // 临时禁用通知（24小时）
  static tempDisableNotice(): void {
    localStorage.setItem(this.STORAGE_KEYS.TEMP_DISABLE, Date.now().toString());
  }

  // 启动新升级
  static startNewUpgrade(config: Partial<UpgradeConfig>): void {
    const newConfig: UpgradeConfig = {
      ...this.DEFAULT_CONFIG,
      ...config,
      status: 'in-progress',
      enabled: true,
      showProgress: true,
      progress: 0
    };
    
    // 清除之前的查看状态
    this.updateUserState({
      dismissedVersions: this.getUserState().dismissedVersions.filter(v => v !== newConfig.version)
    });
    
    this.updateConfig(newConfig);
  }

  // 完成升级
  static completeUpgrade(): void {
    const config = this.getCurrentConfig();
    this.updateConfig({
      status: 'completed',
      progress: 100,
      showProgress: false,
      endTime: new Date().toISOString()
    });
  }

  // 关闭升级通知（不再显示）
  static disableUpgrade(): void {
    this.updateConfig({ enabled: false });
  }

  // 启用升级通知
  static enableUpgrade(): void {
    this.updateConfig({ enabled: true });
  }

  // 更新升级进度
  static updateProgress(progress: number): void {
    const config = this.getCurrentConfig();
    this.updateConfig({ 
      progress: Math.min(100, Math.max(0, progress)) 
    });
  }

  // 配置变化通知
  private static notifyConfigChange(config: UpgradeConfig): void {
    // 触发自定义事件，通知其他组件
    window.dispatchEvent(new CustomEvent('upgradeConfigChanged', { 
      detail: config 
    }));
  }

  // 监听配置变化
  static onConfigChange(callback: (config: UpgradeConfig) => void): () => void {
    const handler = (event: CustomEvent) => callback(event.detail);
    window.addEventListener('upgradeConfigChanged', handler as EventListener);
    
    return () => {
      window.removeEventListener('upgradeConfigChanged', handler as EventListener);
    };
  }

  // 获取管理员控制接口
  static getAdminControls() {
    return {
      startUpgrade: (config: Partial<UpgradeConfig>) => this.startNewUpgrade(config),
      completeUpgrade: () => this.completeUpgrade(),
      disableUpgrade: () => this.disableUpgrade(),
      enableUpgrade: () => this.enableUpgrade(),
      updateProgress: (progress: number) => this.updateProgress(progress),
      updateConfig: (config: Partial<UpgradeConfig>) => this.updateConfig(config),
      resetVersion: (version: string) => this.resetNoticeForVersion(version),
      tempDisable: () => this.tempDisableNotice(),
      getCurrentConfig: () => this.getCurrentConfig(),
      getUserState: () => this.getUserState()
    };
  }
}

// 开发环境下暴露到全局
if (process.env.NODE_ENV === 'development') {
  (window as any).UpgradeManager = UpgradeManager.getAdminControls();
  console.log('升级管理器已暴露到全局: window.UpgradeManager');
}

export default UpgradeManager;
