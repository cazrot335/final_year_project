import os
import json
import re
from datetime import datetime
from collections import Counter
import PyPDF2
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

resume_bp = Blueprint('resume_screening', __name__, url_prefix='/api/resumes')

# Load NLP model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print("Warning: spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

# --- SECTION DIVISION ---

def divide_resume_by_sections(text):
    """
    Divide resume into logical sections based on common headers.
    Returns dict with sections as keys and content as values.
    """
    # Common section headers
    section_patterns = {
        'contact': r'(?:contact|personal info|contact info|details)',
        'summary': r'(?:professional summary|objective|about|profile)',
        'experience': r'(?:work experience|employment|professional experience|experience)',
        'education': r'(?:education|academic|qualifications)',
        'skills': r'(?:technical skills|skills|competencies|technical)',
        'projects': r'(?:projects|portfolio)',
        'certifications': r'(?:certifications|certificates|cert)',
    }
    
    lines = text.split('\n')
    sections = {}
    current_section = None
    current_content = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check if line is a section header
        is_header = False
        for section_name, pattern in section_patterns.items():
            if re.match(f'^{pattern}', line_stripped, re.IGNORECASE) and len(line_stripped) < 50:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                current_section = section_name
                current_content = []
                is_header = True
                break
        
        # If not header, add to current section
        if not is_header and current_section and line_stripped:
            current_content.append(line_stripped)
    
    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections

# --- PARSING HELPERS ---

def extract_text_from_pdf(file_path):
    """Extract text from PDF file."""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting PDF {file_path}: {e}")
        return None

def extract_contact_info(sections_dict, full_text):
    """Extract email, phone, LinkedIn, GitHub from contact section and full text."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    # Phone pattern: (123) 456-7890, 123-456-7890, 1234567890, +91-XXXX-XXXXX
    phone_pattern = r'(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,3}\)[\s.-]?)?(?:\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}|\d{10})'
    
    linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9\-]+'
    github_pattern = r'github\.com/[a-zA-Z0-9\-]+'
    
    # Search in contact section first, then full text
    search_text = sections_dict.get('contact', '') + '\n' + full_text
    
    emails = list(set(re.findall(email_pattern, search_text)))
    
    # Extract phones - validate minimum 10 digits
    phone_matches = re.findall(phone_pattern, search_text)
    phones = []
    for phone in phone_matches:
        digits_only = re.sub(r'\D', '', phone)
        if len(digits_only) >= 10:
            phones.append(phone.strip())
    phones = list(set(phones))[:1]  # Keep only first unique phone
    
    linkedin_urls = list(set(re.findall(linkedin_pattern, search_text, re.IGNORECASE)))
    github_urls = list(set(re.findall(github_pattern, search_text, re.IGNORECASE)))
    
    contact = {
        'email': emails,
        'phone': phones,
        'linkedin': linkedin_urls,
        'github': github_urls
    }
    
    return contact

def extract_name(sections_dict, full_text):
    """Extract name from resume - look for it in contact section or first few lines."""
    # Try contact section first
    contact_section = sections_dict.get('contact', '')
    if contact_section:
        lines = contact_section.split('\n')
        for line in lines:
            line = line.strip()
            if line and '@' not in line and 'http' not in line and len(line) < 60:
                words = line.split()
                if 1 <= len(words) <= 4:
                    return line
    
    # Try first few non-empty lines of full text
    lines = full_text.split('\n')
    for line in lines[:15]:
        line = line.strip()
        if line and len(line) > 2 and len(line) < 60:
            # Skip if looks like section header or common keywords
            if not any(x in line.lower() for x in ['summary', 'objective', 'profile', 'contact', 'experience', 'education', 'skills', '@', 'http']):
                words = line.split()
                if 1 <= len(words) <= 4:
                    return line
    
    return 'Unknown'

def extract_education_section(education_text):
    """
    Extract education details from education section.
    Returns just the text lines, not the pattern.
    """
    if not education_text:
        return []
    
    lines = education_text.split('\n')
    education_entries = []
    
    degree_keywords = ['bachelor', 'b.s.', 'b.a.', 'bs', 'ba', 'master', 'm.s.', 'm.a.', 'ms', 'ma', 'phd', 'ph.d.', 'diploma', 'associate']
    
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and any(keyword in line_stripped.lower() for keyword in degree_keywords):
            education_entries.append(line_stripped)
    
    return education_entries[:3]  # Limit to 3 entries

def parse_date_advanced(date_str):
    """Parse date string with improved handling."""
    if not date_str:
        return None
    
    date_str = date_str.strip().lower()
    
    # Handle "Present" or "Current"
    if any(x in date_str for x in ['present', 'current', 'ongoing', 'till date', 'till now']):
        return (datetime.now().year, datetime.now().month)
    
    # Month mapping
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    # Try "Month Year" format
    parts = date_str.split()
    if len(parts) >= 2:
        month_name = parts[0].rstrip('.,')
        try:
            year = int(parts[-1])
            if 1980 <= year <= 2030:
                month = months.get(month_name)
                if month:
                    return (year, month)
        except ValueError:
            pass
    
    # Try "MM/YYYY" or "MM-YYYY" format
    if '/' in date_str or '-' in date_str:
        separator = '/' if '/' in date_str else '-'
        try:
            parts = date_str.split(separator)
            if len(parts) == 2:
                month, year = int(parts[0]), int(parts[1])
                if 1 <= month <= 12 and 1980 <= year <= 2030:
                    return (year, month)
        except ValueError:
            pass
    
    # Try just year
    try:
        year = int(date_str)
        if 1980 <= year <= 2030:
            return (year, 1)
    except ValueError:
        pass
    
    return None

def extract_experience_from_section(experience_text):
    """
    Extract work experience from dedicated experience section.
    More accurate since section is already separated.
    """
    if not experience_text:
        return []
    
    experience = []
    lines = experience_text.split('\n')
    
    # Date patterns
    date_patterns = [
        r'(\d{1,2}/\d{4})',  # MM/YYYY
        r'(\d{1,2}-\d{4})',  # MM-YYYY
        r'([A-Za-z]{3,9}\s+\d{4})',  # Month YYYY
        r'(Present|Current|Ongoing|Till Date|Till Now)',  # Present/Current
    ]
    
    current_job = None
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        # Check if line contains dates
        dates_found = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, line_stripped, re.IGNORECASE)
            for match in matches:
                dates_found.append(match.group(1))
        
        # If we found dates, this is likely a job entry
        if dates_found:
            # Save previous job
            if current_job and (current_job.get('start_date') or current_job.get('end_date')):
                experience.append(current_job)
            
            # Create new job entry
            current_job = {
                'position': line_stripped,
                'start_date': None,
                'end_date': None,
                'raw_dates': dates_found
            }
            
            # Parse dates - assume format: "End Date - Start Date" or similar
            if len(dates_found) >= 2:
                date1 = parse_date_advanced(dates_found[0])
                date2 = parse_date_advanced(dates_found[1])
                
                if date1 and date2:
                    # Determine which is start and which is end
                    if date1 > date2:
                        current_job['end_date'] = date1
                        current_job['start_date'] = date2
                    else:
                        current_job['start_date'] = date1
                        current_job['end_date'] = date2
            elif len(dates_found) == 1:
                parsed = parse_date_advanced(dates_found[0])
                if parsed:
                    current_job['end_date'] = parsed
                    # Try to estimate start date from next date
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_matches = re.finditer(date_patterns[0], lines[j], re.IGNORECASE)
                        for match in next_matches:
                            start = parse_date_advanced(match.group(1))
                            if start and start < parsed:
                                current_job['start_date'] = start
                                break
    
    # Add last job
    if current_job and (current_job.get('start_date') or current_job.get('end_date')):
        experience.append(current_job)
    
    # Calculate tenure
    for job in experience:
        if job['start_date'] and job['end_date']:
            tenure_months = calculate_tenure(job['start_date'], job['end_date'])
            job['tenure_months'] = tenure_months
            job['tenure_years'] = round(tenure_months / 12, 1)
        else:
            job['tenure_months'] = None
            job['tenure_years'] = None
    
    return experience

def calculate_tenure(start_date, end_date):
    """Calculate tenure in months between two dates."""
    if not start_date or not end_date:
        return None
    
    start_year, start_month = start_date
    end_year, end_month = end_date
    
    months = (end_year - start_year) * 12 + (end_month - start_month)
    return max(0, months)

def detect_job_hopping_detailed(experience):
    """Detect job hopping pattern."""
    if len(experience) < 2:
        return {
            'is_hopping': False,
            'severity': 'None',
            'score': 0,
            'analysis': 'Insufficient job history',
            'flagged_jobs': [],
            'hopping_ratio': 0,
            'total_jobs': len(experience),
            'short_tenure_count': 0,
            'avg_tenure_months': 0,
            'stability_assessment': '✅ Not enough data'
        }
    
    # Filter jobs with valid tenure
    jobs_with_tenure = [j for j in experience if j.get('tenure_months') is not None]
    
    if len(jobs_with_tenure) < 2:
        return {
            'is_hopping': False,
            'severity': 'None',
            'score': 0,
            'analysis': 'Cannot determine tenure pattern',
            'flagged_jobs': [],
            'hopping_ratio': 0,
            'total_jobs': len(experience),
            'short_tenure_count': 0,
            'avg_tenure_months': 0,
            'stability_assessment': '⚠️ Limited data'
        }
    
    # Analyze patterns
    short_tenure_jobs = [j for j in jobs_with_tenure if j.get('tenure_months', 0) < 12]
    avg_tenure_months = sum(j.get('tenure_months', 0) for j in jobs_with_tenure) / len(jobs_with_tenure)
    hopping_ratio = len(short_tenure_jobs) / len(jobs_with_tenure)
    
    # Determine severity
    severity = 'None'
    is_hopping = False
    hopping_score = 0
    
    if hopping_ratio >= 0.5:
        severity = 'Critical'
        is_hopping = True
        hopping_score = 90
    elif hopping_ratio >= 0.35:
        severity = 'High'
        is_hopping = True
        hopping_score = 70
    elif len(short_tenure_jobs) >= 3 and hopping_ratio >= 0.25:
        severity = 'Medium'
        is_hopping = True
        hopping_score = 50
    elif len(short_tenure_jobs) >= 2:
        severity = 'Low'
        hopping_score = 25
    
    flagged_jobs = [
        {
            'position': j['position'][:60],
            'tenure_months': j.get('tenure_months'),
            'tenure_years': j.get('tenure_years'),
            'status': 'Very Short' if j.get('tenure_months', 0) < 6 else 'Short'
        }
        for j in short_tenure_jobs
    ]
    
    analysis = f"{len(jobs_with_tenure)} total positions. " \
               f"{len(short_tenure_jobs)} roles under 1 year. " \
               f"Avg tenure: {avg_tenure_months:.1f} months."
    
    return {
        'is_hopping': is_hopping,
        'severity': severity,
        'score': hopping_score,
        'analysis': analysis,
        'flagged_jobs': flagged_jobs,
        'hopping_ratio': round(hopping_ratio * 100, 1),
        'short_tenure_count': len(short_tenure_jobs),
        'total_jobs': len(jobs_with_tenure),
        'avg_tenure_months': round(avg_tenure_months, 1),
        'stability_assessment': get_stability_assessment(avg_tenure_months, hopping_ratio)
    }

def get_stability_assessment(avg_tenure, hopping_ratio):
    """Generate stability assessment."""
    if hopping_ratio >= 0.5:
        return f"⚠️ Unstable: Frequent job changes ({hopping_ratio*100:.0f}% under 1yr). Avg: {avg_tenure:.1f}mo"
    elif hopping_ratio >= 0.35:
        return f"⚠️ Moderate instability: {hopping_ratio*100:.0f}% short tenures. Avg: {avg_tenure:.1f}mo"
    elif hopping_ratio >= 0.2:
        return f"⚡ Some job changes: {hopping_ratio*100:.0f}% under 1yr. Avg: {avg_tenure:.1f}mo"
    else:
        return f"✅ Stable: {hopping_ratio*100:.0f}% short tenures. Avg: {avg_tenure:.1f}mo"

def extract_skills(text):
    """Extract skills from resume."""
    tech_skills = [
        # Languages
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'kotlin', 'swift', 'scala', 'r', 'matlab',
        # Frontend
        'react', 'react.js', 'angular', 'vue.js', 'vue', 'html', 'css', 'scss', 'sass', 'bootstrap', 'tailwind', 'next.js', 'nextjs', 'svelte', 'ember',
        # Backend
        'nodejs', 'node.js', 'express', 'django', 'flask', 'spring', 'spring boot', 'fastapi', 'laravel', 'rails', 'asp.net',
        # Databases
        'sql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch', 'firebase', 'dynamodb', 'cassandra', 'oracle', 'sqlite',
        # Cloud & DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab ci', 'github actions', 'terraform', 'ansible',
        # Version Control
        'git', 'github', 'gitlab', 'bitbucket', 'svn',
        # OS
        'linux', 'unix', 'windows', 'macos',
        # ML/AI
        'machine learning', 'tensorflow', 'pytorch', 'scikit-learn', 'nlp', 'data science', 'keras',
        # APIs
        'rest api', 'graphql', 'microservices', 'monolithic', 'soap', 'grpc',
        # Methodologies
        'agile', 'scrum', 'kanban', 'jira', 'confluence',
        # Testing
        'jest', 'pytest', 'mocha', 'cypress', 'selenium', 'junit', 'testing',
        # Other
        'api design', 'system design', 'database design', 'oop', 'functional programming', 'devops'
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in tech_skills:
        if skill in text_lower:
            found_skills.append(skill)
    
    return list(set(found_skills))

def calculate_total_experience_years(experience):
    """Calculate total years of experience from job history."""
    if not experience:
        return 0
    
    jobs_with_tenure = [j for j in experience if j.get('tenure_months') is not None]
    
    if not jobs_with_tenure:
        return 0
    
    total_months = sum(j.get('tenure_months', 0) for j in jobs_with_tenure)
    total_years = total_months / 12
    
    return round(total_years, 1)

def quality_check(text):
    """Check resume quality."""
    issues = []
    
    typo_patterns = {
        r'\b(teh|taht|tihs|recieve|occured|seperator|neccessary)\b': 'Spelling error',
        r'\.\.\.+': 'Multiple periods',
        r'\s{3,}': 'Extra spacing',
    }
    
    for pattern, issue_type in typo_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            issues.append(issue_type)
    
    quality_score = min(10, max(1, 10 - len(issues)))
    
    return {
        'score': quality_score,
        'issues': issues
    }

def calculate_relevance_score(resume_text, job_description):
    """Calculate relevance score."""
    try:
        if not job_description or not resume_text or len(resume_text) < 100:
            return 0
        vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3), max_features=100)
        vectors = vectorizer.fit_transform([resume_text[:2000], job_description[:2000]])
        similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        return round(similarity * 100, 2)
    except:
        return 0

def identify_skill_gaps(resume_skills, job_description):
    """Identify missing skills."""
    job_skills = extract_skills(job_description)
    gaps = [skill for skill in job_skills if skill not in resume_skills]
    return list(set(gaps))[:10]

def identify_plus_points(resume, job_description):
    """Identify strengths."""
    plus_points = []
    
    # Experience match
    exp_years = resume.get('experience_years', 0)
    if exp_years >= 5:
        plus_points.append(f'✅ Strong experience: {exp_years}+ years')
    elif exp_years >= 2:
        plus_points.append(f'✅ Solid experience: {exp_years}+ years')
    elif exp_years >= 1:
        plus_points.append(f'✅ Some experience: {exp_years}+ years')
    
    # Skills match
    resume_skills = resume.get('skills', [])
    job_skills = extract_skills(job_description)
    matched_skills = [s for s in resume_skills if s in job_skills]
    if matched_skills and job_skills:
        skill_match_pct = round((len(matched_skills) / len(job_skills)) * 100)
        plus_points.append(f'✅ {len(matched_skills)}/{len(job_skills)} matching skills ({skill_match_pct}%)')
    
    # Contact completeness
    contact = resume.get('contact', {})
    contact_items = sum(1 for v in [contact.get('email'), contact.get('phone'), 
                                     contact.get('linkedin'), contact.get('github')] if v)
    if contact_items >= 3:
        plus_points.append(f'✅ Complete contact info ({contact_items}/4 channels)')
    
    # Quality
    if resume.get('quality_check', {}).get('score', 0) >= 9:
        plus_points.append('✅ Excellent formatting')
    
    # Stability
    if not resume.get('job_hopping', {}).get('is_hopping'):
        plus_points.append('✅ Stable career progression')
    
    return plus_points[:6]

def identify_flaws(resume, job_description):
    """Identify weaknesses."""
    flaws = []
    
    exp_years = resume.get('experience_years', 0)
    if exp_years < 2:
        flaws.append(f'⚠️  Limited experience: {exp_years:.1f} years')
    elif exp_years < 5:
        flaws.append(f'⚠️  Below requirement: {exp_years:.1f} years (need 5+)')
    
    # Skill gaps
    skill_gaps = identify_skill_gaps(resume.get('skills', []), job_description)
    if skill_gaps:
        flaws.append(f'⚠️  Missing {len(skill_gaps)} key skills: {", ".join(skill_gaps[:3])}')
    
    # Quality issues
    quality = resume.get('quality_check', {})
    if quality.get('score', 0) < 7:
        flaws.append(f'⚠️  Format issues: {quality["score"]}/10 quality')
    
    # Job hopping
    job_hopping = resume.get('job_hopping', {})
    if job_hopping.get('is_hopping'):
        severity = job_hopping.get('severity', 'Unknown')
        ratio = job_hopping.get('hopping_ratio', 0)
        flaws.append(f'🚩 Job hopping ({severity}): {ratio}% roles <1yr')
    
    # Missing contact
    contact = resume.get('contact', {})
    if not contact.get('email'):
        flaws.append('❌ No email address')
    if not contact.get('phone'):
        flaws.append('⚠️  No phone number')
    
    return flaws[:6]

# --- MAIN PARSING FUNCTION ---

def parse_resume(file_path, job_description=''):
    """Parse resume using section-based approach."""
    text = extract_text_from_pdf(file_path)
    if not text:
        return {'error': 'Could not extract text from PDF'}
    
    # Divide into sections
    sections = divide_resume_by_sections(text)
    
    # Extract from sections
    contact = extract_contact_info(sections, text)
    name = extract_name(sections, text)
    education = extract_education_section(sections.get('education', ''))
    experience = extract_experience_from_section(sections.get('experience', ''))
    skills = extract_skills(text)
    quality = quality_check(text)
    
    # Job hopping analysis
    job_hopping = detect_job_hopping_detailed(experience)
    
    # Calculate experience
    experience_years = calculate_total_experience_years(experience)
    relevance_score = calculate_relevance_score(text, job_description) if job_description else 0
    
    # Red flags
    red_flags = []
    if quality['score'] < 7:
        red_flags.append('Quality issues')
    if job_hopping['is_hopping']:
        red_flags.append(f"Job hopping: {job_hopping['severity']}")
    if not contact['email']:
        red_flags.append('No email')
    if experience_years < 2:
        red_flags.append('Limited exp')
    
    result = {
        'name': name,
        'contact': contact,
        'experience': experience,
        'job_hopping': job_hopping,
        'skills': skills,
        'experience_years': experience_years,
        'quality_check': quality,
        'red_flags': red_flags,
        'relevance_score': relevance_score,
        'parsed_at': datetime.now().isoformat()
    }
    
    # Analysis if JD provided
    if job_description:
        result['plus_points'] = identify_plus_points(result, job_description)
        result['flaws'] = identify_flaws(result, job_description)
    
    return result

def calculate_overall_fit(resume):
    """Calculate overall fit score."""
    score = 0
    
    # Experience (0-30 points)
    exp_years = resume.get('experience_years', 0)
    score += min(exp_years * 3, 30)
    
    # Skills (0-20 points)
    skill_count = len(resume.get('skills', []))
    score += min(skill_count * 2, 20)
    
    # Relevance (0-15 points)
    relevance = resume.get('relevance_score', 0)
    score += (relevance / 100) * 15
    
    # Quality (0-10 points)
    quality_score = resume.get('quality_check', {}).get('score', 5)
    score += quality_score
    
    # Contact (0-10 points)
    contact = resume.get('contact', {})
    contact_items = sum(1 for v in [contact.get('email'), contact.get('phone')] if v)
    score += contact_items * 5
    
    # Job hopping penalty (0-20 deduction)
    hopping_penalty = resume.get('job_hopping', {}).get('score', 0) * 0.2
    score -= hopping_penalty
    
    return round(max(0, score), 1)

def calculate_peer_rank(resumes):
    """Rank resumes using peer comparison."""
    if not resumes:
        return []
    
    scored_resumes = []
    for resume in resumes:
        fit_score = calculate_overall_fit(resume)
        scored_resumes.append({
            'resume': resume,
            'fit_score': fit_score
        })
    
    # Sort by fit score
    scored_resumes.sort(key=lambda x: x['fit_score'], reverse=True)
    
    # Assign ranks and percentiles
    ranked = []
    for idx, item in enumerate(scored_resumes):
        percentile = round(((len(scored_resumes) - idx) / len(scored_resumes)) * 100, 1)
        
        ranked.append({
            'rank': idx + 1,
            'name': item['resume'].get('name', 'Unknown'),
            'fit_score': item['fit_score'],
            'percentile': percentile,
            'comparison': f"Better than {percentile}% of candidates",
            'resume': item['resume']
        })
    
    return ranked

# --- FLASK ROUTES ---

@resume_bp.route('/parse', methods=['POST'])
def parse_resume_endpoint():
    """Parse single resume."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    job_description = request.form.get('job_description', '')
    
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    temp_path = f'/tmp/{file.filename}'
    file.save(temp_path)
    
    result = parse_resume(temp_path, job_description)
    
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    return jsonify(result)

@resume_bp.route('/parse-batch', methods=['POST'])
def parse_batch_endpoint():
    """Parse batch of resumes."""
    files = request.files.getlist('files')
    job_description = request.form.get('job_description', '')
    
    if not files:
        return jsonify({'error': 'No files provided'}), 400
    
    parsed_resumes = []
    errors = []
    
    for file in files:
        if not file.filename:
            continue
        
        if not file.filename.lower().endswith('.pdf'):
            errors.append({'file': file.filename, 'error': 'Not a PDF'})
            continue
        
        try:
            temp_path = f'/tmp/{file.filename}'
            file.save(temp_path)
            
            result = parse_resume(temp_path, job_description)
            if 'error' not in result:
                parsed_resumes.append(result)
            else:
                errors.append({'file': file.filename, 'error': result.get('error')})
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            errors.append({'file': file.filename, 'error': str(e)})
    
    # Peer ranking
    ranked_resumes = calculate_peer_rank(parsed_resumes)
    
    return jsonify({
        'resumes': [r['resume'] for r in ranked_resumes],
        'rankings': ranked_resumes,
        'count': len(parsed_resumes),
        'errors': errors,
        'total_processed': len(files)
    })

@resume_bp.route('/rank', methods=['POST'])
def rank_resumes_endpoint():
    """Rank resumes."""
    data = request.get_json()
    resumes = data.get('resumes', [])
    
    ranked = calculate_peer_rank(resumes)
    
    return jsonify(ranked)

@resume_bp.route('/analyze', methods=['POST'])
def analyze_resume_endpoint():
    """Analyze single resume."""
    data = request.get_json()
    resume = data.get('resume', {})
    job_description = data.get('job_description', '')
    all_resumes = data.get('all_resumes', [resume])
    
    rankings = calculate_peer_rank(all_resumes)
    resume_rank = next((r for r in rankings if r['resume']['name'] == resume.get('name')), None)
    
    analysis = {
        'name': resume.get('name'),
        'overall_fit': calculate_overall_fit(resume),
        'peer_rank': resume_rank['rank'] if resume_rank else 'N/A',
        'percentile': resume_rank['percentile'] if resume_rank else 0,
        'keyword_match': resume.get('relevance_score', 0),
        'experience_years': resume.get('experience_years', 0),
        'skill_count': len(resume.get('skills', [])),
        'skill_gaps': identify_skill_gaps(resume.get('skills', []), job_description),
        'plus_points': identify_plus_points(resume, job_description),
        'flaws': identify_flaws(resume, job_description),
        'job_hopping_analysis': resume.get('job_hopping', {})
    }
    
    return jsonify(analysis)

@resume_bp.route('/export', methods=['POST'])
def export_resumes_endpoint():
    """Export ranked resumes."""
    data = request.get_json()
    resumes = data.get('resumes', [])
    job_description = data.get('job_description', '')
    
    ranked_resumes = calculate_peer_rank(resumes)
    
    export_data = {
        'export_date': datetime.now().isoformat(),
        'total_resumes': len(resumes),
        'job_description': job_description[:300] if job_description else 'N/A',
        'ranked_resumes': []
    }
    
    for ranked_item in ranked_resumes:
        resume = ranked_item['resume']
        export_data['ranked_resumes'].append({
            'rank': ranked_item['rank'],
            'name': resume.get('name'),
            'percentile': ranked_item['percentile'],
            'experience_years': resume.get('experience_years'),
            'skills_count': len(resume.get('skills', [])),
            'contact': resume.get('contact'),
            'job_hopping': resume.get('job_hopping'),
            'plus_points': identify_plus_points(resume, job_description),
            'flaws': identify_flaws(resume, job_description)
        })
    
    return jsonify(export_data)