import { useEffect, useState, type FormEvent } from 'react'
import { ArrowUpRight, Check, ChevronDown, Clock3, Compass, Leaf, LoaderCircle, MapPin, Menu, Mountain, Sparkles, Wind, X } from 'lucide-react'
import { requestRecommendation } from './api/recommendations'
import { getPlannerHealth, type PlannerHealth } from './api/health'
import RecommendationResults from './components/RecommendationResults'
import type { RecommendationResponse } from './types/recommendations'

const prompts = [
  { icon: '↗', label: 'Running', text: 'Where can I go running tomorrow evening near Koregaon Park?' },
  { icon: '↗', label: 'Cycling', text: 'Is it okay to cycle to work at 8 AM?' },
  { icon: '◌', label: 'Golf', text: 'Good place and time for golf on Saturday within 40 km of Andheri?' },
  { icon: '◌', label: 'Cricket', text: 'Best time this weekend for a kids’ cricket match within 15 km of Whitefield?' },
  { icon: '◌', label: 'Outdoor football', text: 'Where can I play outdoor football this weekend near Powai?' },
  { icon: '◌', label: 'Outdoor tennis', text: 'Outdoor tennis after work today near Hinjewadi, any good spots?' },
  { icon: '⌁', label: 'Hiking', text: 'Is Saturday or Sunday better for a hike near Lonavala?' },
  { icon: '⌁', label: 'Picnic', text: 'What’s a good time for a picnic in a park this weekend near Bandra?' },
  { icon: '◌', label: 'Outdoor event', text: 'Planning an outdoor birthday party on Sunday afternoon in Pune, what should I keep in mind?' },
  { icon: '⌁', label: 'Photography', text: 'Where can I take sunset photos this evening around Bandra?' },
]

function App() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<RecommendationResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState<PlannerHealth>('checking')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  useEffect(() => {
    let active = true
    void getPlannerHealth().then(status => { if (active) setHealth(status) })
    return () => { active = false }
  }, [])

  const healthLabel: Record<PlannerHealth, string> = {
    checking: 'Checking planner',
    ready: 'Planner ready',
    'model-not-ready': 'Model starting',
    'api-unavailable': 'Planner offline',
    unknown: 'Planner connected',
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const cleanQuestion = question.trim()
    if (!cleanQuestion || loading) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      setResult(await requestRecommendation(cleanQuestion))
    } catch (cause) {
      setError(cause instanceof Error && cause.name === 'TimeoutError'
        ? 'This request took too long. Please try again in a moment.'
        : cause instanceof Error ? cause.message : 'Could not reach the planner. Check that the API is running and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#home" aria-label="GoWise home"><span className="brand-mark"><Compass size={21} strokeWidth={2.2} /></span><span>go<span className="brand-accent">wise</span></span></a>
        <nav className="desktop-nav" aria-label="Main navigation"><a className="nav-active" href="#planner">Planner</a><a href="#how-it-works">How it works</a><a href="#about">About</a></nav>
        <div className={`health-indicator health-${health}`} role="status"><span />{healthLabel[health]}</div>
        <a className="topbar-link" href="#planner">Plan your day <ArrowUpRight size={16} /></a>
        <button className="mobile-menu" aria-label={mobileNavOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={mobileNavOpen} aria-controls="mobile-navigation" onClick={() => setMobileNavOpen(open => !open)}><Menu size={21} /></button>
      </header>
      {mobileNavOpen && <nav id="mobile-navigation" className="mobile-navigation" aria-label="Mobile navigation"><a href="#planner" onClick={() => setMobileNavOpen(false)}>Planner</a><a href="#how-it-works" onClick={() => setMobileNavOpen(false)}>How it works</a><a href="#about" onClick={() => setMobileNavOpen(false)}>About</a></nav>}

      <main id="home">
        <section className="hero" id="planner">
          <div className="hero-copy">
            <div className="eyebrow"><span className="live-dot" /> YOUR DAY, OUTSIDE</div>
            <h1>Make room<br />for <span>the outdoors.</span></h1>
            <p className="hero-subtitle">Tell us what you’re in the mood for. We’ll find a place and a time that make getting outside feel easy.</p>
            <div className="trust-row"><span><Check size={14} /> Live local conditions</span><span><Check size={14} /> Places worth the trip</span></div>
          </div>

          <div className="planner-card">
            <div className="card-heading"><div><p className="section-kicker">LET’S MAKE A PLAN</p><h2>What would you like to do?</h2></div><span className="sparkle-badge"><Sparkles size={17} /></span></div>
            <form onSubmit={submit}>
              <label className="sr-only" htmlFor="question">Describe the outdoor activity and where or when you want to go</label>
              <div className="input-wrap"><textarea id="question" value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void submit() } }} placeholder="e.g. A relaxed evening walk near Powai tomorrow" rows={3} maxLength={500} /><span className="input-hint"><MapPin size={14} /> Add a place and time for a more useful plan</span></div>
              <div className="form-bottom"><span className="privacy-note"><Leaf size={14} /> Your plans stay private</span><button className="submit-button" type="submit" disabled={loading || !question.trim()}>{loading ? <><LoaderCircle size={17} className="spin" /> Finding your plan</> : <>Find my plan <ArrowUpRight size={17} /></>}</button></div>
            </form>
            <div className="suggestions"><div className="suggestion-label">QUICK START · ALL 10 ACTIVITIES <ChevronDown size={13} /></div><div className="prompt-list">{prompts.map(prompt => <button className="prompt-chip" key={prompt.label} title={`Use a ${prompt.label.toLowerCase()} example`} onClick={() => { setQuestion(prompt.text); setError(''); setResult(null) }}><span className="prompt-icon">{prompt.icon}</span>{prompt.label}<ArrowUpRight size={13} /></button>)}</div><p className="prompt-help">Examples fill in a sample question. Edit the place and time to fit your plans.</p></div>
            {loading && <div className="status-panel" role="status"><span className="status-icon"><LoaderCircle className="spin" size={17} /></span><span><strong>Checking places and conditions</strong><small>Looking for a good fit around your plans…</small></span></div>}
            {error && <div className="status-panel error-panel" role="alert"><span className="status-icon"><X size={17} /></span><span><strong>We couldn’t make that plan</strong><small>{error}</small></span></div>}
          </div>
          <div className="hero-stamp"><div className="stamp-icon"><Wind size={18} /></div><span>Thoughtful plans,<br /><b>better days outside</b></span></div>
        </section>

        {result && <RecommendationResults data={result} />}

        <section className="below-fold" id="how-it-works"><div className="section-intro"><span className="section-kicker">A LITTLE MORE OUT THERE</span><h2>Good plans start<br />with a good moment.</h2></div><div className="feature-grid"><article className="feature-card"><span className="feature-icon green"><MapPin size={20} /></span><span className="feature-index">01 / FIND A PLACE</span><h3>Somewhere that fits</h3><p>Explore parks, trails and outdoor spots around the area you have in mind.</p></article><article className="feature-card"><span className="feature-icon orange"><Clock3 size={20} /></span><span className="feature-index">02 / PICK A MOMENT</span><h3>Time it just right</h3><p>Compare the forecast across your window to find a more comfortable time to go.</p></article><article className="feature-card"><span className="feature-icon blue"><Mountain size={20} /></span><span className="feature-index">03 / GET OUT THERE</span><h3>Know before you go</h3><p>See the conditions, sources and practical notes behind each suggestion.</p></article></div></section>
      </main>
      <footer id="about"><a className="brand footer-brand" href="#home"><span className="brand-mark"><Compass size={18} /></span><span>go<span className="brand-accent">wise</span></span></a><span>Made for more time outside.</span><span className="footer-disclosure">Decision support · Forecasts are estimates</span></footer>
    </div>
  )
}

export default App
