import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer
} from "recharts"

import "../styles/GapAnalysis.css"

export default function GapResult({ result }){

  const radarData = [

    { subject:"Skills", value:result.radar_scores.skills },
    { subject:"Experience", value:result.radar_scores.experience },
    { subject:"Domain", value:result.radar_scores.domain },
    { subject:"Education", value:result.radar_scores.education },
    { subject:"Tools", value:result.radar_scores.tools }

  ]

  return(

    <div className="gap-result">

      <div className={`recommend ${result.recommendation.replace(" ","-")}`}>

        {result.recommendation} — Score {result.fit_score}

      </div>


      <div className="radar-box">

        <ResponsiveContainer width="100%" height={280}>

          <RadarChart data={radarData}>

            <PolarGrid />

            <PolarAngleAxis dataKey="subject"/>

            <PolarRadiusAxis domain={[0,10]}/>

            <Radar
              dataKey="value"
              stroke="#4f8cff"
              fill="#4f8cff"
              fillOpacity={0.6}
            />

          </RadarChart>

        </ResponsiveContainer>

      </div>


      <div className="summary">

        <h4>AI Summary</h4>

        <p>{result.summary}</p>

      </div>


      <div className="match-gap">

        <div>

          <h4>Matches</h4>

          <ul>

            {result.matches.map((m,i)=>(
              <li key={i}>✔ {m}</li>
            ))}

          </ul>

        </div>


        <div>

          <h4>Gaps</h4>

          <ul>

            {result.gaps.map((g,i)=>(
              <li key={i}>⚠ {g}</li>
            ))}

          </ul>

        </div>

      </div>

    </div>

  )

}