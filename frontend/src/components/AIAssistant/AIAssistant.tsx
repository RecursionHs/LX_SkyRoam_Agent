import React, { useState, useRef, useEffect } from 'react';
import { FloatButton, Modal, Input, Button, List, Avatar, Spin, Space, Typography, message } from 'antd';
import { MessageOutlined, SendOutlined, CloseOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';
import './AIAssistant.css';

const { TextArea } = Input;
const { Text } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

const AIAssistant: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (visible) {
      scrollToBottom();
      // 延迟聚焦输入框
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [visible, messages]);

  // 发送消息
  const handleSend = async () => {
    if (!inputValue.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: Date.now()
    };

    // 添加用户消息
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputValue('');
    setLoading(true);

    try {
      // 构建对话历史（只包含role和content）
      const conversationHistory = newMessages
        //.filter(msg => msg.role !== 'system')
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }));

      // 调用API
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.OPENAI_CHAT), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_history: conversationHistory.slice(0, -1), // 排除当前消息
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(errorData.detail || `请求失败 (${response.status})`);
      }

      const data = await response.json();

      if (data.status === 'success') {
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.message,
          timestamp: Date.now()
        };
        setMessages([...newMessages, assistantMessage]);
      } else {
        throw new Error(data.message || 'AI响应异常');
      }
    } catch (error: any) {
      console.error('AI对话失败:', error);
      message.error(error.message || 'AI对话失败，请稍后重试');
      
      // 添加错误消息
      const errorMessage: Message = {
        role: 'assistant',
        content: `抱歉，我遇到了一些问题：${error.message || '未知错误'}`,
        timestamp: Date.now()
      };
      setMessages([...newMessages, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // 清空对话
  const handleClear = () => {
    setMessages([]);
    message.success('对话已清空');
  };

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <FloatButton
        icon={<MessageOutlined />}
        type="primary"
        style={{
          right: 24,
          bottom: 24,
          width: 56,
          height: 56,
        }}
        onClick={() => setVisible(true)}
      />

      <Modal
        title={
          <Space>
            <RobotOutlined style={{ color: '#6366f1' }} />
            <span>AI 助手</span>
          </Space>
        }
        open={visible}
        onCancel={() => setVisible(false)}
        footer={null}
        width={600}
        className="ai-assistant-modal"
        styles={{
          body: {
            padding: 0,
            height: '600px',
            display: 'flex',
            flexDirection: 'column',
          }
        }}
      >
        <div className="ai-assistant-container">
          {/* 消息列表 */}
          <div className="ai-assistant-messages">
            {messages.length === 0 ? (
              <div className="ai-assistant-empty">
                <RobotOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
                <Text type="secondary">我是您的AI旅行助手，有什么问题可以问我哦~</Text>
                <div style={{ marginTop: 24 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    提示：您可以复制页面上的内容到这里提问
                  </Text>
                </div>
              </div>
            ) : (
              <List
                dataSource={messages}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      border: 'none',
                      padding: '12px 16px',
                      justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <div
                      className={`ai-message ${item.role === 'user' ? 'ai-message-user' : 'ai-message-assistant'}`}
                    >
                      <Space align="start" size={12}>
                        {item.role === 'assistant' && (
                          <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#6366f1', flexShrink: 0 }} />
                        )}
                        <div className="ai-message-content">
                          <div className="ai-message-text">{item.content}</div>
                        </div>
                        {item.role === 'user' && (
                          <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#10b981', flexShrink: 0 }} />
                        )}
                      </Space>
                    </div>
                  </List.Item>
                )}
              />
            )}
            {loading && (
              <div style={{ padding: '12px 16px', display: 'flex', justifyContent: 'flex-start' }}>
                <Space>
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#6366f1' }} />
                  <Spin size="small" />
                  <Text type="secondary">AI正在思考...</Text>
                </Space>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="ai-assistant-input">
            <Space.Compact style={{ width: '100%' }}>
              <TextArea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题...（Shift+Enter换行，Enter发送）"
                autoSize={{ minRows: 1, maxRows: 4 }}
                disabled={loading}
                style={{ resize: 'none' }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={loading}
                disabled={!inputValue.trim()}
                style={{ height: 'auto' }}
              >
                发送
              </Button>
            </Space.Compact>
            {messages.length > 0 && (
              <Button
                type="text"
                size="small"
                onClick={handleClear}
                style={{ marginTop: 8, padding: 0 }}
              >
                清空对话
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </>
  );
};

export default AIAssistant;

