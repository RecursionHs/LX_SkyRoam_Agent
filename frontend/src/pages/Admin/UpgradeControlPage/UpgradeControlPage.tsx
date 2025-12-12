import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Switch,
  Input,
  Form,
  Progress,
  Timeline,
  Badge,
  Space,
  Divider,
  message,
  Modal,
  Select,
  InputNumber,
  Typography,
  Tag,
  Alert
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  RocketOutlined,
  SettingOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import './UpgradeControlPage.css';
import UpgradeManager, { UpgradeConfig, UpgradeFeature } from '../../../utils/upgradeManager';
const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const UpgradeControlPage: React.FC = () => {
  const [config, setConfig] = useState<UpgradeConfig>(UpgradeManager.getCurrentConfig());
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [featureForm] = Form.useForm();

  // 监听配置变化
  useEffect(() => {
    const cleanup = UpgradeManager.onConfigChange((newConfig) => {
      setConfig(newConfig);
    });
    return cleanup;
  }, []);

  // 刷新配置
  const refreshConfig = () => {
    const currentConfig = UpgradeManager.getCurrentConfig();
    setConfig(currentConfig);
    form.setFieldsValue(currentConfig);
  };

  // 启动新升级
  const startUpgrade = async (values: any) => {
    setLoading(true);
    try {
      const upgradeConfig: Partial<UpgradeConfig> = {
        version: values.version,
        title: values.title,
        description: values.description,
        status: 'in-progress',
        enabled: true,
        showProgress: true,
        progress: 0,
        features: values.features || []
      };

      UpgradeManager.startNewUpgrade(upgradeConfig);
      message.success(`升级 ${values.version} 已启动！`);
      refreshConfig();
    } catch (error) {
      message.error('启动升级失败');
    } finally {
      setLoading(false);
    }
  };

  // 更新进度
  const updateProgress = (progress: number) => {
    UpgradeManager.updateProgress(progress);
    refreshConfig();
  };

  // 完成升级
  const completeUpgrade = () => {
    Modal.confirm({
      title: '确认完成升级',
      content: `确定要完成 ${config.version} 版本的升级吗？完成后用户将看到升级完成通知。`,
      icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      onOk: () => {
        UpgradeManager.completeUpgrade();
        message.success('升级已完成！');
        refreshConfig();
      }
    });
  };

  // 停用升级
  const disableUpgrade = () => {
    Modal.confirm({
      title: '确认停用升级',
      content: '确定要停用升级通知吗？用户将不再看到升级提醒。',
      icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
      onOk: () => {
        UpgradeManager.disableUpgrade();
        message.success('升级通知已停用');
        refreshConfig();
      }
    });
  };

  // 启用升级
  const enableUpgrade = () => {
    UpgradeManager.enableUpgrade();
    message.success('升级通知已启用');
    refreshConfig();
  };

  // 添加功能项
  const addFeature = () => {
    const features = form.getFieldValue('features') || [];
    const newFeature: UpgradeFeature = {
      title: '',
      description: '',
      status: 'upcoming'
    };
    form.setFieldValue('features', [...features, newFeature]);
  };

  // 删除功能项
  const removeFeature = (index: number) => {
    const features = form.getFieldValue('features') || [];
    const newFeatures = features.filter((_: any, i: number) => i !== index);
    form.setFieldValue('features', newFeatures);
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'completed':
        return <Tag color="success">已完成</Tag>;
      case 'in-progress':
        return <Tag color="processing">升级中</Tag>;
      case 'upcoming':
        return <Tag color="warning">即将推出</Tag>;
      default:
        return <Tag>未知</Tag>;
    }
  };

  const controlActions = [
    {
      key: 'start',
      label: '启动新升级',
      icon: <PlayCircleOutlined />,
      action: () => form.submit(),
      type: 'primary',
      disabled: config.status === 'in-progress'
    },
    {
      key: 'complete',
      label: '完成升级',
      icon: <CheckCircleOutlined />,
      action: completeUpgrade,
      disabled: config.status !== 'in-progress'
    },
    {
      key: 'enable',
      label: '启用通知',
      icon: <RocketOutlined />,
      action: enableUpgrade,
      disabled: config.enabled
    },
    {
      key: 'disable',
      label: '停用通知',
      icon: <PauseCircleOutlined />,
      action: disableUpgrade,
      disabled: !config.enabled
    },
    {
      key: 'refresh',
      label: '刷新配置',
      icon: <ReloadOutlined />,
      action: refreshConfig
    }
  ];

  return (
    <div className="upgrade-control-page">
      <div className="page-header">
        <Title level={2}>
          <SettingOutlined /> 升级通知控制台
        </Title>
        <Paragraph>
          管理系统升级通知的显示状态、版本信息和功能特性。
        </Paragraph>
      </div>

      {/* 当前状态卡片 */}
      <Card title="当前升级状态" className="status-card" extra={
        <Space>
          <Tag color={config.enabled ? 'green' : 'red'}>
            {config.enabled ? '已启用' : '已停用'}
          </Tag>
          <Tag color={
            config.status === 'completed' ? 'green' :
            config.status === 'in-progress' ? 'blue' : 'orange'
          }>
            {config.status === 'completed' ? '已完成' :
             config.status === 'in-progress' ? '升级中' : '即将开始'}
          </Tag>
        </Space>
      }>
        <div className="status-content">
          <div className="status-item">
            <Text strong>当前版本:</Text>
            <Text>{config.version}</Text>
          </div>
          <div className="status-item">
            <Text strong>升级标题:</Text>
            <Text>{config.title}</Text>
          </div>
          <div className="status-item">
            <Text strong>升级描述:</Text>
            <Text>{config.description}</Text>
          </div>
          
          {config.showProgress && (
            <div className="progress-section">
              <Text strong>升级进度:</Text>
              <Progress
                percent={config.progress}
                status="active"
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
              <div className="progress-controls">
                <InputNumber
                  min={0}
                  max={100}
                  value={config.progress}
                  onChange={(value) => updateProgress(value || 0)}
                  placeholder="输入进度"
                />
                <Button
                  type="primary"
                  icon={<SyncOutlined />}
                  onClick={() => {
                    const newProgress = Math.min(100, config.progress + 10);
                    updateProgress(newProgress);
                  }}
                >
                  +10%
                </Button>
                <Button
                  onClick={() => updateProgress(100)}
                >
                  完成
                </Button>
              </div>
            </div>
          )}
        </div>

        <Divider />

        <div className="control-actions">
          <Space wrap>
            {controlActions.map(action => (
              <Button
                key={action.key}
                type={action.type as any}
                icon={action.icon}
                onClick={action.action}
                disabled={action.disabled}
                loading={loading}
              >
                {action.label}
              </Button>
            ))}
          </Space>
        </div>
      </Card>

      {/* 创建新升级 */}
      <Card title="创建新升级" className="create-upgrade-card">
        <Form
          form={form}
          layout="vertical"
          onFinish={startUpgrade}
          initialValues={config}
        >
          <div className="form-grid">
            <Form.Item
              label="版本号"
              name="version"
              rules={[{ required: true, message: '请输入版本号' }]}
            >
              <Input placeholder="例如: 2.1.0" />
            </Form.Item>

            <Form.Item
              label="升级标题"
              name="title"
              rules={[{ required: true, message: '请输入升级标题' }]}
            >
              <Input placeholder="升级的标题" />
            </Form.Item>

            <Form.Item
              label="升级描述"
              name="description"
              rules={[{ required: true, message: '请输入升级描述' }]}
            >
              <TextArea rows={3} placeholder="描述本次升级的主要内容" />
            </Form.Item>

            <Form.Item label="显示进度条" name="showProgress" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item label="启用通知" name="enabled" valuePropName="checked">
              <Switch />
            </Form.Item>
          </div>

          <Form.List name="features">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <div key={key} className="feature-item">
                    <div className="feature-header">
                      <Text strong>功能项 {name + 1}</Text>
                      <Button
                        type="text"
                        danger
                        icon={<PauseCircleOutlined />}
                        onClick={() => remove(name)}
                      />
                    </div>
                    <div className="feature-form">
                      <Form.Item
                        {...restField}
                        name={[name, 'title']}
                        label="功能标题"
                        rules={[{ required: true, message: '请输入功能标题' }]}
                      >
                        <Input placeholder="例如: 🚀 AI 智能引擎升级" />
                      </Form.Item>

                      <Form.Item
                        {...restField}
                        name={[name, 'description']}
                        label="功能描述"
                        rules={[{ required: true, message: '请输入功能描述' }]}
                      >
                        <TextArea rows={2} placeholder="详细描述这个功能" />
                      </Form.Item>

                      <Form.Item
                        {...restField}
                        name={[name, 'status']}
                        label="状态"
                        initialValue="upcoming"
                      >
                        <Select>
                          <Select.Option value="completed">已完成</Select.Option>
                          <Select.Option value="in-progress">升级中</Select.Option>
                          <Select.Option value="upcoming">即将推出</Select.Option>
                        </Select>
                      </Form.Item>
                    </div>
                  </div>
                ))}
                <Form.Item>
                  <Button
                    type="dashed"
                    onClick={() => add()}
                    block
                    icon={<PlayCircleOutlined />}
                  >
                    添加功能项
                  </Button>
                </Form.Item>
              </>
            )}
          </Form.List>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              启动升级
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 功能预览 */}
      {config.features && config.features.length > 0 && (
        <Card title="功能预览" className="preview-card">
          <Timeline>
            {config.features.map((feature, index) => (
              <Timeline.Item
                key={index}
                dot={
                  feature.status === 'completed' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                  feature.status === 'in-progress' ? <SyncOutlined spin style={{ color: '#1890ff' }} /> :
                  <RocketOutlined style={{ color: '#faad14' }} />
                }
                color={
                  feature.status === 'completed' ? 'green' :
                  feature.status === 'in-progress' ? 'blue' : 'orange'
                }
              >
                <div className="preview-feature">
                  <div className="preview-header">
                    <Text strong>{feature.title}</Text>
                    {getStatusTag(feature.status)}
                  </div>
                  <Paragraph type="secondary">{feature.description}</Paragraph>
                </div>
              </Timeline.Item>
            ))}
          </Timeline>
        </Card>
      )}

      {/* 使用说明 */}
      <Alert
        message="使用说明"
        description={
          <ul>
            <li>启动新升级会重置用户的通知状态，确保用户能看到新版本的通知</li>
            <li>升级进度可以手动调整，也可以自动递增</li>
            <li>完成升级后，用户看到的是"升级完成"状态，不再显示进度</li>
            <li>停用通知会完全隐藏升级提醒，包括头部按钮</li>
            <li>所有操作都会实时反映在用户界面上</li>
          </ul>
        }
        type="info"
        showIcon
      />
    </div>
  );
};

export default UpgradeControlPage;
