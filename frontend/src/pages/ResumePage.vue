<template>
  <div class="resume-page">
    <!-- HEADER -->
    <div class="page-header">
      <h1>📄 Resume Screening & Ranking</h1>
      <p>Upload, parse, and rank resumes with peer comparison</p>
    </div>

    <!-- MAIN CONTAINER -->
    <div class="main-container">
      <!-- LEFT SIDEBAR - UPLOAD & JD -->
      <div class="sidebar">
        <!-- JOB DESCRIPTION SECTION -->
        <div class="card jd-card">
          <div class="card-header">
            <h3>📋 Job Description</h3>
            <button 
              v-if="jobDescription" 
              class="btn-icon-small" 
              @click="clearJD"
              title="Clear JD"
            >
              ✕
            </button>
          </div>
          <textarea 
            v-model="jobDescription"
            placeholder="Paste job description here for skill matching..."
            class="jd-input"
            @input="onJDChange"
          ></textarea>
          <div class="jd-info">{{ jobDescription.length }} characters</div>
          
          <!-- RE-ANALYZE BUTTON -->
          <button 
            v-if="parsedResumes.length && jobDescription && jdChanged"
            class="btn-primary btn-full"
            @click="reAnalyzeAll"
            :disabled="parsing"
          >
            🔄 Re-Analyze All Resumes
          </button>
        </div>

        <!-- FILE UPLOAD SECTION -->
        <div class="card upload-card">
          <div class="card-header">
            <h3>📁 Upload Resumes</h3>
          </div>
          
          <div
            class="drop-zone"
            @drop="handleDrop"
            @dragover.prevent
            @dragenter.prevent
          >
            <div class="drop-icon">📥</div>
            <p>Drag PDFs here or click to select</p>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf"
              style="display: none"
              @change="handleFileSelect"
            />
            <button class="btn-light" @click="$refs.fileInput.click()">
              Choose Files
            </button>
          </div>

          <!-- SELECTED FILES PREVIEW -->
          <div v-if="selectedFiles.length" class="selected-files">
            <p class="files-count">{{ selectedFiles.length }} file(s) selected</p>
            <div class="file-list">
              <div v-for="(file, i) in selectedFiles" :key="i" class="file-item">
                <span>📄 {{ file.name }}</span>
                <button class="btn-remove" @click="removeFile(i)">✕</button>
              </div>
            </div>
          </div>

          <!-- UPLOAD BUTTON -->
          <button
            class="btn-primary btn-full"
            @click="uploadAndParse"
            :disabled="!selectedFiles.length || parsing"
          >
            <span v-if="!parsing">⬆️ Upload & Parse</span>
            <span v-else>⏳ Parsing ({{ currentProgress }}/{{ selectedFiles.length }})</span>
          </button>
        </div>

        <!-- EXPORT SECTION -->
        <div v-if="parsedResumes.length" class="card export-card">
          <div class="card-header">
            <h3>💾 Export</h3>
          </div>
          <button class="btn-light btn-full" @click="downloadReport">
            📊 JSON Report
          </button>
          <button class="btn-light btn-full" @click="downloadCSV">
            📈 CSV Export
          </button>
        </div>
      </div>

      <!-- RIGHT CONTENT - RESUMES LIST & DETAIL -->
      <div class="content">
        <!-- STATS HEADER -->
        <div v-if="parsedResumes.length" class="stats-header">
          <div class="stat-box">
            <div class="stat-number">{{ parsedResumes.length }}</div>
            <div class="stat-label">Total Candidates</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ topResume?.name?.split(' ')[0] || 'N/A' }}</div>
            <div class="stat-label">Top Candidate</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ topResume?.experience_years || 0 }}y</div>
            <div class="stat-label">Best Experience</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ topResume?.skills.length || 0 }}</div>
            <div class="stat-label">Top Skills</div>
          </div>
        </div>

        <!-- EMPTY STATE -->
        <div v-if="!parsedResumes.length" class="empty-state">
          <div class="empty-icon">📋</div>
          <h2>No Resumes Yet</h2>
          <p>Upload PDF resumes from the sidebar to get started</p>
        </div>

        <!-- RESUMES LIST -->
        <div v-else class="resumes-list">
          <div class="list-header">
            <h2>Ranked Candidates ({{ parsedResumes.length }})</h2>
            <div class="view-toggle">
              <button 
                :class="['toggle-btn', { active: viewMode === 'list' }]"
                @click="viewMode = 'list'"
              >
                ☰ List
              </button>
              <button 
                :class="['toggle-btn', { active: viewMode === 'grid' }]"
                @click="viewMode = 'grid'"
              >
                ⊞ Grid
              </button>
            </div>
          </div>

          <!-- LIST VIEW -->
          <div v-if="viewMode === 'list'" class="rankings-list">
            <div
              v-for="(resume, i) in sortedResumes"
              :key="resume.name"
              class="ranking-card"
              @click="viewDetailedAnalysis(resume)"
            >
              <div class="ranking-rank">#{{ i + 1 }}</div>
              <div class="ranking-content">
                <h4 class="ranking-name">{{ resume.name }}</h4>
                <div class="ranking-quick-info">
                  <span class="quick-badge">{{ resume.experience_years }}y</span>
                  <span class="quick-badge">{{ resume.skills.length }}sk</span>
                  <span v-if="getPercentile(resume.name) >= 75" class="quick-badge green">
                    ⭐ Top {{ 100 - getPercentile(resume.name) }}%
                  </span>
                  <span v-else-if="getPercentile(resume.name) >= 50" class="quick-badge blue">
                    ⬆️ Top Half
                  </span>
                  <span v-else class="quick-badge grey">
                    Bottom Half
                  </span>
                </div>
              </div>
              <div class="ranking-percentile">
                <div class="percentile-value">{{ getPercentile(resume.name) }}</div>
                <div class="percentile-label">%ile</div>
              </div>
              <div class="ranking-actions">
                <button 
                  class="btn-icon"
                  @click.stop="removeResume(i)"
                  title="Remove resume"
                >
                  🗑️
                </button>
              </div>
              <div class="expand-icon">→</div>
            </div>
          </div>

          <!-- GRID VIEW -->
          <div v-else class="rankings-grid">
            <div
              v-for="(resume, i) in sortedResumes"
              :key="resume.name"
              class="ranking-card-grid"
              @click="viewDetailedAnalysis(resume)"
            >
              <div class="card-rank">#{{ i + 1 }}</div>
              <div class="card-name">{{ resume.name }}</div>
              <div class="card-percentile">{{ getPercentile(resume.name) }}%ile</div>
              <div class="card-stats">
                <span>{{ resume.experience_years }}y</span>
                <span>{{ resume.skills.length }}sk</span>
              </div>
              <button 
                class="btn-remove-card"
                @click.stop="removeResume(i)"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- DETAIL MODAL -->
    <div v-if="selectedResume" class="detail-modal-overlay" @click="closeDetail">
      <div class="detail-modal" @click.stop>
        <!-- Modal Header -->
        <div class="modal-header">
          <div class="modal-title-section">
            <h2>{{ selectedResume.name }}</h2>
            <p class="modal-subtitle">
              Rank: #{{ getRank(selectedResume.name) }} of {{ parsedResumes.length }} 
              | {{ selectedResume.experience_years }} years exp 
              | {{ selectedResume.skills.length }} skills
            </p>
          </div>
          <div class="modal-score-display">
            <div class="score-circle">{{ getPercentile(selectedResume.name) }}<span class="percentile-mark">%</span></div>
            <span class="score-label">Peer Percentile</span>
          </div>
          <button class="btn-close-modal" @click="closeDetail">✕</button>
        </div>

        <!-- Modal Body -->
        <div class="modal-body">
          <!-- QUICK STATS -->
          <div class="report-section">
            <h3 class="report-section-title">📊 Quick Stats</h3>
            <div class="quick-stats-grid">
              <div class="stat-item">
                <span class="stat-label">Experience</span>
                <span class="stat-value">{{ selectedResume.experience_years }}y</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Skills</span>
                <span class="stat-value">{{ selectedResume.skills.length }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">JD Match</span>
                <span class="stat-value">{{ selectedResume.relevance_score }}%</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Quality</span>
                <span class="stat-value">{{ selectedResume.quality_check.score }}/10</span>
              </div>
            </div>
          </div>

          <!-- CONTACT INFO -->
          <div class="report-section">
            <h3 class="report-section-title">📞 Contact</h3>
            <div class="contact-grid">
              <div v-if="selectedResume.contact.email" class="contact-item">
                <span class="contact-icon">📧</span>
                <div>
                  <span class="contact-label">Email</span>
                  <a :href="`mailto:${selectedResume.contact.email[0]}`">{{ selectedResume.contact.email[0] }}</a>
                </div>
              </div>
              <div v-if="selectedResume.contact.phone" class="contact-item">
                <span class="contact-icon">☎️</span>
                <div>
                  <span class="contact-label">Phone</span>
                  <span>{{ selectedResume.contact.phone[0] }}</span>
                </div>
              </div>
              <div v-if="selectedResume.contact.linkedin" class="contact-item">
                <span class="contact-icon">💼</span>
                <div>
                  <span class="contact-label">LinkedIn</span>
                  <a :href="'https://' + selectedResume.contact.linkedin[0]" target="_blank">View →</a>
                </div>
              </div>
              <div v-if="selectedResume.contact.github" class="contact-item">
                <span class="contact-icon">🔗</span>
                <div>
                  <span class="contact-label">GitHub</span>
                  <a :href="'https://' + selectedResume.contact.github[0]" target="_blank">View →</a>
                </div>
              </div>
            </div>
          </div>

          <!-- MATCHING POINTS -->
          <div class="report-section">
            <h3 class="report-section-title">✅ Strengths (vs JD)</h3>
            <div v-if="selectedResume.plus_points?.length" class="points-list">
              <div v-for="(point, i) in selectedResume.plus_points" :key="`plus-${i}`" class="point-item green">
                {{ point }}
              </div>
            </div>
            <div v-else class="empty-message">No JD provided</div>
          </div>

          <!-- WEAKNESSES -->
          <div class="report-section">
            <h3 class="report-section-title">⚠️ Gaps (vs JD)</h3>
            <div v-if="selectedResume.flaws?.length" class="points-list">
              <div v-for="(flaw, i) in selectedResume.flaws" :key="`flaw-${i}`" class="point-item red">
                {{ flaw }}
              </div>
            </div>
            <div v-else class="empty-message">No JD provided</div>
          </div>

          <!-- SKILLS -->
          <div class="report-section">
            <h3 class="report-section-title">💡 Technical Skills ({{ selectedResume.skills.length }})</h3>
            <div class="skills-cloud">
              <span v-for="(skill, i) in selectedResume.skills" :key="i" class="skill-tag">
                {{ skill }}
              </span>
            </div>
          </div>

          <!-- WORK EXPERIENCE -->
          <div class="report-section">
            <h3 class="report-section-title">💼 Work Experience</h3>
            <div class="experience-summary">
              <div class="exp-stat">
                <span class="exp-label">Total Positions</span>
                <span class="exp-value">{{ selectedResume.experience.length }}</span>
              </div>
              <div class="exp-stat">
                <span class="exp-label">Total Years</span>
                <span class="exp-value">{{ selectedResume.experience_years }}</span>
              </div>
            </div>
            <div v-if="selectedResume.experience.length" class="experience-timeline">
              <div v-for="(job, i) in selectedResume.experience.slice(0, 8)" :key="i" class="exp-item">
                <div class="exp-marker"></div>
                <div class="exp-details">
                  <p class="exp-role">{{ job.position }}</p>
                  <p v-if="job.tenure_years !== null" class="exp-tenure">
                    {{ job.tenure_years }} year{{ job.tenure_years !== 1 ? 's' : '' }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- JOB HOPPING ANALYSIS -->
          <div class="report-section">
            <h3 class="report-section-title">📈 Career Stability</h3>
            <div :class="['hopping-analysis-card', `severity-${selectedResume.job_hopping.severity.toLowerCase()}`]">
              <div class="hopping-badge">
                <span v-if="selectedResume.job_hopping.severity === 'None'" class="badge stable">✅ Stable</span>
                <span v-else-if="selectedResume.job_hopping.severity === 'Low'" class="badge low">⚡ Low Risk</span>
                <span v-else-if="selectedResume.job_hopping.severity === 'Medium'" class="badge medium">⚠️ Medium Risk</span>
                <span v-else-if="selectedResume.job_hopping.severity === 'High'" class="badge high">🚩 High Risk</span>
                <span v-else class="badge critical">⛔ Critical</span>
              </div>
              <div class="hopping-metrics-grid">
                <div class="metric">
                  <span class="metric-label">Positions</span>
                  <span class="metric-value">{{ selectedResume.job_hopping.total_jobs }}</span>
                </div>
                <div class="metric">
                  <span class="metric-label">Under 1yr</span>
                  <span class="metric-value">{{ selectedResume.job_hopping.short_tenure_count }}</span>
                </div>
                <div class="metric">
                  <span class="metric-label">Ratio</span>
                  <span class="metric-value">{{ selectedResume.job_hopping.hopping_ratio }}%</span>
                </div>
                <div class="metric">
                  <span class="metric-label">Avg</span>
                  <span class="metric-value">{{ selectedResume.job_hopping.avg_tenure_months }}mo</span>
                </div>
              </div>
              <p class="hopping-assessment">{{ selectedResume.job_hopping.stability_assessment }}</p>
            </div>
          </div>

          <!-- RED FLAGS -->
          <div v-if="selectedResume.red_flags?.length" class="report-section">
            <h3 class="report-section-title">🚩 Red Flags</h3>
            <div class="red-flags-list">
              <div v-for="(flag, i) in selectedResume.red_flags" :key="i" class="red-flag-item">
                {{ flag }}
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button class="btn-light" @click="closeDetail">Close</button>
          <button class="btn-primary" @click="downloadResumePDF">📥 Download Report</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { api } from 'boot/axios'

// STATE
const jobDescription = ref('')
const jobDescriptionOriginal = ref('')
const jdChanged = ref(false)
const selectedFiles = ref([])
const parsedResumes = ref([])
const selectedResume = ref(null)
const parsing = ref(false)
const currentProgress = ref(0)
const fileInput = ref(null)
const viewMode = ref('list')

// COMPUTED
const sortedResumes = computed(() => {
  return [...parsedResumes.value].sort((a, b) => calculateScore(b) - calculateScore(a))
})

const topResume = computed(() => sortedResumes.value[0] || null)

// FUNCTIONS - FILE HANDLING
function handleFileSelect(event) {
  selectedFiles.value = Array.from(event.target.files)
}

function handleDrop(event) {
  event.preventDefault()
  selectedFiles.value = Array.from(event.dataTransfer.files).filter(f => f.type === 'application/pdf')
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

// FUNCTIONS - JOB DESCRIPTION
function onJDChange() {
  jdChanged.value = jobDescription.value !== jobDescriptionOriginal.value
}

function clearJD() {
  jobDescription.value = ''
  jobDescriptionOriginal.value = ''
  jdChanged.value = false
}

// FUNCTIONS - RESUME MANAGEMENT
function removeResume(index) {
  if (confirm(`Remove ${sortedResumes.value[index].name}?`)) {
    const nameToRemove = sortedResumes.value[index].name
    parsedResumes.value = parsedResumes.value.filter(r => r.name !== nameToRemove)
  }
}

// FUNCTIONS - SCORING & RANKING
function calculateScore(resume) {
  const expScore = Math.min(resume.experience_years * 3, 30)
  const skillScore = Math.min(resume.skills.length * 2, 20)
  const relevanceScore = (resume.relevance_score || 0) / 10
  const qualityScore = resume.quality_check.score * 1

  let total = expScore + skillScore + relevanceScore + qualityScore

  total -= (resume.red_flags?.length || 0) * 3
  const hoppingPenalty = resume.job_hopping?.score || 0
  total -= hoppingPenalty * 0.15

  return Math.round(Math.min(Math.max(total, 0), 100))
}

function getPercentile(resumeName) {
  if (!sortedResumes.value || sortedResumes.value.length === 0) return 0
  
  const position = sortedResumes.value.findIndex(r => r.name === resumeName)
  if (position === -1) return 0
  
  return Math.round(((sortedResumes.value.length - position) / sortedResumes.value.length) * 100)
}

function getRank(resumeName) {
  if (!sortedResumes.value) return 'N/A'
  const index = sortedResumes.value.findIndex(r => r.name === resumeName)
  return index !== -1 ? index + 1 : 'N/A'
}

// FUNCTIONS - MODAL
function viewDetailedAnalysis(resume) {
  selectedResume.value = resume
}

function closeDetail() {
  selectedResume.value = null
}

// FUNCTIONS - API CALLS
async function uploadAndParse() {
  if (!selectedFiles.value.length) return

  parsing.value = true
  currentProgress.value = 0
  
  try {
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('files', file)
    })
    if (jobDescription.value) {
      formData.append('job_description', jobDescription.value)
    }

    const res = await api.post('/api/resumes/parse-batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    // ADD NEW RESUMES TO EXISTING ONES
    parsedResumes.value.push(...(res.data.resumes || []))
    
    // UPDATE JD ORIGIN AFTER SUCCESSFUL PARSE
    jobDescriptionOriginal.value = jobDescription.value
    jdChanged.value = false
    
    if (res.data.errors?.length) {
      console.warn('Parse errors:', res.data.errors)
      alert(`Processed ${res.data.count} resumes with ${res.data.errors.length} errors`)
    }
    
    selectedFiles.value = []
    fileInput.value.value = ''
  } catch (err) {
    console.error(err)
    alert('Failed to parse resumes: ' + (err.response?.data?.error || err.message))
  } finally {
    parsing.value = false
    currentProgress.value = 0
  }
}

async function reAnalyzeAll() {
  if (!parsedResumes.value.length || !jobDescription.value) return

  parsing.value = true
  
  try {
    // Call re-analyze endpoint for each resume
    const reanalyzedResumes = await Promise.all(
      parsedResumes.value.map(resume => 
        api.post('/api/resumes/analyze', {
          resume: resume,
          job_description: jobDescription.value,
          all_resumes: parsedResumes.value
        })
      )
    )

    // Update parsed resumes with re-analyzed data
    parsedResumes.value = reanalyzedResumes.map(res => res.data.resume || res.data)

    // Update JD origin
    jobDescriptionOriginal.value = jobDescription.value
    jdChanged.value = false

    alert('✅ Re-analysis complete!')
  } catch (err) {
    console.error(err)
    alert('Failed to re-analyze: ' + (err.response?.data?.error || err.message))
  } finally {
    parsing.value = false
  }
}

// FUNCTIONS - EXPORT
function downloadReport() {
  if (!parsedResumes.value.length) return

  const report = {
    export_date: new Date().toISOString(),
    total_resumes: parsedResumes.value.length,
    job_description: jobDescription.value.substring(0, 300),
    ranked_resumes: sortedResumes.value.map((resume, i) => ({
      rank: i + 1,
      name: resume.name,
      percentile: getPercentile(resume.name),
      experience_years: resume.experience_years,
      skills_count: resume.skills.length,
      contact: resume.contact,
      job_hopping: resume.job_hopping,
      plus_points: resume.plus_points || [],
      flaws: resume.flaws || []
    }))
  }

  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `resume_ranking_report_${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function downloadCSV() {
  if (!parsedResumes.value.length) return

  const headers = ['Rank', 'Name', 'Percentile', 'Experience (yrs)', 'Skills Count', 'Email', 'JD Match %', 'Red Flags', 'Career Stability']
  const rows = sortedResumes.value.map((resume, i) => [
    i + 1,
    resume.name,
    getPercentile(resume.name),
    resume.experience_years,
    resume.skills.length,
    resume.contact.email?.[0] || 'N/A',
    resume.relevance_score || 0,
    resume.red_flags.length,
    resume.job_hopping.severity || 'Stable'
  ])

  const csvContent = [headers, ...rows]
    .map(row => row.map(cell => `"${cell}"`).join(','))
    .join('\r\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `resume_rankings_${Date.now()}.csv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function downloadResumePDF() {
  if (!selectedResume.value) return
  
  const reportData = {
    name: selectedResume.value.name,
    rank: getRank(selectedResume.value.name),
    percentile: getPercentile(selectedResume.value.name),
    timestamp: new Date().toLocaleString(),
    analysis: {
      experience_years: selectedResume.value.experience_years,
      skills_count: selectedResume.value.skills.length,
      jd_match: selectedResume.value.relevance_score,
      stability: selectedResume.value.job_hopping.severity,
      plus_points: selectedResume.value.plus_points,
      flaws: selectedResume.value.flaws
    }
  }
  
  const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${selectedResume.value.name}_analysis_${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.resume-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%);
  padding: 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 32px;
  margin: 0;
  color: #003B7F;
  font-weight: 700;
}

.page-header p {
  color: #6B7280;
  margin: 8px 0 0 0;
}

.main-container {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

/* SIDEBAR */
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #E5E7EB;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  color: #1F2937;
  font-weight: 600;
}

.btn-icon-small {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-icon-small:hover {
  background: #F3F4F6;
}

/* JD SECTION */
.jd-input {
  width: 100%;
  min-height: 150px;
  padding: 12px;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  margin-bottom: 10px;
}

.jd-input:focus {
  outline: none;
  border-color: #0099D8;
  box-shadow: 0 0 0 3px rgba(0, 153, 216, 0.1);
}

.jd-info {
  font-size: 12px;
  color: #9CA3AF;
  margin-bottom: 12px;
}

/* DROP ZONE */
.drop-zone {
  border: 2px dashed #D1D5DB;
  border-radius: 8px;
  padding: 30px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #F9FAFB;
  margin-bottom: 15px;
}

.drop-zone:hover {
  border-color: #0099D8;
  background: #EFF8FF;
}

.drop-icon {
  font-size: 40px;
  margin-bottom: 10px;
}

.drop-zone p {
  margin: 10px 0;
  font-size: 14px;
  color: #6B7280;
}

/* SELECTED FILES */
.selected-files {
  margin-bottom: 15px;
  padding: 12px;
  background: #F3F4F6;
  border-radius: 8px;
}

.files-count {
  font-size: 12px;
  color: #6B7280;
  margin: 0 0 10px 0;
  font-weight: 500;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  background: white;
  padding: 8px 10px;
  border-radius: 6px;
  border-left: 3px solid #0099D8;
}

.btn-remove {
  background: none;
  border: none;
  color: #EF4444;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
}

.btn-remove:hover {
  background: #FEE2E2;
  border-radius: 4px;
}

/* BUTTONS */
.btn-primary,
.btn-light {
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(135deg, #003B7F, #0099D8);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 153, 216, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-light {
  background: #F3F4F6;
  color: #1F2937;
  border: 1px solid #D1D5DB;
}

.btn-light:hover {
  background: #E5E7EB;
}

.btn-full {
  width: 100%;
}

/* STATS */
.stats-header {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat-box {
  background: white;
  padding: 16px;
  border-radius: 10px;
  text-align: center;
  border-left: 4px solid #0099D8;
}

.stat-number {
  font-size: 24px;
  font-weight: 700;
  color: #003B7F;
  display: block;
}

.stat-label {
  font-size: 12px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-top: 4px;
}

/* LIST VIEW */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.list-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1F2937;
}

.view-toggle {
  display: flex;
  gap: 8px;
}

.toggle-btn {
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.toggle-btn.active {
  background: #0099D8;
  color: white;
  border-color: #0099D8;
}

.rankings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ranking-card {
  background: white;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 15px;
  cursor: pointer;
  transition: all 0.3s;
}

.ranking-card:hover {
  border-color: #0099D8;
  box-shadow: 0 4px 12px rgba(0, 153, 216, 0.15);
  transform: translateY(-2px);
}

.ranking-rank {
  font-size: 18px;
  font-weight: 700;
  color: #0099D8;
  min-width: 40px;
  text-align: center;
}

.ranking-content {
  flex: 1;
}

.ranking-name {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1F2937;
}

.ranking-quick-info {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.quick-badge {
  background: #F3F4F6;
  color: #6B7280;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.quick-badge.green {
  background: #D1FAE5;
  color: #065F46;
}

.quick-badge.blue {
  background: #DBEAFE;
  color: #1E40AF;
}

.quick-badge.grey {
  background: #F3F4F6;
  color: #6B7280;
}

.ranking-percentile {
  text-align: center;
  min-width: 60px;
  padding: 8px 12px;
  background: #F0F9FF;
  border-radius: 8px;
}

.percentile-value {
  font-size: 18px;
  font-weight: 700;
  color: #0099D8;
}

.percentile-label {
  font-size: 10px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ranking-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: #FEE2E2;
}

.expand-icon {
  font-size: 18px;
  color: #D1D5DB;
}

/* GRID VIEW */
.rankings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 15px;
}

.ranking-card-grid {
  background: white;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}

.ranking-card-grid:hover {
  border-color: #0099D8;
  box-shadow: 0 4px 12px rgba(0, 153, 216, 0.15);
  transform: translateY(-2px);
}

.card-rank {
  font-size: 16px;
  font-weight: 700;
  color: #0099D8;
  margin-bottom: 8px;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 12px;
  word-break: break-word;
}

.card-percentile {
  font-size: 18px;
  font-weight: 700;
  color: #003B7F;
  margin-bottom: 12px;
}

.card-stats {
  display: flex;
  justify-content: center;
  gap: 12px;
  font-size: 12px;
  color: #6B7280;
}

.btn-remove-card {
  position: absolute;
  top: 8px;
  right: 8px;
  background: #FEE2E2;
  border: none;
  color: #DC2626;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-remove-card:hover {
  background: #FCA5A5;
  color: white;
}

/* MODAL */
.detail-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.detail-modal {
  background: white;
  border-radius: 16px;
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  border-bottom: 1px solid #E5E7EB;
}

.modal-title-section h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #1F2937;
}

.modal-subtitle {
  margin: 0;
  font-size: 13px;
  color: #6B7280;
}

.modal-score-display {
  text-align: center;
}

.score-circle {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  background: linear-gradient(135deg, #003B7F, #0099D8);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 28px;
  margin-bottom: 8px;
}

.percentile-mark {
  font-size: 18px;
}

.score-label {
  font-size: 11px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
}

.btn-close-modal {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6B7280;
  padding: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
}

.btn-close-modal:hover {
  background: #F3F4F6;
  color: #1F2937;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.report-section {
  margin-bottom: 24px;
}

.report-section-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2937;
}

.quick-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.stat-item {
  background: #F9FAFB;
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid #0099D8;
}

.stat-label {
  font-size: 11px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #003B7F;
  display: block;
}

.contact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.contact-item {
  background: #F9FAFB;
  padding: 12px;
  border-radius: 8px;
  display: flex;
  gap: 12px;
}

.contact-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.contact-label {
  font-size: 11px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 4px;
}

.contact-item a {
  font-size: 13px;
  color: #0099D8;
  text-decoration: none;
  word-break: break-all;
}

.contact-item a:hover {
  text-decoration: underline;
}

.points-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.point-item {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  border-left: 3px solid;
}

.point-item.green {
  background: #D1FAE5;
  border-color: #10B981;
  color: #065F46;
}

.point-item.red {
  background: #FEE2E2;
  border-color: #EF4444;
  color: #991B1B;
}

.empty-message {
  padding: 16px;
  text-align: center;
  color: #9CA3AF;
  font-size: 13px;
  background: #F9FAFB;
  border-radius: 6px;
}

.skills-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag {
  background: linear-gradient(135deg, #EFF8FF, #DBEAFE);
  color: #0099D8;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid #BFDBFE;
}

.experience-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.exp-stat {
  background: #F9FAFB;
  padding: 12px;
  border-radius: 8px;
}

.exp-label {
  font-size: 11px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 4px;
}

.exp-value {
  font-size: 18px;
  font-weight: 700;
  color: #003B7F;
  display: block;
}

.experience-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exp-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: #F9FAFB;
  border-radius: 8px;
  border-left: 3px solid #0099D8;
}

.exp-marker {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #0099D8;
  flex-shrink: 0;
  margin-top: 4px;
}

.exp-details {
  flex: 1;
}

.exp-role {
  margin: 0 0 4px 0;
  font-size: 13px;
  font-weight: 500;
  color: #1F2937;
}

.exp-tenure {
  margin: 0;
  font-size: 12px;
  color: #6B7280;
}

.hopping-analysis-card {
  background: #F9FAFB;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #10B981;
}

.hopping-analysis-card.severity-critical {
  border-color: #DC2626;
  background: #FEF2F2;
}

.hopping-analysis-card.severity-high {
  border-color: #F97316;
  background: #FFFBEB;
}

.hopping-analysis-card.severity-medium {
  border-color: #EAB308;
  background: #FFFBEB;
}

.hopping-analysis-card.severity-low {
  border-color: #06B6D4;
  background: #ECFDFD;
}

.hopping-badge {
  margin-bottom: 12px;
}

.badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.badge.stable {
  background: #D1FAE5;
  color: #065F46;
}

.badge.low {
  background: #ECFDFD;
  color: #164E63;
}

.badge.medium {
  background: #FEF3C7;
  color: #92400E;
}

.badge.high {
  background: #FEED7D;
  color: #CA8A04;
}

.badge.critical {
  background: #FCA5A5;
  color: #7F1D1D;
}

.hopping-metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.metric {
  text-align: center;
}

.metric-label {
  font-size: 11px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: #003B7F;
  display: block;
}

.hopping-assessment {
  margin: 0;
  font-size: 12px;
  color: #6B7280;
  font-style: italic;
}

.red-flags-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.red-flag-item {
  background: #FEE2E2;
  border-left: 3px solid #DC2626;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: #991B1B;
}

.modal-footer {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #E5E7EB;
}

.modal-footer .btn-light,
.modal-footer .btn-primary {
  flex: 1;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #6B7280;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h2 {
  margin: 0 0 8px 0;
  color: #1F2937;
}

.empty-state p {
  margin: 0;
}

/* RESPONSIVE */
@media (max-width: 1024px) {
  .main-container {
    grid-template-columns: 1fr;
  }
  
  .sidebar {
    position: sticky;
    top: 20px;
    z-index: 100;
  }
  
  .hopping-metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header h1 {
    font-size: 24px;
  }
  
  .stats-header {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .ranking-card {
    flex-direction: column;
    text-align: center;
  }
  
  .ranking-content {
    flex: auto;
  }
  
  .rankings-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  }
  
  .modal-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .quick-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .hopping-metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>