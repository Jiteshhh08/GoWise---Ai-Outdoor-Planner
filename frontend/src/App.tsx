import { useState, type FormEvent } from 'react'
import { ArrowUpRight, Check, ChevronDown, Clock3, Compass, Leaf, LoaderCircle, MapPin, Menu, Mountain, Sparkles, Wind, X } from 'lucide-react'
import { requestRecommendation } from './api/recommendations'
import RecommendationResults from './components/RecommendationResults'
import type { RecommendationResponse } from './types/recommendations'

const prompts = [
  { icon: '↗', label: 'A run near me', text: 'Where can I go running tomorrow morning near Powai?' },
  { icon: '◌', label: 'A quiet picnic', text: 'Find a good time for a picnic in a park this weekend around Bandra.' },
  { icon: '⌁', label: 'A trail to explore', text: 'Where is a nice nature walk near Whitefield this Sunday morning?' },
]

function App() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<RecommendationResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

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
        <a className="topbar-link" href="#planner">Plan your day <ArrowUpRight size={16} /></a>
        <button className="mobile-menu" aria-label="Open navigation"><Menu size={21} /></button>
      </header>

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
            <div className="suggestions"><div className="suggestion-label">NEED AN IDEA? <ChevronDown size={13} /></div><div className="prompt-list">{prompts.map(prompt => <button className="prompt-chip" key={prompt.label} onClick={() => { setQuestion(prompt.text); setError(''); setResult(null) }}><span className="prompt-icon">{prompt.icon}</span>{prompt.label}<ArrowUpRight size={13} /></button>)}</div></div>
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
