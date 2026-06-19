import { Avatar, Card, Col, Descriptions, Empty, Row, Space, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { kpiApi } from '../api/kpiApi';
import TaskTable from '../components/TaskTable';

export default function EmployeeProfilePage() {
  const { userId } = useParams();
  const [profile, setProfile] = useState(null);
  useEffect(() => { kpiApi.profile(userId).then(setProfile); }, [userId]);
  if (!profile) return <Empty description="Đang tải hồ sơ" />;
  return (
    <Space direction="vertical" size={18} className="page">
      <Typography.Title level={3}>Hồ sơ Cán bộ AI</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card>
            <Space direction="vertical" align="center" className="profile-card">
              <Avatar size={96}>{profile.user.full_name?.[0]}</Avatar>
              <Typography.Title level={4}>{profile.user.full_name}</Typography.Title>
              <Typography.Text>{profile.user.position_title}</Typography.Text>
              <Typography.Text type="secondary">{profile.user.department}</Typography.Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title="Thông tin KPI">
            <Descriptions column={2}>
              <Descriptions.Item label="Email">{profile.user.email}</Descriptions.Item>
              <Descriptions.Item label="Vai trò">{profile.user.role}</Descriptions.Item>
              <Descriptions.Item label="Template">{profile.user.kpi_role_template}</Descriptions.Item>
              <Descriptions.Item label="Điểm">{profile.score?.total_score || '-'}</Descriptions.Item>
              <Descriptions.Item label="Xếp loại">{profile.score?.classification || '-'}</Descriptions.Item>
              <Descriptions.Item label="Rủi ro">{profile.score?.risk_level || '-'}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>
      <Card title="Nhiệm vụ liên quan">
        <TaskTable data={profile.tasks || []} />
      </Card>
    </Space>
  );
}
