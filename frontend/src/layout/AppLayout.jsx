import { Layout } from "antd";
import Sidebar from "../components/Sidebar";
import "../styles/layout.css";

const { Content } = Layout;

export default function AppLayout({ children }) {

  return (
    <Layout className="app-layout">

      <Sidebar />

      <Layout className="content-layout">

        <Content className="main-content">
          {children}
        </Content>

      </Layout>

    </Layout>
  );
}