// 地图配置文件 - 安全版本（不包含API密钥）
export const MAP_CONFIG = {
  // 外部地图跳转配置（不需要API密钥）
  EXTERNAL: {
    AMAP_WEB_URL: 'https://uri.amap.com/marker',
    BAIDU_WEB_URL: 'https://api.map.baidu.com/marker',
    GOOGLE_WEB_URL: 'https://www.google.com/maps/search/',
    TENCENT_WEB_URL: 'https://apis.map.qq.com/uri/v1/marker'
  },
  
  // 默认地图设置
  DEFAULT: {
    ZOOM: 13,
    WIDTH: 400,
    HEIGHT: 300,
    MARKER_STYLE: 'mid'
  }
};

// 地图提供商类型
export type MapProvider = 'amap' | 'baidu' | 'tianditu';

// 地图模式类型
export type MapMode = 'static' | 'leaflet' | 'external';