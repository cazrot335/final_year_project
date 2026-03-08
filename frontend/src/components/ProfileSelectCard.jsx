import "../styles/GapAnalysis.css"

export default function ProfileSelectCard({ profile, selected, onSelect }){

  return(

    <div
      className={`profile-select-card ${selected ? "selected" : ""}`}
      onClick={()=>onSelect(profile)}
    >

      <h4>{profile.name}</h4>

      <p>{profile.headline || "No headline available"}</p>

      <a
        href={profile.profile_url}
        target="_blank"
        rel="noreferrer"
      >
        View Profile
      </a>

    </div>

  )

}