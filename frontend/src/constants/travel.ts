// Shared travel-related option mappings for forms
// Values are English codes stored in backend; labels are Chinese for display

export const TRANSPORTATION_OPTIONS = [
  { value: 'flight', label: '飞机' },
  { value: 'train', label: '火车' },
  { value: 'bus', label: '大巴' },
  { value: 'car', label: '自驾' },
  { value: 'metro', label: '地铁' },
  { value: 'ship', label: '轮船' },
  { value: 'mixed', label: '混合交通' },
  { value: 'other', label: '其他' }
];

export const AGE_GROUP_OPTIONS = [
  { value: 'infant', label: '婴幼儿（0-2岁）' },
  { value: 'child', label: '儿童（3-12岁）' },
  { value: 'teenager', label: '青少年（13-17岁）' },
  { value: 'adult', label: '成人（18-59岁）' },
  { value: 'senior', label: '老年人（60岁以上）' }
];

export const FOOD_PREFERENCES_OPTIONS = [
  { value: 'spicy', label: '辣味' },
  { value: 'sweet', label: '甜味' },
  { value: 'sour', label: '酸味' },
  { value: 'light', label: '清淡' },
  { value: 'heavy', label: '重口味' },
  { value: 'seafood', label: '海鲜' },
  { value: 'meat', label: '肉类' },
  { value: 'vegetarian', label: '素食' },
  { value: 'local', label: '当地特色' },
  { value: 'international', label: '国际美食' }
];

export const DIETARY_RESTRICTIONS_OPTIONS = [
  { value: 'no_pork', label: '不吃猪肉' },
  { value: 'no_beef', label: '不吃牛肉' },
  { value: 'no_seafood', label: '不吃海鲜' },
  { value: 'no_spicy', label: '不吃辣' },
  { value: 'vegetarian', label: '素食主义' },
  { value: 'vegan', label: '严格素食' },
  { value: 'halal', label: '清真食品' },
  { value: 'kosher', label: '犹太洁食' },
  { value: 'gluten_free', label: '无麸质' },
  { value: 'lactose_free', label: '无乳糖' },
  { value: 'nut_allergy', label: '坚果过敏' },
  { value: 'diabetes', label: '糖尿病饮食' }
];

export const STATUS_OPTIONS = [
  { value: 'draft', label: '草稿' },
  { value: 'generating', label: '生成中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
  { value: 'archived', label: '已归档' }
];

// 新增：旅行偏好选项（与创建页一致）
export const PREFERENCES_OPTIONS = [
  { value: 'culture', label: '文化历史' },
  { value: 'nature', label: '自然风光' },
  { value: 'food', label: '美食体验' },
  { value: 'shopping', label: '购物娱乐' },
  { value: 'adventure', label: '冒险刺激' },
  { value: 'relaxation', label: '休闲放松' }
];