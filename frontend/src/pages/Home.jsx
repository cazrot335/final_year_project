import { Progress, Card, Row, Col, Button } from "antd";
import "../styles/home.css";
import { useState, useEffect } from "react";

export default function Home() {

  const [logs, setLogs] = useState([]);

  const [stats, setStats] = useState([
    { name: "Global Talent Harvested", value: 0, percent: 0 },
    { name: "Data Integrity Cleared", value: 0, percent: 0 },
    { name: "Engineered Matches", value: 0, percent: 0 },
    { name: "Interview Finalists", value: 0, percent: 0 }
  ]);

  useEffect(() => {

  const fetchLogs = () => {
    fetch("http://localhost:5000/api/scrape-logs")
      .then(res => res.json())
      .then(data => {

        const formatted = data.map(log => 
          `[${log.timestamp}] DISCOVERY "${log.keyword}" → Found ${log.total_found} profiles | +${log.unique_new} unique | ${log.efficiency}% efficiency`
        );

        setLogs(formatted);
      });
  };

  fetchLogs();

  const interval = setInterval(fetchLogs, 3000);

  return () => clearInterval(interval);

}, []);

    useEffect(() => {
  fetch("http://localhost:5000/api/dashboard-stats")
    .then(res => res.json())
    .then(data => {

      const scraped = data.total_scraped_links || 0;
      const unique = data.total_unique_profiles || 0;

      const matches = Math.floor(unique * 0.4);
      const finalists = Math.floor(matches * 0.25);

      const integrityEfficiency = scraped ? Math.round((unique / scraped) * 100) : 0;
      const matchEfficiency = unique ? Math.round((matches / unique) * 100) : 0;
      const interviewEfficiency = matches ? Math.round((finalists / matches) * 100) : 0;

      setStats([
        {
          name: "Global Talent Harvested",
          value: scraped,
          efficiency: integrityEfficiency
          
        },
        {
          name: "Data Integrity Cleared",
          value: unique,
          efficiency: integrityEfficiency
        },
        {
          name: "Engineered Matches",
          value: matches,
          efficiency: matchEfficiency
        },
        {
          name: "Interview Finalists",
          value: finalists,
          efficiency: interviewEfficiency
        }
      ]);

    });
}, []);


  return (
    <div className="home-container">

      {/* HERO */}
      <section className="hero">

        <h1 className="hero-title">
          Autonomous Talent Sourcing: From LinkedIn Dorking to Final Round Hires
        </h1>

        <p className="hero-subtitle">
          A local-first, agentic recruiting pipeline that ingests, verifies
          and interviews candidates with RAG-powered precision.
        </p>

        <Button className="start-btn">
          Start Discovery
        </Button>

      </section>


      {/* LIVE PIPELINE RIBBON */}
       <section className="pipeline">

        <h2 className="section-title">Live Pipeline Ribbon</h2>

        {stats.map((stat, index) => (
          <div key={index} className="pipeline-bar">

            <div className="pipeline-header">
              <span>{stat.name}</span>
              <span className="pipeline-number">{stat.value}</span>
            </div>

            <Progress
              percent={stat.efficiency}
          
              showInfo={false}
              strokeColor="#5E5ADB"
              status="active"
            />

          </div>
        ))}

      </section>


      {/* TERMINAL FEED */}
      <section className="terminal-section">

       <Card title="Real-Time Engine Feed">

  <div className="terminal">

    {logs.map((log, i) => (
      <p key={i}>{log}</p>
    ))}

  </div>

</Card>

      </section>


      {/* CORE PIPELINE MODULES */}
      <section className="modules">

        <h2 className="section-title">Core Pipeline Modules</h2>

        <Row gutter={24}>

          <Col span={8}>
            <Card className="module-card">
              <h3>01. Discovery & Ingestion</h3>
              <p>
                Autonomous Profile Harvesting thorugh Secure and Trusted Platforms.
              </p>
              
            </Card>
          </Col>

          <Col span={8}>
            <Card className="module-card">
              <h3>02. Gap Analysis</h3>
              <p>
                Deep semantic cross-referencing between Resume
                Vectors and Job Descriptions.
              </p>
              
            </Card>
          </Col>

          <Col span={8}>
            <Card className="module-card">
              <h3>03. Agentic Interview</h3>
              <p>
                RAG-powered technical evaluation with real-time
                scoring and reasoning.
              </p>

            </Card>
          </Col>

        </Row>

      </section>


      {/* FOOTER */}
      <footer className="footer">

        

        

        <a href="">GitHub</a>

      </footer>

    </div>
  );
}