<template>
  <div class="page-wrapper">
    <!-- NAVIGATION BAR -->
    <div class="navbar">
      <div class="navbar-container">
        <div class="navbar-logo">TalentFlow</div>
        <div class="navbar-menu">
          <a href="#features">Features</a>
          <a href="#process">Process</a>
          <a href="#stats">Statistics</a>
          <a href="#faq">FAQ</a>
        </div>
        <div class="navbar-actions">
          <button class="btn-outline">Sign In</button>
          <button class="btn-solid">Get Started</button>
        </div>
      </div>
    </div>

    <!-- HERO SECTION -->
    <section class="hero-section">
      <div class="hero-container">
        <div class="hero-content">
          <h1 class="hero-title">Discover Top Talent with AI-Powered Recruiting</h1>
          <p class="hero-subtitle">Find, screen, and hire the best candidates faster than ever with our intelligent recruitment platform</p>
          <button class="btn-hero">Start Your Search</button>
        </div>
        <div class="hero-stats">
          <div class="stat-card">
            <div class="stat-number">1.2M+</div>
            <div class="stat-label">Profiles Scraped</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">94%</div>
            <div class="stat-label">Match Accuracy</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">500+</div>
            <div class="stat-label">Companies Trust Us</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">24/7</div>
            <div class="stat-label">Auto Scraping</div>
          </div>
        </div>
      </div>
    </section>

    <!-- SEARCH SECTION (Main Functionality) -->
    <section class="search-section">
      <div class="search-container">
        <div class="search-header">
          <h2>Find Your Next Hire</h2>
          <p>Powerful talent search and filtering tools</p>
        </div>
        
        <div class="search-grid">
          <div class="search-panel">
            <h3 class="panel-title">Search Parameters</h3>
            
            <div class="form-group">
              <label>Job Title / Keyword</label>
              <input v-model="keyword" type="text" placeholder="e.g. Software Engineer, Product Manager" class="form-input" />
            </div>

            <div class="form-group">
              <label>Location</label>
              <input v-model="location" type="text" placeholder="e.g. Bengaluru, San Francisco" class="form-input" />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Pages to Search</label>
                <input v-model.number="pages" type="number" min="1" max="10" class="form-input" />
              </div>
              <div class="form-group checkbox-group">
                <label>
                  <input v-model="withEmail" type="checkbox" />
                  Include Email Leads
                </label>
              </div>
            </div>

            <div class="button-group">
              <button class="btn-primary" @click="scrape" :disabled="loadingScrape || loadingRefresh">
                <span v-if="!loadingScrape">🔍 Quick Scrape</span>
                <span v-else>Searching...</span>
              </button>
              <button class="btn-secondary" @click="refresh" :disabled="loadingScrape || loadingRefresh">
                <span v-if="!loadingRefresh">⚡ Full Refresh</span>
                <span v-else>Refreshing...</span>
              </button>
              <button class="btn-light" @click="loadSaved">📥 Load Saved</button>
            </div>
          </div>

          <div class="results-panel">
            <h3 class="panel-title">Results ({{ profiles.length }} found)</h3>
            
            <div v-if="profiles.length === 0" class="empty-state">
              <div class="empty-icon">📋</div>
              <p>No profiles found. Start by entering a keyword and location, then click "Quick Scrape" or "Full Refresh".</p>
            </div>

            <div v-else class="profiles-list">
              <div v-for="(p, i) in profiles" :key="i" class="profile-card">
                <div class="profile-header">
                  <div class="profile-avatar">{{ (p.name || 'U').charAt(0).toUpperCase() }}</div>
                  <div class="profile-info">
                    <h4 class="profile-name">{{ p.name || p.basic_designation || 'Unknown' }}</h4>
                    <p class="profile-role">{{ p.basic_designation }}</p>
                  </div>
                </div>
                <div class="profile-meta">
                  <span class="meta-tag">{{ p.basic_company }}</span>
                  <span class="meta-tag">{{ p.basic_location }}</span>
                </div>
                <a :href="p.profile_url" target="_blank" class="profile-link">Visit LinkedIn →</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- FEATURES SECTION -->
    <section class="features-section" id="features">
      <div class="features-container">
        <h2 class="section-title">Why TalentFlow is Best</h2>
        <p class="section-subtitle">Everything you need to streamline your hiring process</p>

        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <h4>Intelligent Matching</h4>
            <p>AI-powered matching algorithm finds candidates that perfectly fit your requirements</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <h4>Fast Scraping</h4>
            <p>Collect thousands of profiles in minutes using our optimized scraping engine</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">🔐</div>
            <h4>Data Security</h4>
            <p>Enterprise-grade security ensures all candidate data is protected and compliant</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">📊</div>
            <h4>Advanced Analytics</h4>
            <p>Real-time insights and reporting to track your recruitment funnel</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">🔗</div>
            <h4>Easy Integration</h4>
            <p>Seamlessly integrate with your existing ATS and HR systems</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">🌍</div>
            <h4>Global Coverage</h4>
            <p>Access talent pools from over 190 countries worldwide</p>
          </div>
        </div>
      </div>
    </section>

    <!-- PROCESS SECTION -->
    <section class="process-section" id="process">
      <div class="process-container">
        <h2 class="section-title">How It Works</h2>
        <p class="section-subtitle">Simple 4-step process to find your next great hire</p>

        <div class="process-flow">
          <div class="process-step">
            <div class="step-circle">1</div>
            <h4>Define Criteria</h4>
            <p>Enter job title, skills, and location preferences</p>
          </div>
          <div class="process-arrow">→</div>
          <div class="process-step">
            <div class="step-circle">2</div>
            <h4>Scrape Profiles</h4>
            <p>Our engine searches and collects matching candidates</p>
          </div>
          <div class="process-arrow">→</div>
          <div class="process-step">
            <div class="step-circle">3</div>
            <h4>Review Results</h4>
            <p>View detailed profiles with skills and experience</p>
          </div>
          <div class="process-arrow">→</div>
          <div class="process-step">
            <div class="step-circle">4</div>
            <h4>Connect & Hire</h4>
            <p>Reach out directly through LinkedIn</p>
          </div>
        </div>
      </div>
    </section>

    <!-- STATISTICS SECTION -->
    <section class="stats-section" id="stats">
      <div class="stats-container">
        <div class="stat-item">
          <div class="stat-big-number">98K+</div>
          <div class="stat-big-label">Profiles Per Month</div>
        </div>
        <div class="stat-item">
          <div class="stat-big-number">2.5M</div>
          <div class="stat-big-label">Total Candidates</div>
        </div>
        <div class="stat-item">
          <div class="stat-big-number">4.9★</div>
          <div class="stat-big-label">User Rating</div>
        </div>
        <div class="stat-item">
          <div class="stat-big-number">99.9%</div>
          <div class="stat-big-label">Uptime Guarantee</div>
        </div>
      </div>
    </section>

    <!-- FAQ SECTION -->
    <section class="faq-section" id="faq">
      <div class="faq-container">
        <h2 class="section-title">Frequently Asked Questions</h2>
        <p class="section-subtitle">Everything you need to know about TalentFlow</p>

        <div class="faq-list">
          <div 
            v-for="(item, idx) in faqItems" 
            :key="idx" 
            class="faq-item"
            @click="toggleFAQ(idx)"
          >
            <div class="faq-question">
              <h4>{{ item.question }}</h4>
              <span class="faq-chevron" :class="{ expanded: item.open }">▼</span>
            </div>
            <div v-show="item.open" class="faq-answer">
              {{ item.answer }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- FOOTER -->
    <footer class="footer">
      <div class="footer-container">
        <div class="footer-column">
          <h4>TalentFlow</h4>
          <p>AI-powered recruitment platform for modern teams</p>
        </div>
        <div class="footer-column">
          <h5>Company</h5>
          <a href="#">About Us</a>
          <a href="#">Blog</a>
          <a href="#">Careers</a>
          <a href="#">Contact</a>
        </div>
        <div class="footer-column">
          <h5>Product</h5>
          <a href="#">Features</a>
          <a href="#">Pricing</a>
          <a href="#">Security</a>
          <a href="#">API</a>
        </div>
        <div class="footer-column">
          <h5>Support</h5>
          <a href="#">Documentation</a>
          <a href="#">Help Center</a>
          <a href="#">Community</a>
          <a href="#">Contact Support</a>
        </div>
        <div class="footer-column">
          <h5>Legal</h5>
          <a href="#">Privacy Policy</a>
          <a href="#">Terms of Service</a>
          <a href="#">Cookie Policy</a>
          <a href="#">GDPR</a>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; 2024 TalentFlow. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from 'boot/axios'

const keyword = ref('engineer')
const location = ref('Bengaluru')
const pages = ref(1)
const withEmail = ref(true)

const profiles = ref([])
const loadingScrape = ref(false)
const loadingRefresh = ref(false)

const faqItems = ref([
  {
    question: 'How does TalentFlow scrape candidate data?',
    answer: 'TalentFlow uses advanced web scraping technology combined with AI to ethically collect and organize candidate information from public LinkedIn profiles and other professional networks.',
    open: false
  },
  {
    question: 'Is it legal to scrape LinkedIn data?',
    answer: 'We comply with all applicable laws and regulations. Our scraping respects rate limits and robots.txt. Always ensure you have proper legal agreements in place.',
    open: false
  },
  {
    question: 'How accurate are the search results?',
    answer: 'Our matching algorithm achieves 94% accuracy by analyzing skills, experience, location, and other factors. Results are continuously refined with machine learning.',
    open: false
  },
  {
    question: 'Can I export the candidate data?',
    answer: 'Yes! Export results as CSV, JSON, or directly integrate with your ATS system. All exports maintain data privacy and compliance.',
    open: false
  },
  {
    question: 'What is your pricing model?',
    answer: 'We offer flexible plans starting from $99/month for startups up to enterprise solutions. Contact our sales team for custom quotes.',
    open: false
  }
])

async function loadSaved () {
  try {
    const res = await api.get('/profiles')
    profiles.value = Array.isArray(res.data) ? res.data : []
  } catch (err) {
    console.error(err)
    profiles.value = []
  }
}

async function scrape () {
  if (!keyword.value || !location.value) return
  loadingScrape.value = true
  try {
    const res = await api.get('/scrape-linkedin', { params: { keyword: keyword.value, location: location.value, pages: pages.value, with_email: withEmail.value ? 1 : 0 } })
    profiles.value = res.data.profiles || []
  } catch (err) {
    console.error(err)
  } finally {
    loadingScrape.value = false
  }
}

async function refresh () {
  if (!keyword.value || !location.value) return
  loadingRefresh.value = true
  try {
    const res = await api.get('/profiles/refresh', { params: { keyword: keyword.value, location: location.value, pages: pages.value, with_email: withEmail.value ? 1 : 0 } })
    profiles.value = res.data.profiles || []
  } catch (err) {
    console.error(err)
  } finally {
    loadingRefresh.value = false
  }
}

function toggleFAQ(idx) {
  faqItems.value[idx].open = !faqItems.value[idx].open
}

loadSaved()
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.page-wrapper {
  width: 100%;
  background: #F3F4F6;
  font-family: 'Poppins', 'Inter', sans-serif;
  color: #1F2937;
}

/* NAVBAR */
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: #003B7F;
  padding: 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.navbar-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.navbar-logo {
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
}

.navbar-menu {
  display: flex;
  gap: 40px;
  margin: 0 auto;
}

.navbar-menu a {
  color: #FFFFFF;
  text-decoration: none;
  font-size: 14px;
  transition: 300ms ease;
  border-bottom: 2px solid transparent;
}

.navbar-menu a:hover {
  border-bottom-color: #0099D8;
}

.navbar-actions {
  display: flex;
  gap: 12px;
}

.btn-outline {
  background: transparent;
  border: 2px solid #FFFFFF;
  color: #FFFFFF;
  padding: 8px 24px;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  font-size: 14px;
  transition: 300ms ease;
}

.btn-outline:hover {
  background: rgba(255,255,255,0.1);
}

.btn-solid {
  background: #0099D8;
  border: none;
  color: #FFFFFF;
  padding: 8px 24px;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  font-size: 14px;
  transition: 300ms ease;
}

.btn-solid:hover {
  background: #0077a8;
}

@media (max-width: 768px) {
  .navbar-menu {
    display: none;
  }
}

/* HERO SECTION */
.hero-section {
  background: linear-gradient(135deg, #003B7F 0%, #0099D8 100%);
  padding: 80px 24px;
  color: #FFFFFF;
}

.hero-container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
  align-items: center;
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 16px;
  opacity: 0.9;
  line-height: 1.6;
}

.btn-hero {
  background: #FFFFFF;
  color: #003B7F;
  border: none;
  padding: 14px 40px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  transition: 300ms ease;
  width: fit-content;
}

.btn-hero:hover {
  transform: scale(1.02);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}

.hero-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.stat-card {
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #FFFFFF;
}

.stat-label {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
  margin-top: 8px;
}

@media (max-width: 768px) {
  .hero-container {
    grid-template-columns: 1fr;
    gap: 40px;
  }
  
  .hero-title {
    font-size: 32px;
  }
}

/* SEARCH SECTION */
.search-section {
  padding: 80px 24px;
  background: #FFFFFF;
}

.search-container {
  max-width: 1200px;
  margin: 0 auto;
}

.search-header {
  text-align: center;
  margin-bottom: 60px;
}

.search-header h2 {
  font-size: 36px;
  font-weight: 700;
  color: #1F2937;
  margin-bottom: 12px;
}

.search-header p {
  font-size: 16px;
  color: #6B7280;
}

.search-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 40px;
}

.search-panel {
  background: #F3F4F6;
  border-radius: 12px;
  padding: 32px;
  height: fit-content;
  position: sticky;
  top: 80px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1F2937;
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  transition: 300ms ease;
}

.form-input:focus {
  outline: none;
  border-color: #0099D8;
  box-shadow: 0 0 0 3px rgba(0,153,216,0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: normal;
  margin-top: 30px;
}

.checkbox-group input {
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.button-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 24px;
}

.btn-primary, .btn-secondary, .btn-light {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: 300ms ease;
  font-size: 14px;
}

.btn-primary {
  background: #003B7F;
  color: #FFFFFF;
}

.btn-primary:hover:not(:disabled) {
  background: #002957;
  transform: translateY(-2px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #0099D8;
  color: #FFFFFF;
}

.btn-secondary:hover:not(:disabled) {
  background: #0077a8;
  transform: translateY(-2px);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-light {
  background: #FFFFFF;
  color: #003B7F;
  border: 1px solid #E5E7EB;
}

.btn-light:hover {
  background: #F9FAFB;
}

.results-panel {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 32px;
}

.empty-state {
  text-align: center;
  padding: 60px 24px;
  color: #6B7280;
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 16px;
}

.profiles-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 600px;
  overflow-y: auto;
}

.profile-card {
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 16px;
  transition: 300ms ease;
  cursor: pointer;
}

.profile-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}

.profile-header {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.profile-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #0099D8;
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  flex-shrink: 0;
}

.profile-info {
  flex: 1;
}

.profile-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2937;
  margin: 0;
}

.profile-role {
  font-size: 12px;
  color: #6B7280;
  margin: 4px 0 0 0;
}

.profile-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.meta-tag {
  background: #E5E7EB;
  color: #6B7280;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
}

.profile-link {
  color: #0099D8;
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  transition: 300ms ease;
}

.profile-link:hover {
  color: #003B7F;
}

@media (max-width: 768px) {
  .search-grid {
    grid-template-columns: 1fr;
  }
  
  .search-panel {
    position: relative;
    top: 0;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
}

/* FEATURES SECTION */
.features-section {
  padding: 80px 24px;
  background: #F3F4F6;
}

.features-container {
  max-width: 1200px;
  margin: 0 auto;
}

.section-title {
  font-size: 36px;
  font-weight: 700;
  color: #1F2937;
  text-align: center;
  margin-bottom: 16px;
}

.section-subtitle {
  font-size: 16px;
  color: #6B7280;
  text-align: center;
  margin-bottom: 60px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
}

.feature-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  transition: 300ms ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.12);
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.feature-card h4 {
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 12px;
}

.feature-card p {
  font-size: 14px;
  color: #6B7280;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }
}

@media (max-width: 480px) {
  .features-grid {
    grid-template-columns: 1fr;
  }
}

/* PROCESS SECTION */
.process-section {
  padding: 80px 24px;
  background: #FFFFFF;
}

.process-container {
  max-width: 1200px;
  margin: 0 auto;
}

.process-flow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 60px;
  gap: 24px;
}

.process-step {
  flex: 1;
  text-align: center;
}

.step-circle {
  width: 70px;
  height: 70px;
  background: #0099D8;
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  margin: 0 auto 16px;
}

.process-step h4 {
  font-size: 16px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 8px;
}

.process-step p {
  font-size: 14px;
  color: #6B7280;
  line-height: 1.6;
}

.process-arrow {
  font-size: 24px;
  color: #D1D5DB;
  font-weight: 700;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .process-flow {
    flex-direction: column;
    gap: 40px;
  }
  
  .process-arrow {
    transform: rotate(90deg);
  }
}

/* STATS SECTION */
.stats-section {
  background: #003B7F;
  color: #FFFFFF;
  padding: 80px 24px;
}

.stats-container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 40px;
  text-align: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-big-number {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
}

.stat-big-label {
  font-size: 14px;
  opacity: 0.9;
}

@media (max-width: 768px) {
  .stats-container {
    grid-template-columns: repeat(2, 1fr);
    gap: 32px;
  }
}

@media (max-width: 480px) {
  .stats-container {
    grid-template-columns: 1fr;
    gap: 24px;
  }
}

/* FAQ SECTION */
.faq-section {
  padding: 80px 24px;
  background: #F3F4F6;
}

.faq-container {
  max-width: 800px;
  margin: 0 auto;
}

.faq-list {
  margin-top: 60px;
}

.faq-item {
  background: #FFFFFF;
  border-bottom: 1px solid #E5E7EB;
  cursor: pointer;
  transition: 300ms ease;
}

.faq-item:hover {
  background: #F9FAFB;
}

.faq-question {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  font-weight: 600;
  color: #1F2937;
}

.faq-question h4 {
  font-size: 16px;
  margin: 0;
}

.faq-chevron {
  transition: 300ms ease;
  font-size: 12px;
  color: #6B7280;
}

.faq-chevron.expanded {
  transform: rotate(180deg);
}

.faq-answer {
  padding: 0 24px 24px 24px;
  color: #6B7280;
  font-size: 14px;
  line-height: 1.6;
  animation: slideDown 300ms ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* FOOTER */
.footer {
  background: #003B7F;
  color: #FFFFFF;
  padding: 60px 24px 24px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 40px;
  margin-bottom: 40px;
}

.footer-column h4,
.footer-column h5 {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 16px;
  color: #FFFFFF;
}

.footer-column h4 {
  font-size: 18px;
  text-transform: none;
}

.footer-column p {
  font-size: 14px;
  opacity: 0.8;
  line-height: 1.6;
}

.footer-column a {
  display: block;
  font-size: 14px;
  color: #FFFFFF;
  opacity: 0.8;
  text-decoration: none;
  margin-bottom: 8px;
  transition: 300ms ease;
}

.footer-column a:hover {
  opacity: 1;
}

.footer-bottom {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid rgba(255,255,255,0.1);
  font-size: 14px;
  opacity: 0.8;
}

@media (max-width: 768px) {
  .footer-container {
    grid-template-columns: repeat(2, 1fr);
    gap: 32px;
  }
}

@media (max-width: 480px) {
  .footer-container {
    grid-template-columns: 1fr;
  }
}
</style>
