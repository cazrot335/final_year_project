import { useState } from "react";
import "../styles/ProfileCard.css";

export default function ProfileCard({ profile, onSynced }) {

  const [syncing, setSyncing]     = useState(false);
  const [syncedAt, setSyncedAt]   = useState(profile.synced_at || null);
  const [syncError, setSyncError] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalData, setModalData] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);

  /* ── Sync ── */
  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    try {
      const res  = await fetch(`http://localhost:5000/api/profiles/${profile.id}/sync`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Sync failed");
      setSyncedAt(data.synced_at);
      if (onSynced) onSynced(profile.id, data);
    } catch (err) {
      setSyncError(err.message);
    }
    setSyncing(false);
  };

  /* ── View Profile modal ── */
  const openProfile = async () => {
    setModalOpen(true);
    if (modalData) return;           // already loaded
    setModalLoading(true);
    try {
      const res  = await fetch(`http://localhost:5000/api/profiles/${profile.id}/data`);
      const data = await res.json();
      setModalData(data);
    } catch {
      setModalData({ error: "Failed to load profile data." });
    }
    setModalLoading(false);
  };

  const formatDate = (iso) => {
    if (!iso) return null;
    return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  };

  /* ── helpers for nested data ── */
  const normalizeSkills = (skills) =>
    skills.map((s) => (typeof s === "string" ? s : s.name || s.skill || "")).filter(Boolean);

  const normalizeExp = (exp) =>
    exp.map((e) => ({
      company:  e.company_name || e.company || "",
      role:     e.job_title    || e.role    || "",
      duration: `${e.start_date || ""} – ${e.end_date || ""}`.replace(/^ – $/, ""),
    }));

  const normalizeEdu = (edu) =>
    edu.map((e) => ({
      institution: e.university_name || e.institution || "",
      degree:      e.degree || "",
      years:       `${e.start_date || ""} – ${e.end_date || ""}`.replace(/^ – $/, ""),
    }));

  return (
    <>
      {/* ── CARD ── */}
      <div className="profile-card">
        <h3>{profile?.name || "Unknown Candidate"}</h3>
        <p className="designation">{profile?.designation}</p>
        <p className="snippet">{profile?.snippet}</p>

        {syncedAt && <p className="last-synced">Last synced: {formatDate(syncedAt)}</p>}
        {syncError && <p className="sync-error">{syncError}</p>}

        <div className="card-actions">
          <button className="view-btn" onClick={openProfile}>View Profile</button>
          <button className="sync-btn" onClick={handleSync} disabled={syncing}>
            {syncing ? "Syncing..." : "⟳ Sync"}
          </button>
        </div>
      </div>

      {/* ── MODAL ── */}
      {modalOpen && (
        <div className="profile-overlay" onClick={() => setModalOpen(false)}>
          <div className="profile-modal" onClick={(e) => e.stopPropagation()}>

            <button className="modal-close" onClick={() => setModalOpen(false)}>✕</button>

            {modalLoading && <p className="modal-loading">Loading...</p>}

            {!modalLoading && modalData?.error && (
              <p className="sync-error">{modalData.error}</p>
            )}

            {!modalLoading && modalData && !modalData.error && (
              <>
                <div className="modal-header">
                  <div>
                    <h2>{modalData.name || "Unknown"}</h2>
                    {modalData.headline && <p className="modal-headline">{modalData.headline}</p>}
                  </div>
                  <a
                    href={modalData.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="linkedin-link"
                  >
                    LinkedIn ↗
                  </a>
                </div>

                {!modalData.synced && (
                  <div className="not-synced-banner">
                    Profile not yet synced — click Sync on the card to pull full data from LinkedIn.
                  </div>
                )}

                {modalData.synced && (
                  <>
                    {/* Score bar */}
                    <div className="score-row">
                      <span className="score-label">Profile Score</span>
                      <span className="score-value">{modalData.biometric_score ?? "—"}</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${modalData.biometric_score || 0}%` }} />
                    </div>

                    {/* Skills */}
                    {normalizeSkills(modalData.skills || []).length > 0 && (
                      <div className="modal-section">
                        <strong>Skills</strong>
                        <div className="skills-wrap">
                          {normalizeSkills(modalData.skills).map((s, i) => (
                            <span key={i} className="skill-tag">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Experience */}
                    {normalizeExp(modalData.experience || []).length > 0 && (
                      <div className="modal-section">
                        <strong>Experience</strong>
                        {normalizeExp(modalData.experience).map((e, i) => (
                          <div key={i} className="timeline-item">
                            <span className="tl-role">{e.role}</span>
                            <span className="tl-company">{e.company}</span>
                            {e.duration && <span className="tl-duration">{e.duration}</span>}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Education */}
                    {normalizeEdu(modalData.education || []).length > 0 && (
                      <div className="modal-section">
                        <strong>Education</strong>
                        {normalizeEdu(modalData.education).map((e, i) => (
                          <div key={i} className="timeline-item">
                            <span className="tl-role">{e.degree}</span>
                            <span className="tl-company">{e.institution}</span>
                            {e.years && <span className="tl-duration">{e.years}</span>}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* AI Feedback */}
                    {modalData.ai_feedback && (
                      <div className="modal-section">
                        <strong>AI Feedback</strong>
                        <p className="ai-feedback">{modalData.ai_feedback}</p>
                      </div>
                    )}

                    {modalData.synced_at && (
                      <p className="last-synced">Last synced: {formatDate(modalData.synced_at)}</p>
                    )}
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
