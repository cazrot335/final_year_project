import { useState } from "react";
import "../styles/ProfileCard.css";

export default function ProfileCard({ profile }) {

  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [showAnalysis, setShowAnalysis] = useState(false);

  const analyseProfile = async () => {

    // If already analysed → just open modal
    if (analysis) {
      setShowAnalysis(true);
      return;
    }

    setLoading(true);

    try {

      const res = await fetch(
        "http://localhost:5000/api/pipeline/profile-analysis",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            url: profile.profile_url
          })
        }
      );

      const data = await res.json();

      setAnalysis(data);
      setShowAnalysis(true);

    } catch (err) {

      console.error("Analysis error:", err);

    }

    setLoading(false);

  };


  return (

    <>
    
    {/* CARD */}

    <div className="profile-card">

      <h3>{profile?.name || "Unknown Candidate"}</h3>

      <p className="designation">
        {profile?.designation}
      </p>

      <p className="snippet">
        {profile?.snippet}
      </p>

      <div className="card-actions">

        <a
          href={profile?.profile_url}
          target="_blank"
          rel="noreferrer"
        >
          View Profile
        </a>

        <button
          className="analyse-btn"
          onClick={analyseProfile}
          disabled={loading}
        >

          {loading ? "Analysing..." : "Analyse"}

        </button>

      </div>


      {/* AI LABEL AFTER ANALYSIS */}

      {analysis?.candidate_summary && (

        <div
          className="analysis-label"
          onClick={() => setShowAnalysis(true)}
        >

          AI Analysis

          <span className="score-chip">

            {analysis?.candidate_summary?.biometric_score}

          </span>

        </div>

      )}

    </div>



    {/* CENTER MODAL */}

    {analysis?.candidate_summary && showAnalysis && (

      <div className="analysis-overlay">

        <div className="analysis-modal">

          <button
            className="close-btn"
            onClick={() => setShowAnalysis(false)}
          >
            ✕
          </button>


          <h2>
            {analysis?.candidate_summary?.name}
          </h2>

          <p className="headline">
            {analysis?.candidate_summary?.headline}
          </p>


      


          <div className="progress-bar">

            <div
              className="progress-fill"
              style={{
                width:
                  (analysis?.candidate_summary?.biometric_score || 0) + "%"
              }}
            />

          </div>


          {/* QUALIFIED BADGE */}

          {(analysis?.candidate_summary?.biometric_score || 0) > 70 && (

            <div className="badge-pass">
              ✔ High Potential Candidate
            </div>

          )}


          {/* SKILLS */}

          <div className="analysis-section">

            <strong>Skills</strong>

            <div className="skills">

              {analysis?.candidate_summary?.skills?.map((s, i) => (

                <span key={i}>{s}</span>

              ))}

            </div>

          </div>


          {/* AI FEEDBACK */}

          <div className="analysis-section">

            <strong>AI Feedback</strong>

            <p>

              {analysis?.recruiter_notes?.ai_feedback}

            </p>

          </div>

        </div>

      </div>

    )}

    </>

  );

}