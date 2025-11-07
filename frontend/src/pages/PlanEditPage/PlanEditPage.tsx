import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Button, DatePicker, Select, Space, message, Typography, Spin, InputNumber, Divider } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';
import { TRANSPORTATION_OPTIONS, AGE_GROUP_OPTIONS, FOOD_PREFERENCES_OPTIONS, DIETARY_RESTRICTIONS_OPTIONS, STATUS_OPTIONS, PREFERENCES_OPTIONS } from '../../constants/travel';

const { Title } = Typography;
const { RangePicker } = DatePicker;

interface PlanDetail {
  id: number;
  title: string;
  description?: string;
  destination: string;
  start_date?: string;
  end_date?: string;
  duration_days?: number;
  status: string;
  // 新增可编辑字段
  departure?: string;
  budget?: number;
  transportation?: string;
  preferences?: Record<string, any>;
  requirements?: Record<string, any>;
}

const normalizeTransportation = (v?: string) => {
  if (!v) return v;
  const zhMap: Record<string, string> = {
    '飞机': 'flight',
    '高铁': 'train',
    '火车': 'train',
    '大巴': 'bus',
    '巴士': 'bus',
    '自驾': 'car',
    '地铁': 'metro',
    '轮船': 'ship',
    '混合交通': 'mixed',
    '其他': 'other',
  };
  const en = v.trim().toLowerCase();
  const enSet: Record<string, string> = {
    flight: 'flight',
    train: 'train',
    bus: 'bus',
    car: 'car',
    metro: 'metro',
    ship: 'ship',
    mixed: 'mixed',
    other: 'other',
  };
  if (enSet[en]) return enSet[en];
  return zhMap[v] || zhMap[en] || v;
};

const PlanEditPage: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const planId = Number(id);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [plan, setPlan] = useState<PlanDetail | null>(null);

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true);
      try {
        if (!planId) throw new Error('缺少计划ID');
        const resp = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)));
        if (!resp.ok) throw new Error(`获取计划详情失败 (${resp.status})`);
        const data = await resp.json();
        setPlan(data);
        const prefs = data.preferences || {};
        const normalizeArray = (value: any) => (Array.isArray(value) ? value : []);
        form.setFieldsValue({
          title: data.title,
          description: data.description,
          destination: data.destination,
          dateRange: data.start_date && data.end_date ? [dayjs(data.start_date), dayjs(data.end_date)] : undefined,
          status: data.status,
          // 新增：扩展字段回填
          departure: data.departure,
          budget: data.budget,
          transportation: normalizeTransportation(data.transportation),
          travelers: typeof prefs.travelers === 'number'
            ? prefs.travelers
            : (typeof prefs.travelers === 'string' ? Number(prefs.travelers) || undefined : undefined),
          ageGroups: normalizeArray(prefs.ageGroups),
          foodPreferences: normalizeArray(prefs.foodPreferences),
          dietaryRestrictions: normalizeArray(prefs.dietaryRestrictions),
          travelPreferences: normalizeArray(prefs.interests),
          specialRequirements: data.requirements?.special_requirements || data.requirements?.specialRequirements || '',
        });
      } catch (e) {
        console.error('加载计划详情失败:', e);
        message.error('无法加载计划详情');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const body: any = {};
      if (typeof values.title === 'string') body.title = values.title.trim();
      if (typeof values.description === 'string') body.description = values.description.trim();
      if (typeof values.destination === 'string') body.destination = values.destination.trim();
      if (Array.isArray(values.dateRange) && values.dateRange.length === 2) {
        const [start, end] = values.dateRange;
        body.start_date = start.format('YYYY-MM-DD HH:mm:ss');
        body.end_date = end.format('YYYY-MM-DD HH:mm:ss');
        body.duration_days = end.diff(start, 'day') + 1;
      }
      if (typeof values.status === 'string') body.status = values.status;
  
      // 新增：扩展保存字段
      if (typeof values.departure === 'string') body.departure = values.departure.trim();
      if (typeof values.budget === 'number') body.budget = values.budget;
      if (typeof values.transportation === 'string') body.transportation = normalizeTransportation(values.transportation);
      const nextPreferences = { ...(plan?.preferences || {}) };
      if (Array.isArray(values.travelPreferences)) {
        nextPreferences.interests = values.travelPreferences;
      }
      if (typeof values.travelers === 'number') {
        nextPreferences.travelers = values.travelers;
      }
      if (Array.isArray(values.ageGroups)) {
        nextPreferences.ageGroups = values.ageGroups.map((s: any) => String(s));
      }
      if (Array.isArray(values.foodPreferences)) {
        nextPreferences.foodPreferences = values.foodPreferences.map((s: any) => String(s));
      }
      if (Array.isArray(values.dietaryRestrictions)) {
        nextPreferences.dietaryRestrictions = values.dietaryRestrictions.map((s: any) => String(s));
      }
      body.preferences = nextPreferences;

      if (values.specialRequirements !== undefined) {
        const nextRequirements = { ...(plan?.requirements || {}) };
        const specialText =
          typeof values.specialRequirements === 'string'
            ? values.specialRequirements.trim()
            : '';
        if (specialText) {
          nextRequirements.special_requirements = specialText;
        } else {
          delete nextRequirements.special_requirements;
        }
        body.requirements = Object.keys(nextRequirements).length ? nextRequirements : {};
      }
  
      setSaving(true);
      const resp = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!resp.ok) throw new Error(`更新计划失败 (${resp.status})`);
      message.success('保存成功');
      navigate(`/plan/${planId}`);
    } catch (e) {
      console.error('保存失败:', e);
      message.error('保存失败，请检查表单');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Title level={3} style={{ marginBottom: 0 }}>编辑旅行计划</Title>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '24px' }}>
              <Spin />
            </div>
          ) : (
            <Form form={form} layout="vertical">
              {/* 基本信息 */}
              <Divider orientation="left">基本信息</Divider>
              <Form.Item label="标题" name="title" rules={[{ required: true, message: '请输入标题' }]}> 
                <Input placeholder="计划标题" />
              </Form.Item>
              <Form.Item label="出发地" name="departure"> 
                <Input placeholder="例如：上海" />
              </Form.Item>
              <Form.Item label="目的地" name="destination" rules={[{ required: true, message: '请输入目的地' }]}> 
                <Input placeholder="例如：北京" />
              </Form.Item>
              
              <Form.Item label="出行日期" name="dateRange"> 
                <RangePicker showTime />
              </Form.Item>
  
              {/* 旅行参数 */}
              <Divider orientation="left">旅行参数</Divider>
              <Space size="large" wrap>
                <Form.Item label="预算(￥)" name="budget">
                  <InputNumber style={{ width: 200 }} min={0} step={100} placeholder="预算" />
                </Form.Item>
                <Form.Item label="出行方式" name="transportation">
                  <Select options={TRANSPORTATION_OPTIONS} allowClear style={{ width: 200 }} placeholder="选择出行方式"/>
                </Form.Item>
                <Form.Item label="出行人数" name="travelers">
                  <InputNumber style={{ width: 120 }} min={1} placeholder="人数" />
                </Form.Item>
              </Space>
  
              {/* 人群与饮食 */}
              <Divider orientation="left">人群与饮食</Divider>
              <Form.Item label="年龄组成" name="ageGroups">
                <Select mode="multiple" options={AGE_GROUP_OPTIONS} placeholder="选择年龄组成"/>
              </Form.Item>
              <Form.Item label="口味偏好" name="foodPreferences">
                <Select mode="multiple" options={FOOD_PREFERENCES_OPTIONS} placeholder="选择口味偏好"/>
              </Form.Item>
              <Form.Item label="饮食禁忌" name="dietaryRestrictions">
                <Select mode="multiple" options={DIETARY_RESTRICTIONS_OPTIONS} placeholder="选择饮食禁忌"/>
              </Form.Item>
  
              {/* 偏好与特殊要求 */}
              <Divider orientation="left">偏好与特殊要求</Divider>
              <Form.Item label="旅行偏好" name="travelPreferences">
                <Select
                  mode="multiple"
                  options={PREFERENCES_OPTIONS}
                  placeholder="选择旅行偏好（与创建页一致）"
                  allowClear
                />
              </Form.Item>
              <Form.Item label="特殊要求" name="specialRequirements">
                <Input.TextArea
                  placeholder="请输入特殊要求（如：带老人、带小孩、无障碍设施、特殊饮食需求等）"
                  rows={4}
                />
              </Form.Item>

              {/* 状态与描述 */}
              <Divider orientation="left">状态与描述</Divider>
              <Form.Item label="状态" name="status"> 
                <Select options={STATUS_OPTIONS} placeholder="选择状态" allowClear />
              </Form.Item>
              <Form.Item label="描述" name="description"> 
                <Input.TextArea placeholder="计划描述" rows={4} />
              </Form.Item>
  
              <Space>
                <Button onClick={() => navigate(`/plan/${planId}`)}>取消</Button>
                <Button type="primary" loading={saving} onClick={handleSave}>保存</Button>
              </Space>
            </Form>
          )}
        </Space>
      </Card>
    </div>
  );
};

export default PlanEditPage;
