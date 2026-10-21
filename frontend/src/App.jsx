import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Copy,
  Download,
  BookOpen,
  History,
  Shield,
  Layers,
  ExternalLink,
  ChevronRight,
  Check,
  Cpu
} from 'lucide-react';

/* ─── Design tokens (inline, mirrors index.css variables) ─────────────── */
const C = {
  bgBase:     '#0A0F1E',
  bgSurface:  '#0F1525',
  bgElevated: '#141C30',
  bgOverlay:  '#1A2240',
  cream100:   '#F5F1E8',
  cream200:   '#EDE8DC',
  cream300:   '#D8D0BE',
  cream400:   '#B8AE97',
  cream500:   '#8C8270',
  blue:       '#5B8DB8',
  blueMid:    '#3D6B96',
  blueDim:    '#2A4D6E',
  blueMuted:  '#1C3350',
  green:      '#4CAF82',
  greenDim:   '#1A3D2E',
  red:        '#C85454',
  redDim:     '#3D1515',
  amber:      '#C8954C',
  amberDim:   '#3D2A10',
  borderSubtle: 'rgba(91,141,184,0.12)',
  borderMid:    'rgba(91,141,184,0.22)',
  borderActive: 'rgba(91,141,184,0.50)',
};

/* ─── Helper: inline-style card ───────────────────────────────────────── */
const card = (extra = {}) => ({
  background: C.bgSurface,
  border: `1px solid ${C.borderSubtle}`,
  borderRadius: '14px',
  ...extra,
});

export default function App() {
  const [activeTab, setActiveTab]         = useState('studio');
  const [topic, setTopic]                 = useState('Introduction to RAG');
  const [demoError, setDemoError]         = useState(false);
  const [loading, setLoading]             = useState(false);
  const [currentRun, setCurrentRun]       = useState(null);
  const [historyRuns, setHistoryRuns]     = useState([]);
  const [rules, setRules]                 = useState([]);
  const [proposals, setProposals]         = useState([]);
  const [contentIssues, setContentIssues] = useState([]);
  const [healthStatus, setHealthStatus]   = useState(null);
  const [copied, setCopied]               = useState(false);
  const [errorMessage, setErrorMessage]   = useState('');
  const [feedbackRating, setFeedbackRating]   = useState(5);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackSaved, setFeedbackSaved]     = useState(false);

  useEffect(() => {
    fetchHealth();
    fetchHistory();
    fetchRules();
    fetchProposals();
    fetchContentIssues();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/health');
      if (res.ok) setHealthStatus(await res.json());
    } catch (e) { console.warn('Backend offline', e); }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/history');
      if (res.ok) setHistoryRuns(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchRules = async () => {
    try {
      const res = await fetch('/api/rules');
      if (res.ok) setRules(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchProposals = async () => {
    try {
      const res = await fetch('/api/proposals');
      if (res.ok) setProposals(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchContentIssues = async () => {
    try {
      const res = await fetch('/api/content-issues');
      if (res.ok) setContentIssues(await res.json());
    } catch (e) { console.error(e); }
  };

  const handleGenerate = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim() || 'Introduction to RAG',
          enable_deliberate_error: demoError,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Generation failed');
      }
      const data = await res.json();
      setCurrentRun(data);
      fetchHistory();
      fetchRules();
    } catch (e) {
      setErrorMessage(e.message || 'Error occurred during generation.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadRun = async (runId) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/runs/${runId}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentRun(data);
        setActiveTab('studio');
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleReviewRule = async (ruleId, newStatus) => {
    try {
      const res = await fetch(`/api/rules/${ruleId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) fetchRules();
    } catch (e) { console.error(e); }
  };

  const handleReviewProposal = async (proposalId, newStatus) => {
    try {
      const res = await fetch(`/api/proposals/${proposalId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) fetchProposals();
    } catch (e) { console.error(e); }
  };

  const handleCopyLesson = () => {
    if (!currentRun?.approved_lesson) return;
    navigator.clipboard.writeText(currentRun.approved_lesson);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadLesson = () => {
    if (!currentRun?.approved_lesson) return;
    const blob = new Blob([currentRun.approved_lesson], { type: 'text/markdown' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = `lesson-${currentRun.run_id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSubmitFeedback = async () => {
    if (!currentRun) return;
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id:  currentRun.run_id,
          rating:  feedbackRating,
          comment: feedbackComment,
        }),
      });
      if (res.ok) {
        setFeedbackSaved(true);
        setTimeout(() => setFeedbackSaved(false), 3000);
        setFeedbackComment('');
      }
    } catch (e) { console.error(e); }
  };

  const rubricDisplayNames = {
    accurate_and_grounded:        '1. Accurate & Grounded',
    beginner_friendly_language:   '2. Beginner-Friendly Language',
    teaches_by_example:           '3. Teaches by Example',
    clear_no_unexplained_jargon:  '4. Clear, No Unexplained Jargon',
    covers_the_key_points:        '5. Covers the Key Points',
    coherent_teaching_flow:       '6. Coherent Teaching Flow',
  };

  const latestAttempt = currentRun?.attempts?.length > 0
    ? currentRun.attempts[currentRun.attempts.length - 1]
    : null;

  const tabs = [
    { id: 'studio',     label: 'Lesson Studio',                                         icon: BookOpen },
    { id: 'rejections', label: `Rejection Inspector (${currentRun?.rejection_log?.length || 0})`, icon: Shield  },
    { id: 'memory',     label: `Memory & Evolution (${rules.length})`,                   icon: Cpu     },
    { id: 'sources',    label: 'Grounding Sources',                                     icon: Layers  },
    { id: 'history',    label: `Run History (${historyRuns.length})`,                   icon: History },
  ];

  /* ── Shared style fragments ──────────────────────────────────────────── */
  const sectionHeading = {
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    color: C.cream400,
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '10px',
  };

  const inlineBtn = (bg = C.bgOverlay, border = C.borderMid, color = C.cream200) => ({
    background: bg,
    border: `1px solid ${border}`,
    borderRadius: '8px',
    color,
    fontSize: '11px',
    fontWeight: 600,
    padding: '5px 12px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    transition: 'border-color 0.15s, background 0.15s',
  });

  return (
    <div style={{ minHeight: '100vh', background: C.bgBase, color: C.cream200, fontFamily: 'Inter, ui-sans-serif, sans-serif', display: 'flex', flexDirection: 'column' }}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header style={{
        background: `${C.bgSurface}CC`,
        backdropFilter: 'blur(12px)',
        borderBottom: `1px solid ${C.borderSubtle}`,
        position: 'sticky',
        top: 0,
        zIndex: 50,
        padding: '0 28px',
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', height: 58, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Title */}
          <div>
            <h1 style={{ fontSize: '15px', fontWeight: 700, color: C.cream100, letterSpacing: '-0.01em', margin: 0 }}>
              EduGen — Self-Evaluating Lesson Pipeline
            </h1>
          </div>

          {/* Status chip */}
          {healthStatus && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: C.bgElevated,
              border: `1px solid ${C.borderSubtle}`,
              borderRadius: 8,
              padding: '5px 12px',
              fontSize: 11,
              color: C.cream400,
            }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%',
                background: healthStatus.status === 'healthy' ? C.green : C.amber,
                display: 'inline-block',
              }} />
              {healthStatus.status === 'healthy' ? 'Connected' : 'Degraded'}
            </div>
          )}
        </div>
      </header>

      {/* ── Navigation tabs ────────────────────────────────────────────── */}
      <div style={{
        background: `${C.bgSurface}99`,
        borderBottom: `1px solid ${C.borderSubtle}`,
        padding: '0 28px',
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', gap: 2 }}>
          {tabs.map(({ id, label, icon: Icon }) => {
            const active = activeTab === id;
            return (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '10px 14px',
                  fontSize: 11,
                  fontWeight: 600,
                  borderBottom: `2px solid ${active ? C.blue : 'transparent'}`,
                  color: active ? C.blue : C.cream500,
                  background: 'transparent',
                  cursor: 'pointer',
                  transition: 'color 0.15s, border-color 0.15s',
                  whiteSpace: 'nowrap',
                }}
              >
                <Icon style={{ width: 13, height: 13 }} />
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Main content ───────────────────────────────────────────────── */}
      <main style={{ flex: 1, maxWidth: 1200, width: '100%', margin: '0 auto', padding: '28px', display: 'flex', flexDirection: 'column', gap: 22 }}>

        {/* Error alert */}
        {errorMessage && (
          <div style={{ ...card(), background: C.redDim, border: `1px solid ${C.red}44`, padding: '14px 18px', display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12, color: '#E8A0A0' }}>
            <XCircle style={{ width: 16, height: 16, color: C.red, flexShrink: 0, marginTop: 1 }} />
            <div>
              <p style={{ fontWeight: 700, marginBottom: 3, color: '#E8A0A0' }}>Pipeline Error</p>
              <p style={{ color: '#D08080', margin: 0 }}>{errorMessage}</p>
            </div>
          </div>
        )}

        {/* ── TAB 1: STUDIO ──────────────────────────────────────────── */}
        {activeTab === 'studio' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>

            {/* Generator input card */}
            <div style={{ ...card(), padding: '20px 22px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 16, alignItems: 'flex-end' }}>
                {/* Topic input */}
                <div>
                  <label style={{ display: 'block', fontSize: 10, fontWeight: 700, letterSpacing: '0.09em', textTransform: 'uppercase', color: C.cream500, marginBottom: 7 }}>
                    Lesson Topic
                  </label>
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Introduction to RAG"
                    disabled={loading}
                    style={{
                      width: '100%',
                      background: C.bgBase,
                      border: `1px solid ${C.borderMid}`,
                      borderRadius: 9,
                      padding: '9px 14px',
                      fontSize: 13,
                      color: C.cream100,
                      outline: 'none',
                      fontFamily: 'inherit',
                    }}
                  />
                </div>

                {/* Inject test error toggle */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <label style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={demoError}
                      onChange={(e) => setDemoError(e.target.checked)}
                      disabled={loading}
                      style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }}
                    />
                    <div style={{
                      width: 40, height: 22, borderRadius: 11,
                      background: demoError ? C.amber : C.bgOverlay,
                      border: `1px solid ${demoError ? C.amber : C.borderMid}`,
                      position: 'relative',
                      transition: 'background 0.2s',
                      cursor: 'pointer',
                    }}>
                      <div style={{
                        position: 'absolute',
                        top: 2,
                        left: demoError ? 19 : 2,
                        width: 16, height: 16,
                        borderRadius: '50%',
                        background: '#fff',
                        transition: 'left 0.2s',
                      }} />
                    </div>
                  </label>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: demoError ? C.amber : C.cream300 }}>
                      Inject Test Error
                    </div>
                    <p style={{ fontSize: 10, color: C.cream500, margin: 0 }}>Tests evaluator rejection</p>
                  </div>
                </div>

                {/* Generate button */}
                <button
                  onClick={handleGenerate}
                  disabled={loading}
                  style={{
                    background: loading ? C.bgOverlay : C.blueMid,
                    border: `1px solid ${loading ? C.borderMid : C.blue}`,
                    borderRadius: 9,
                    color: loading ? C.cream500 : C.cream100,
                    fontWeight: 700,
                    fontSize: 12,
                    padding: '9px 20px',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex', alignItems: 'center', gap: 7,
                    whiteSpace: 'nowrap',
                    transition: 'background 0.2s, border-color 0.2s',
                    fontFamily: 'inherit',
                  }}
                >
                  {loading ? (
                    <>
                      <RefreshCw style={{ width: 14, height: 14, animation: 'spin 1s linear infinite' }} />
                      Running Pipeline...
                    </>
                  ) : (
                    'Generate & Evaluate Lesson'
                  )}
                </button>
              </div>

              {/* Test error notice */}
              {demoError && (
                <div style={{
                  marginTop: 14,
                  padding: '10px 14px',
                  background: `${C.amberDim}99`,
                  border: `1px solid ${C.amber}44`,
                  borderRadius: 9,
                  fontSize: 11,
                  color: '#D4A86A',
                  display: 'flex', alignItems: 'flex-start', gap: 8,
                }}>
                  <AlertTriangle style={{ width: 14, height: 14, color: C.amber, flexShrink: 0, marginTop: 1 }} />
                  <span>
                    <strong>Error injection active.</strong> A controlled false claim will be inserted on Attempt 1
                    to verify that the evaluator catches and rejects it before regenerating a corrected version.
                  </span>
                </div>
              )}
            </div>

            {/* Run result dashboard */}
            {currentRun && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

                {/* Status bar */}
                <div style={{ ...card(), padding: '14px 18px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    {/* Status badge */}
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      padding: '4px 12px',
                      borderRadius: 20,
                      fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em',
                      background: currentRun.status === 'PASSED' ? `${C.green}22` : `${C.red}22`,
                      border: `1px solid ${currentRun.status === 'PASSED' ? C.green : C.red}44`,
                      color: currentRun.status === 'PASSED' ? C.green : C.red,
                    }}>
                      {currentRun.status === 'PASSED'
                        ? <CheckCircle2 style={{ width: 13, height: 13 }} />
                        : <XCircle style={{ width: 13, height: 13 }} />
                      }
                      {currentRun.status}
                    </div>
                    <div style={{ fontSize: 11, color: C.cream500 }}>
                      Run: <code style={{ color: C.cream300, fontFamily: 'monospace' }}>{currentRun.run_id}</code>
                    </div>
                    <div style={{ fontSize: 11, color: C.cream500 }}>
                      Attempts: <span style={{ color: C.cream200, fontWeight: 600 }}>{currentRun.attempts_count}</span> / 3
                    </div>
                  </div>

                  {currentRun.status === 'PASSED' && currentRun.approved_lesson && (
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button onClick={handleCopyLesson} style={inlineBtn()}>
                        {copied ? <Check style={{ width: 13, height: 13, color: C.green }} /> : <Copy style={{ width: 13, height: 13 }} />}
                        {copied ? 'Copied' : 'Copy Markdown'}
                      </button>
                      <button onClick={handleDownloadLesson} style={inlineBtn(C.blueDim, C.borderActive, C.cream100)}>
                        <Download style={{ width: 13, height: 13 }} />
                        Download .md
                      </button>
                    </div>
                  )}
                </div>

                {/* Evaluation grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 18 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '7fr 5fr', gap: 18 }}>

                    {/* Rubric checkpoints */}
                    <div>
                      <div style={sectionHeading}>
                        <Shield style={{ width: 13, height: 13, color: C.blue }} />
                        Six Evaluation Rubric Dimensions
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {latestAttempt?.rubric_checkpoints?.map((rc) => {
                          const ok = rc.passed;
                          return (
                            <div
                              key={rc.checkpoint_id}
                              style={{
                                ...card(),
                                background: ok ? C.bgElevated : `${C.redDim}99`,
                                border: `1px solid ${ok ? C.borderSubtle : C.red + '44'}`,
                                padding: '11px 14px',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  {ok
                                    ? <CheckCircle2 style={{ width: 14, height: 14, color: C.green, flexShrink: 0 }} />
                                    : <XCircle style={{ width: 14, height: 14, color: C.red, flexShrink: 0 }} />
                                  }
                                  <span style={{ fontSize: 12, fontWeight: 600, color: ok ? C.cream200 : '#E8A0A0' }}>
                                    {rubricDisplayNames[rc.checkpoint_id] || rc.checkpoint_id}
                                  </span>
                                </div>
                                <span style={{
                                  fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                                  background: ok ? `${C.green}18` : `${C.red}22`,
                                  color: ok ? C.green : C.red,
                                }}>
                                  {ok ? 'PASSED' : 'FAILED'}
                                </span>
                              </div>
                              {rc.evidence && (
                                <p style={{ fontSize: 11, color: C.cream500, marginTop: 6, marginBottom: 0, paddingLeft: 22 }}>
                                  <strong style={{ color: C.cream400 }}>Evidence:</strong> {rc.evidence}
                                </p>
                              )}
                              {!ok && rc.failure_reason && (
                                <p style={{ fontSize: 11, color: '#D08080', marginTop: 4, marginBottom: 0, paddingLeft: 22 }}>
                                  <strong>Reason:</strong> {rc.failure_reason}
                                </p>
                              )}
                              {!ok && rc.correction_instruction && (
                                <p style={{ fontSize: 11, color: '#D4A86A', marginTop: 3, marginBottom: 0, paddingLeft: 22 }}>
                                  <strong>Correction:</strong> {rc.correction_instruction}
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Deterministic checks */}
                    <div>
                      <div style={sectionHeading}>
                        <Layers style={{ width: 13, height: 13, color: C.blue }} />
                        Stage A: Deterministic Checks
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                        {latestAttempt?.deterministic_checks?.map((dc) => (
                          <div
                            key={dc.check_id}
                            style={{
                              ...card(),
                              background: dc.passed ? C.bgElevated : `${C.redDim}99`,
                              border: `1px solid ${dc.passed ? C.borderSubtle : C.red + '44'}`,
                              padding: '9px 13px',
                              fontSize: 11,
                              display: 'flex', alignItems: 'flex-start', gap: 8,
                            }}
                          >
                            {dc.passed
                              ? <CheckCircle2 style={{ width: 13, height: 13, color: C.green, flexShrink: 0, marginTop: 1 }} />
                              : <XCircle style={{ width: 13, height: 13, color: C.red, flexShrink: 0, marginTop: 1 }} />
                            }
                            <div>
                              <div style={{ fontWeight: 600, color: dc.passed ? C.cream300 : '#E8A0A0' }}>{dc.name}</div>
                              {!dc.passed && dc.failure_reason && (
                                <div style={{ fontSize: 10, color: '#D08080', marginTop: 3 }}>{dc.failure_reason}</div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Lesson markdown preview */}
                <div style={{ ...card(), padding: '22px 24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${C.borderSubtle}`, paddingBottom: 14, marginBottom: 16 }}>
                    <h2 style={{ fontSize: 13, fontWeight: 700, color: C.cream100, display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
                      <BookOpen style={{ width: 15, height: 15, color: C.blue }} />
                      {currentRun.status === 'PASSED' ? 'Approved Lesson Content' : 'Latest Rejected Draft'}
                    </h2>
                    {currentRun.status !== 'PASSED' && (
                      <span style={{ fontSize: 10, fontWeight: 700, color: C.red, background: `${C.red}18`, border: `1px solid ${C.red}44`, padding: '3px 10px', borderRadius: 10 }}>
                        Publication Blocked
                      </span>
                    )}
                  </div>
                  <pre style={{
                    fontSize: 12,
                    color: C.cream300,
                    whiteSpace: 'pre-wrap',
                    lineHeight: 1.7,
                    fontFamily: 'ui-monospace, monospace',
                    background: C.bgBase,
                    padding: '18px 20px',
                    borderRadius: 10,
                    border: `1px solid ${C.borderSubtle}`,
                    margin: 0,
                    overflowX: 'auto',
                  }}>
                    {latestAttempt?.draft_markdown || 'No content available.'}
                  </pre>
                </div>

                {/* Feedback */}
                {currentRun.status === 'PASSED' && (
                  <div style={{ ...card(), padding: '18px 22px' }}>
                    <h3 style={{ ...sectionHeading, marginBottom: 12 }}>Reviewer Feedback</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        {[1,2,3,4,5].map((star) => (
                          <button
                            key={star}
                            onClick={() => setFeedbackRating(star)}
                            style={{ fontSize: 18, background: 'none', border: 'none', cursor: 'pointer', color: star <= feedbackRating ? C.amber : C.bgOverlay, transition: 'transform 0.1s', padding: 2 }}
                          >
                            ★
                          </button>
                        ))}
                      </div>
                      <input
                        type="text"
                        value={feedbackComment}
                        onChange={(e) => setFeedbackComment(e.target.value)}
                        placeholder="Add comments for curriculum improvement..."
                        style={{
                          flex: 1, minWidth: 180,
                          background: C.bgBase,
                          border: `1px solid ${C.borderMid}`,
                          borderRadius: 8,
                          padding: '7px 12px',
                          fontSize: 11,
                          color: C.cream200,
                          outline: 'none',
                          fontFamily: 'inherit',
                        }}
                      />
                      <button
                        onClick={handleSubmitFeedback}
                        style={inlineBtn()}
                      >
                        Submit Feedback
                      </button>
                    </div>
                    {feedbackSaved && (
                      <p style={{ fontSize: 11, color: C.green, marginTop: 8, marginBottom: 0 }}>Feedback saved.</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── TAB 2: REJECTION INSPECTOR ─────────────────────────────── */}
        {activeTab === 'rejections' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div>
              <h2 style={{ fontSize: 14, fontWeight: 700, color: C.cream100, margin: '0 0 4px' }}>Rejection Log & Regeneration Audit</h2>
              <p style={{ fontSize: 11, color: C.cream500, margin: 0 }}>
                Inspect what failed, why it failed, and what corrective feedback was sent on each retry.
              </p>
            </div>

            {currentRun?.rejection_log?.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {currentRun.rejection_log.map((rec, i) => (
                  <div key={i} style={{ ...card(), padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${C.borderSubtle}`, paddingBottom: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 6, background: `${C.red}22`, border: `1px solid ${C.red}44`, color: C.red }}>
                          Attempt {rec.attempt_number} — Rejected
                        </span>
                        <span style={{ fontSize: 10, color: C.cream500, fontFamily: 'monospace' }}>{rec.timestamp}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {rec.failed_checkpoints?.map((f, fi) => (
                          <span key={fi} style={{ fontSize: 10, fontFamily: 'monospace', padding: '2px 7px', borderRadius: 5, background: C.bgOverlay, border: `1px solid ${C.borderMid}`, color: C.cream400 }}>
                            {f}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: C.red, marginBottom: 8, marginTop: 0 }}>Failure Reasons</h4>
                      <ul style={{ paddingLeft: 18, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {rec.reasons?.map((r, ri) => (
                          <li key={ri} style={{ fontSize: 11, color: C.cream300 }}>{r}</li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h4 style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: C.amber, marginBottom: 8, marginTop: 0 }}>Corrective Feedback Sent to Next Attempt</h4>
                      <ul style={{ paddingLeft: 18, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {rec.corrective_instructions?.map((ci, cii) => (
                          <li key={cii} style={{ fontSize: 11, color: C.cream300 }}>{ci}</li>
                        ))}
                      </ul>
                    </div>

                    <div style={{ background: C.bgBase, borderRadius: 9, border: `1px solid ${C.borderSubtle}`, padding: '12px 14px' }}>
                      <h4 style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: C.cream500, marginBottom: 8, marginTop: 0 }}>Rejected Draft Excerpt</h4>
                      <pre style={{ fontSize: 11, color: C.cream400, whiteSpace: 'pre-wrap', fontFamily: 'monospace', margin: 0 }}>{rec.draft_snippet}</pre>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ ...card(), padding: '48px 24px', textAlign: 'center' }}>
                <CheckCircle2 style={{ width: 36, height: 36, color: C.green, margin: '0 auto 10px' }} />
                <p style={{ fontSize: 13, fontWeight: 600, color: C.cream200, margin: '0 0 4px' }}>No Rejections in Current Run</p>
                <p style={{ fontSize: 11, color: C.cream500, margin: 0 }}>
                  The lesson cleared all checks on its initial attempt, or no run has been executed yet.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: MEMORY & SELF-EVOLUTION ─────────────────────────── */}
        {activeTab === 'memory' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
            <div>
              <h2 style={{ fontSize: 14, fontWeight: 700, color: C.cream100, margin: '0 0 4px' }}>Cross-Run Memory & Self-Evolution</h2>
              <p style={{ fontSize: 11, color: C.cream500, margin: 0 }}>
                Learned editorial rules extracted from recurring failures and approved by curriculum engineers.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              {/* Rules */}
              <div>
                <div style={sectionHeading}>Learned Guidance Rules ({rules.length})</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {rules.map((rule) => (
                    <div key={rule.id} style={{ ...card(), padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: 10, fontFamily: 'monospace', padding: '2px 7px', borderRadius: 5, background: C.bgOverlay, border: `1px solid ${C.borderMid}`, color: C.blue }}>
                          {rule.category.toUpperCase()}
                        </span>
                        <span style={{
                          fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                          background: rule.status === 'APPROVED' ? `${C.green}18` : rule.status === 'REJECTED' ? `${C.red}18` : `${C.amber}18`,
                          color: rule.status === 'APPROVED' ? C.green : rule.status === 'REJECTED' ? C.red : C.amber,
                        }}>
                          {rule.status} (x{rule.evidence_count})
                        </span>
                      </div>
                      <p style={{ fontSize: 11, color: C.cream200, margin: 0 }}>{rule.rule_text}</p>
                      {rule.status === 'CANDIDATE' && (
                        <div style={{ display: 'flex', gap: 8, borderTop: `1px solid ${C.borderSubtle}`, paddingTop: 8 }}>
                          <button onClick={() => handleReviewRule(rule.id, 'APPROVED')} style={inlineBtn(`${C.green}22`, `${C.green}44`, C.green)}>
                            Approve
                          </button>
                          <button onClick={() => handleReviewRule(rule.id, 'REJECTED')} style={inlineBtn()}>
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Proposals */}
              <div>
                <div style={sectionHeading}>Prompt & Rubric Evolution Proposals ({proposals.length})</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {proposals.map((prop) => (
                    <div key={prop.id} style={{ ...card(), padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: C.cream100 }}>{prop.title}</span>
                        <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10, background: `${C.blue}18`, color: C.blue }}>{prop.target}</span>
                      </div>
                      <p style={{ fontSize: 11, color: C.cream300, margin: 0 }}>{prop.description}</p>
                      <div style={{ background: C.bgBase, borderRadius: 7, border: `1px solid ${C.borderSubtle}`, padding: '8px 11px', fontSize: 10, fontFamily: 'monospace', color: C.blue }}>
                        {prop.proposed_diff}
                      </div>
                      {prop.status === 'PENDING' && (
                        <div style={{ display: 'flex', gap: 8, borderTop: `1px solid ${C.borderSubtle}`, paddingTop: 8 }}>
                          <button onClick={() => handleReviewProposal(prop.id, 'APPROVED')} style={inlineBtn(`${C.green}22`, `${C.green}44`, C.green)}>
                            Approve
                          </button>
                          <button onClick={() => handleReviewProposal(prop.id, 'REJECTED')} style={inlineBtn()}>
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 4: GROUNDING SOURCES ────────────────────────────────── */}
        {activeTab === 'sources' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
            <div>
              <h2 style={{ fontSize: 14, fontWeight: 700, color: C.cream100, margin: '0 0 4px' }}>Curated Primary Grounding Sources</h2>
              <p style={{ fontSize: 11, color: C.cream500, margin: 0 }}>
                Authoritative reference pack for Introduction to RAG with verified claims and publication metadata.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {[
                {
                  id: 'REF-01',
                  title: 'Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al. 2020)',
                  url: 'https://arxiv.org/abs/2005.11401',
                  claims: [
                    'Combines parametric (weights) and non-parametric (vector index) memory.',
                    'Retrieval happens dynamically at inference time; does NOT modify model weights.',
                  ],
                },
                {
                  id: 'REF-02',
                  title: 'LlamaIndex Core Concepts: Chunking, Embeddings & Vector Search',
                  url: 'https://docs.llamaindex.ai/en/stable/getting_started/concepts/',
                  claims: [
                    'Splits long text into manageable chunks.',
                    'Converts text into numerical embeddings representing semantic meaning.',
                  ],
                },
                {
                  id: 'REF-03',
                  title: 'LangChain Documentation: RAG Architecture & Context Injection',
                  url: 'https://python.langchain.com/docs/tutorials/rag/',
                  claims: [
                    'Two phases: Ingestion (chunk, embed, store) and Generation (retrieve, inject, prompt).',
                    'Allows models to query private data without retraining.',
                  ],
                },
                {
                  id: 'REF-04',
                  title: 'Anthropic Prompt Engineering: Grounding & Hallucination Mitigations',
                  url: 'https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview',
                  claims: [
                    'RAG reduces hallucinations but cannot mathematically guarantee 100% accuracy.',
                    'Evaluation rubrics are required to detect retrieval gaps.',
                  ],
                },
              ].map((s) => (
                <div key={s.id} style={{ ...card(), padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'monospace', color: C.blue }}>[{s.id}]</span>
                    <a href={s.url} target="_blank" rel="noopener noreferrer"
                      style={{ fontSize: 11, color: C.cream500, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
                      Source <ExternalLink style={{ width: 11, height: 11 }} />
                    </a>
                  </div>
                  <h4 style={{ fontSize: 11, fontWeight: 600, color: C.cream200, margin: 0 }}>{s.title}</h4>
                  <ul style={{ paddingLeft: 16, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {s.claims.map((c, ci) => (
                      <li key={ci} style={{ fontSize: 10, color: C.cream500 }}>{c}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            {/* Content maintenance */}
            <div style={{ borderTop: `1px solid ${C.borderSubtle}`, paddingTop: 20 }}>
              <div style={sectionHeading}>Content Defect & Maintenance Tracker</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {contentIssues.map((issue) => (
                  <div key={issue.id} style={{ ...card(), padding: '10px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: 11 }}>
                      <span style={{ fontWeight: 700, color: C.amber, marginRight: 8 }}>[{issue.issue_type}]</span>
                      <span style={{ color: C.cream300 }}>{issue.description}</span>
                    </div>
                    <span style={{ fontSize: 10, fontFamily: 'monospace', padding: '2px 8px', borderRadius: 5, background: C.bgOverlay, border: `1px solid ${C.borderMid}`, color: C.cream400 }}>
                      {issue.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 5: RUN HISTORY ──────────────────────────────────────── */}
        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <h2 style={{ fontSize: 14, fontWeight: 700, color: C.cream100, margin: 0 }}>Historical Generation Runs</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {historyRuns.map((r) => (
                <div
                  key={r.run_id}
                  onClick={() => handleLoadRun(r.run_id)}
                  style={{
                    ...card(),
                    padding: '13px 16px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = C.borderActive}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = C.borderSubtle}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{
                      width: 9, height: 9, borderRadius: '50%',
                      background: r.status === 'PASSED' ? C.green : C.red,
                      display: 'inline-block', flexShrink: 0,
                    }} />
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: C.cream100 }}>{r.topic}</div>
                      <div style={{ fontSize: 10, color: C.cream500, fontFamily: 'monospace', marginTop: 2 }}>{r.run_id}</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 11 }}>
                    <span style={{ color: C.cream500 }}>{r.attempts_count} attempt(s)</span>
                    {r.deliberate_error_injected && (
                      <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6, background: `${C.amber}18`, border: `1px solid ${C.amber}44`, color: C.amber }}>
                        Error Injected
                      </span>
                    )}
                    <span style={{ fontWeight: 700, color: r.status === 'PASSED' ? C.green : C.red }}>
                      {r.status}
                    </span>
                    <ChevronRight style={{ width: 15, height: 15, color: C.cream500 }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </main>

      {/* CSS for loading spinner */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
