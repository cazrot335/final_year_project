import { useEffect, useRef } from "react"
import Quill from "quill"
import "../styles/JDEditor.css"
import "quill/dist/quill.snow.css"

export default function JDEditor({ value, onChange }) {

  const editorRef = useRef(null)
  const quillRef = useRef(null)

  useEffect(()=>{

    if(!quillRef.current){

      quillRef.current = new Quill(editorRef.current,{
        theme:"snow",
        placeholder:"Write or paste Job Description...",
        modules:{
          toolbar:[
            ["bold","italic","underline"],
            [{ list:"ordered" },{ list:"bullet" }],
            ["link"],
            ["clean"]
          ]
        }
      })

      quillRef.current.on("text-change",()=>{

        const html = editorRef.current.querySelector(".ql-editor").innerHTML
        onChange(html)

      })

    }

  },[])

  return(

    <div className="jd-editor-wrapper">
      <div ref={editorRef}/>
    </div>

  )

}