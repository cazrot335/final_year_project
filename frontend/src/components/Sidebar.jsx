import { Layout } from "antd";
import { NavLink } from "react-router-dom";
import {
  HomeOutlined,
  SearchOutlined,
  NodeIndexOutlined,
  RobotOutlined
} from "@ant-design/icons";

import "../styles/sidebar.css";

const { Sider } = Layout;

export default function Sidebar() {

  return (
    <Sider width={230} className="sidebar">

      <div className="logo">
        Scout
      </div>

      <nav className="menu">

        <NavLink to="/" end className="menu-item">
          <HomeOutlined />
          <span>Dashboard</span>
        </NavLink>

        <NavLink to="/discovery" className="menu-item">
          <SearchOutlined />
          <span>Discovery</span>
        </NavLink>

        <NavLink to="/gap-analysis" className="menu-item">
          <NodeIndexOutlined />
          <span>Gap Analysis</span>
        </NavLink>

        <NavLink to="/interview" className="menu-item">
          <RobotOutlined />
          <span>Agentic Interview</span>
        </NavLink>

      </nav>

    </Sider>
  );
}