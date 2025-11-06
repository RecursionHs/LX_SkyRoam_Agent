import React, { useState, useEffect, useRef } from 'react';
import { 
  Card, 
  List, 
  Typography, 
  Space,
  Tag,
  Button,
  Row,
  Col,
  Empty,
  Spin,
  Pagination,
  Input,
  Select,
  DatePicker,
  Rate
} from 'antd';
import { 
  CalendarOutlined, 
  EnvironmentOutlined,
  EyeOutlined,
  DeleteOutlined,
  EditOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';
import dayjs from 'dayjs';
import { useSearchParams } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

interface TravelPlan {
  id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  status: string;
  score: number;
  created_at: string;
}

const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const latestReq = useRef(0);
  // 初始值来自URL参数，避免刷新后丢失
  const initialKeyword = searchParams.get('keyword') || '';
  const initialMinScoreStr = searchParams.get('min_score');
  const initialMinScore = initialMinScoreStr ? Number(initialMinScoreStr) : undefined;
  const initialTravelFrom = searchParams.get('travel_from');
  const initialTravelTo = searchParams.get('travel_to');
  const initialRange = initialTravelFrom && initialTravelTo ? [dayjs(initialTravelFrom), dayjs(initialTravelTo)] : [];
  const initialSkipStr = searchParams.get('skip');
  const initialLimitStr = searchParams.get('limit');

  const [plans, setPlans] = useState<TravelPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const pageSize = 6;
  const initialPage = initialSkipStr ? (Math.floor(Number(initialSkipStr) / Number(initialLimitStr || pageSize)) + 1) : 1;
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState<string>(initialKeyword);
  const [keywordInput, setKeywordInput] = useState<string>(initialKeyword);
  const [minScore, setMinScore] = useState<number | undefined>(initialMinScore);
  const [dateRange, setDateRange] = useState<any[]>(initialRange);

  // 当筛选或分页变化时，把状态写入URL，防止刷新后丢失
  useEffect(() => {
    const params: Record<string, string> = {
      skip: String((currentPage - 1) * pageSize),
      limit: String(pageSize),
    };
    if (keyword && keyword.trim()) params.keyword = keyword.trim();
    if (typeof minScore === 'number') params.min_score = String(minScore);
    if (dateRange && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
      const fromStr = toDateStr(dateRange[0]);
      const toStr = toDateStr(dateRange[1]);
      if (fromStr) params.travel_from = fromStr;
      if (toStr) params.travel_to = toStr;
    }
    setSearchParams(params, { replace: true });
  }, [currentPage, keyword, minScore, dateRange]);

  useEffect(() => {
    fetchPlans();
  }, [currentPage, keyword, minScore, dateRange]);

  // 将日期转换为 YYYY-MM-DD 字符串（兼容 dayjs 与原生 Date）
  const toDateStr = (d: any): string => {
    if (!d) return '';
    try {
      const dj = (typeof d.isValid === 'function') ? d : dayjs(d);
      if (!dj.isValid()) return '';
      return dj.format('YYYY-MM-DD');
    } catch {
      return '';
    }
  };

  const fetchPlans = async () => {
    const reqId = ++latestReq.current;
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.set('skip', String((currentPage - 1) * pageSize));
      params.set('limit', String(pageSize));
      if (keyword && keyword.trim()) params.set('keyword', keyword.trim());
      if (typeof minScore === 'number') params.set('min_score', String(minScore));
      if (dateRange && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
        const fromStr = toDateStr(dateRange[0]);
        const toStr = toDateStr(dateRange[1]);
        if (fromStr) params.set('travel_from', fromStr);
        if (toStr) params.set('travel_to', toStr);
      }

      const response = await authFetch(
        buildApiUrl(`/travel-plans/?${params.toString()}`)
      );
      if (!response.ok) {
        throw new Error('获取历史记录失败');
      }
      const data = await response.json();
      if (reqId !== latestReq.current) return; // 只有最新请求可写状态，防止旧数据覆盖
      const list = Array.isArray(data?.plans) ? data.plans : (Array.isArray(data) ? data : []);
      const totalCount = typeof data?.total === 'number' ? data.total : (Array.isArray(data) ? data.length : 0);
      setPlans(list);
      setTotal(totalCount);
    } catch (error) {
      if (reqId !== latestReq.current) return;
      console.error('获取历史记录失败:', error);
      setPlans([]);
      setTotal(0);
    } finally {
      if (reqId === latestReq.current) setLoading(false);
    }
  };

  const handleViewPlan = (planId: number) => {
    navigate(`/plan/${planId}`);
  };

  const handleEditPlan = (planId: number) => {
    navigate(`/plan?edit=${planId}`);
  };

  const handleDeletePlan = async (planId: number) => {
    try {
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)), {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchPlans(); // 刷新列表
      }
    } catch (error) {
      console.error('删除计划失败:', error);
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap = {
      draft: { color: 'default', text: '草稿' },
      generating: { color: 'processing', text: '生成中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
      archived: { color: 'default', text: '已归档' }
    };
    
    const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN');
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>
          <Text>加载中...</Text>
        </div>
      </div>
    );
  }

  return (
    <div className="history-page" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>我的旅行计划</Title>
        <Paragraph style={{ color: '#666' }}>
          查看和管理您的所有旅行计划
        </Paragraph>
      </div>

      {/* 新增：搜索过滤条 */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Input.Search
            placeholder="关键词（标题/目的地/描述）"
            allowClear
            style={{ width: 280 }}
            value={keywordInput}
            onChange={(e) => { setKeywordInput(e.target.value); }}
            onSearch={(v) => { const t = v.trim(); setKeyword(t); setKeywordInput(t); setCurrentPage(1); }}
          />
          <Select
            placeholder="评分"
            allowClear
            style={{ width: 160 }}
            value={minScore}
            onChange={(v) => { setMinScore(v as number | undefined); setCurrentPage(1); }}
            options={[
              { value: 1, label: '1星及以上' },
              { value: 2, label: '2星及以上' },
              { value: 3, label: '3星及以上' },
              { value: 4, label: '4星及以上' },
              { value: 5, label: '5星' },
            ]}
          />
          <DatePicker.RangePicker
            value={dateRange as any}
            onChange={(range) => { setDateRange(range || []); setCurrentPage(1); }}
          />
          <Button onClick={() => { setKeyword(''); setKeywordInput(''); setMinScore(undefined); setDateRange([]); setCurrentPage(1); }}>
            重置
          </Button>
        </Space>
      </Card>

      {plans.length === 0 ? (
        <Card>
          <Empty
            description="还没有旅行计划"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button 
              type="primary" 
              onClick={() => navigate('/plan')}
            >
              创建第一个计划
            </Button>
          </Empty>
        </Card>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {plans.map((plan) => (
              <Col xs={24} sm={12} lg={8} key={plan.id}>
                <Card
                  className="travel-card"
                  hoverable
                  actions={[
                    <Button 
                      type="text" 
                      icon={<EyeOutlined />}
                      onClick={() => handleViewPlan(plan.id)}
                    >
                      查看
                    </Button>,
                    <Button 
                      type="text" 
                      icon={<EditOutlined />}
                      onClick={() => handleEditPlan(plan.id)}
                    >
                      编辑
                    </Button>,
                    <Button 
                      type="text" 
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleDeletePlan(plan.id)}
                    >
                      删除
                    </Button>
                  ]}
                >
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Title level={4} style={{ margin: 0, flex: 1 }}>
                        {plan.title}
                      </Title>
                      <Tag color="purple" style={{ marginLeft: '8px' }}>
                        ID: {plan.id}
                      </Tag>
                    </div>
                    
                    <Space>
                      <Tag color="blue" icon={<EnvironmentOutlined />}>
                        {plan.destination}
                      </Tag>
                      <Tag color="green" icon={<CalendarOutlined />}>
                        {plan.duration_days} 天
                      </Tag>
                    </Space>
                    
                    <div>
                      <Text type="secondary">
                        {formatDate(plan.start_date)} - {formatDate(plan.end_date)}
                      </Text>
                    </div>
                    {/* 状态与评分显示 */}
                    <div>
                      <Space>
                        {getStatusTag(plan.status)}
                        {typeof plan.score === 'number' && (
                          <>
                            <Tag color="orange">评分: {plan.score.toFixed(1)}</Tag>
                            <Rate disabled allowHalf value={plan.score} style={{ fontSize: 14 }} />
                          </>
                        )}
                      </Space>
                    </div>
                    
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        创建时间: {formatDateTime(plan.created_at)}
                      </Text>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>

          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <Pagination
              current={currentPage}
              total={total}
              pageSize={pageSize}
              onChange={setCurrentPage}
              showSizeChanger={false}
              showQuickJumper
              showTotal={(total, range) => 
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
              }
            />
          </div>
        </>
      )}
    </div>
  );
};

export default HistoryPage;

// 移除不再需要的整日 ISO 边界函数
// const toISOStart = ...
// const toISOEnd = ...
