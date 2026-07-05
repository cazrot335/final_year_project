import { useEffect, useRef, useState } from "react"
// import ReactQuill from "react-quill"

// import "react-quill/dist/quill.snow.css"

import ProfileSelectCard from "../components/ProfileSelectCard"
import GapResult from "../components/GapResult"

import "../styles/GapAnalysis.css"
import JDEditor from "../components/JDEditor"

export default function GapAnalysis(){

  const [profiles,setProfiles] = useState([])
  const [selectedProfile,setSelectedProfile] = useState(null)

  const [jd,setJd] = useState("")
  const [result,setResult] = useState(null)
  const [loading,setLoading] = useState(false)
  const resultRef = useRef(null)

  // scroll result into view whenever it appears
  useEffect(()=>{
    if(result && resultRef.current){
      resultRef.current.scrollIntoView({ behavior:"smooth", block:"start" })
    }
  },[result])

  useEffect(()=>{

    fetch("http://localhost:5000/api/profiles/analyzed")
      .then(res=>res.json())
      .then(data=>setProfiles(data))

  },[])


  const runAnalysis = async ()=>{

    if(!selectedProfile) return

    setLoading(true)

    try{

      const res = await fetch(
        "http://localhost:5000/api/pipeline/gap-analysis",
        {
          method:"POST",
          headers:{ "Content-Type":"application/json" },
          body:JSON.stringify({
            profile_id:selectedProfile.id,
            jd:jd
          })
        }
      )

      const data = await res.json()

      setResult(data)

    }catch(err){
      console.error(err)
    }

    setLoading(false)

  }


  return(

    <div className="gap-page">

      {/* LEFT PANEL */}

      <div className="gap-left">

        <h2>Job Description</h2>

       <JDEditor
  value={jd}
  onChange={setJd}
/>

        <button
          className="run-btn"
          onClick={runAnalysis}
          disabled={loading}
        >

          {loading ? "Analyzing..." : "Run Gap Analysis"}

        </button>

      </div>


      {/* RIGHT PANEL — candidate selection only */}

      <div className="gap-right">

        <h3>Select Candidate</h3>

        <div className="profile-grid">

          {profiles.map(p=>(

            <ProfileSelectCard
              key={p.id}
              profile={p}
              selected={selectedProfile?.id === p.id}
              onSelect={setSelectedProfile}
            />

          ))}

        </div>

      </div>

      {/* RESULT PANEL — full width below both panels */}
      {result && (
        <div className="gap-result-panel" ref={resultRef}>
          <GapResult result={result}/>
        </div>
      )}

    </div>

  )

}