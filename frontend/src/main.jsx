import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import viVN from 'antd/locale/vi_VN';
import App from './App.jsx';
import './styles/theme.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider
      locale={viVN}
      theme={{
        token: {
          colorPrimary: '#0062ff',
          borderRadius: 8,
          fontFamily: "'Be Vietnam Pro', sans-serif",
          fontSize: 16,
        },
        components: {
          Button: {
            colorPrimary: '#0062ff',
            colorPrimaryHover: '#3385ff',
            colorPrimaryActive: '#0052cc',
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
