import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Space, Spin, Button, message, Modal, Form, Input, Popconfirm } from 'antd';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Title } = Typography;

interface UserItem {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  role: string;
  is_verified: boolean;
}

const UsersAdminPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<UserItem[]>([]);
  // 编辑用户名
  const [editVisible, setEditVisible] = useState(false);
  const [editTarget, setEditTarget] = useState<UserItem | null>(null);
  const [editForm] = Form.useForm();
  // 重置密码
  const [resetVisible, setResetVisible] = useState(false);
  const [resetTarget, setResetTarget] = useState<UserItem | null>(null);
  const [resetForm] = Form.useForm();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.USERS + '/'));
      const data = await res.json();
      setUsers(Array.isArray(data) ? data : []);
    } catch (e) {
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const openEditUsername = (user: UserItem) => {
    setEditTarget(user);
    setEditVisible(true);
    editForm.setFieldsValue({ username: user.username });
  };

  const submitEditUsername = async () => {
    try {
      const values = await editForm.validateFields();
      const newUsername = values.username?.trim();
      if (!editTarget || !newUsername) return;
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.USER_DETAIL(editTarget.id)), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: newUsername }),
      });
      if (res.ok) {
        message.success('用户名已更新');
        setEditVisible(false);
        setEditTarget(null);
        fetchUsers();
      } else {
        const err = await res.json();
        message.error(err?.detail || '更新失败');
      }
    } catch (e) {
      // 表单校验或请求失败
      if ((e as any)?.errorFields) return;
      message.error('请求失败');
    }
  };

  const openResetPassword = (user: UserItem) => {
    setResetTarget(user);
    setResetVisible(true);
    resetForm.resetFields();
  };

  const submitResetPassword = async () => {
    try {
      const values = await resetForm.validateFields();
      const pwd = values.new_password;
      const confirm = values.confirm_password;
      if (pwd !== confirm) {
        message.error('两次输入的密码不一致');
        return;
      }
      if (!resetTarget) return;
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.USER_RESET_PASSWORD(resetTarget.id)), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: pwd }),
      });
      if (res.ok) {
        message.success('密码已重置');
        setResetVisible(false);
        setResetTarget(null);
      } else {
        const err = await res.json();
        message.error(err?.detail || '重置失败');
      }
    } catch (e) {
      if ((e as any)?.errorFields) return;
      message.error('请求失败');
    }
  };

  const handleDeleteUser = async (user: UserItem) => {
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.USER_DETAIL(user.id)), {
        method: 'DELETE',
      });
      if (res.ok) {
        message.success('用户已删除');
        fetchUsers();
      } else {
        const err = await res.json();
        message.error(err?.detail || '删除失败');
      }
    } catch (e) {
      message.error('请求失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
    { 
      title: '角色', 
      dataIndex: 'role', 
      key: 'role',
      render: (role: string) => (
        <Tag color={role === 'admin' ? 'red' : 'blue'}>{role}</Tag>
      )
    },
    { 
      title: '已验证', 
      dataIndex: 'is_verified', 
      key: 'is_verified',
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'orange'}>{v ? '是' : '否'}</Tag>
      )
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: UserItem) => (
        <Space>
          <Button type="link" onClick={() => openEditUsername(record)}>编辑用户名</Button>
          <Button type="link" onClick={() => openResetPassword(record)}>重置密码</Button>
          <Popconfirm title={`确认删除用户 ${record.username} ?`} onConfirm={() => handleDeleteUser(record)}>
            <Button type="link" danger>删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={2}>用户管理</Title>
        </div>
        <Card>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 32 }}>
              <Spin />
            </div>
          ) : (
            <Table
              rowKey="id"
              columns={columns as any}
              dataSource={users}
              pagination={{ pageSize: 10 }}
            />
          )}
        </Card>
      </Space>

      {/* 编辑用户名 Modal */}
      <Modal
        title="编辑用户名"
        open={editVisible}
        onOk={submitEditUsername}
        onCancel={() => { setEditVisible(false); setEditTarget(null); }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}> 
            <Input placeholder="请输入新的用户名" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 重置密码 Modal */}
      <Modal
        title="重置密码"
        open={resetVisible}
        onOk={submitResetPassword}
        onCancel={() => { setResetVisible(false); setResetTarget(null); }}
        okText="重置"
        cancelText="取消"
      >
        <Form form={resetForm} layout="vertical">
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '密码至少6位' }]}> 
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item name="confirm_password" label="确认密码" rules={[{ required: true, message: '请再次输入新密码' }]}> 
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UsersAdminPage;