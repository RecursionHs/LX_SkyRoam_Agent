import React, { useState, useRef, useEffect } from 'react';
import { FloatButton, Modal, Input, Button, List, Avatar, Spin, Space, Typography, message } from 'antd';
import { MessageOutlined, SendOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { getToken } from '../../utils/auth';
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

  // 监听来自外部的事件，用于设置初始消息上下文
  useEffect(() => {
    const handleSetContext = (event: CustomEvent) => {
      const { context, openModal = true } = event.detail || {};
      if (context) {
        // 设置初始消息
        const initialMessages: Message[] = [
          {
            role: 'assistant',
            content: context,
            timestamp: Date.now()
          }
        ];
        setMessages(initialMessages);
        
        // 如果需要，自动打开对话框
        if (openModal) {
          setVisible(true);
        }
      }
    };

    window.addEventListener('ai-assistant:set-context', handleSetContext as EventListener);
    
    return () => {
      window.removeEventListener('ai-assistant:set-context', handleSetContext as EventListener);
    };
  }, []);

  // 发送消息（流式）
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

    // 创建AI消息占位符
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: Date.now() + 1 // 确保时间戳不同
    };
    const messagesWithAssistant = [...newMessages, assistantMessage];
    setMessages(messagesWithAssistant);

    try {
      // 构建对话历史（只包含role和content）
      const conversationHistory = newMessages
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }));

      // 获取token
      const token = getToken();
      if (!token) {
        throw new Error('未登录');
      }

      // 调用流式API
      const response = await fetch(buildApiUrl(API_ENDPOINTS.OPENAI_CHAT_STREAM), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
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

      // 读取流式响应
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      const updateMessage = (content: string) => {
        setMessages(prev => {
          const updated = [...prev];
          // 查找最后一个AI消息（role为assistant且可能是空的）
          // 从后往前查找，找到第一个assistant消息
          let targetIndex = -1;
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].role === 'assistant') {
              targetIndex = i;
              break;
            }
          }
          
          // 如果找到了，更新它
          if (targetIndex !== -1) {
            updated[targetIndex] = {
              ...updated[targetIndex],
              content: content
            };
          }
          return updated;
        });
        // 滚动到底部
        setTimeout(() => scrollToBottom(), 10);
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'content') {
                accumulatedContent += data.content;
                updateMessage(accumulatedContent);
              } else if (data.type === 'done') {
                setLoading(false);
                updateMessage(accumulatedContent);
              } else if (data.type === 'error') {
                throw new Error(data.message || '流式响应错误');
              }
            } catch (e) {
              // 忽略JSON解析错误
              console.warn('解析流式数据失败:', e);
            }
          }
        }
      }
    } catch (error: any) {
      console.error('AI对话失败:', error);
      message.error(error.message || 'AI对话失败，请稍后重试');
      setLoading(false);
      
      // 更新错误消息
      setMessages(prev => {
        const updated = [...prev];
        // 查找最后一个AI消息（role为assistant）
        let targetIndex = -1;
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === 'assistant') {
            targetIndex = i;
            break;
          }
        }
        if (targetIndex !== -1) {
          updated[targetIndex] = {
            ...updated[targetIndex],
            content: `抱歉，我遇到了一些问题：${error.message || '未知错误'}`
          };
        }
        return updated;
      });
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

