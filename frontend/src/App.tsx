import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import 'antd/dist/reset.css';
import './App.css';
import './pages/common.css';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';

import Layout from './components/Layout/Layout';
import RouterApp from './app/router/RouterApp';

const App: React.FC = () => {
  dayjs.locale('zh-cn');
  return (
    <ConfigProvider locale={zhCN} theme={{ token: { colorPrimary: '#6366f1', colorInfo: '#6366f1', colorSuccess: '#10b981', colorWarning: '#f59e0b', colorError: '#ef4444', borderRadius: 12 } }}>
      <Router>
        <div className="App">
          <Layout>
            <RouterApp />
          </Layout>
        </div>
      </Router>
    </ConfigProvider>
  );
};

export default App;
