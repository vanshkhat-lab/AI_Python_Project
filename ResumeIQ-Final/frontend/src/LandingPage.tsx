import type { FormEvent } from "react";
import "./landing.css";
import { LegalLinks } from "./LegalPages";

type AuthMode = "login" | "signup";

type LandingPageProps = {
  mode: AuthMode;
  email: string;
  password: string;
  busy: boolean;
  message: string;
  onModeChange: (mode: AuthMode) => void;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

const steps = [
  {
    number: "01",
    title: "Add your resume",
    description: "Upload a PDF or DOCX resume, or paste your resume text.",
  },
  {
    number: "02",
    title: "Paste the job description",
    description: "Choose the position you want to compare your resume against.",
  },
  {
    number: "03",
    title: "Review your match",
    description: "Explore evidence-backed matches, skill gaps and suggestions.",
  },
];

const features = [
  {
    symbol: "◎",
    title: "Resume-to-job matching",
    description: "Compare resume details with the requirements of a specific role.",
  },
  {
    symbol: "▤",
    title: "Evidence you can inspect",
    description: "Understand which requirements your resume supports and where evidence is missing.",
  },
  {
    symbol: "✧",
    title: "Actionable improvements",
    description: "Discover gaps to address before tailoring your next application.",
  },
  {
    symbol: "↗",
    title: "Downloadable results",
    description: "Keep a copy of your analysis as text or JSON to review later.",
  },
];

export default function LandingPage({
  mode,
  email,
  password,
  busy,
  message,
  onModeChange,
  onEmailChange,
  onPasswordChange,
  onSubmit,
}: LandingPageProps) {
  const goToAccount = (nextMode: AuthMode) => {
    onModeChange(nextMode);
    document.getElementById("resumeiq-auth")?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  };

  return (
    <div className="ri-page">
      <header className="ri-header">
        <a className="ri-brand" href="#top" aria-label="ResumeIQ home">
          <span className="ri-brand-icon">R</span>
          <span>Resume<span className="ri-brand-highlight">IQ</span></span>
        </a>
        <nav className="ri-nav" aria-label="Main navigation">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
          <a href="#pricing">Pricing</a>
        </nav>
        <div className="ri-nav-actions">
          <button type="button" className="ri-link-button" onClick={() => goToAccount("login")}>Log in</button>
          <button type="button" className="ri-button ri-button-small" onClick={() => goToAccount("signup")}>Get started</button>
        </div>
      </header>

      <main id="top">
        <section className="ri-hero ri-container" aria-labelledby="ri-hero-title">
          <div className="ri-hero-text">
            <span className="ri-eyebrow"><span className="ri-status-dot" /> Your next application, with more clarity</span>
            <h1 id="ri-hero-title">
              Make your resume <span>work harder</span> for every job.
            </h1>
            <p className="ri-hero-description">
              Compare your resume with a job description, see how your experience matches the requirements,
              and find practical opportunities to improve.
            </p>
            <div className="ri-hero-actions">
              <button type="button" className="ri-button ri-button-large" onClick={() => goToAccount("signup")}>
                Analyze my resume <span aria-hidden="true">→</span>
              </button>
              <a className="ri-secondary-link" href="#how-it-works">See how it works <span aria-hidden="true">↗</span></a>
            </div>
            <div className="ri-hero-note">
              <span aria-hidden="true" className="ri-check">✓</span>
              2 free analyses with a new account
              <span className="ri-separator" aria-hidden="true">·</span>
              No card required to start
            </div>
          </div>

          <div className="ri-preview-wrap">
            <div className="ri-orb ri-orb-one" aria-hidden="true" />
            <div className="ri-orb ri-orb-two" aria-hidden="true" />
            <div className="ri-preview" aria-label="Illustrative resume analysis example">
              <div className="ri-preview-top">
                <span className="ri-preview-brand"><span className="ri-mini-mark">R</span> Resume analysis</span>
                <span className="ri-demo-tag">Example preview</span>
              </div>
              <div className="ri-preview-heading">
                <div>
                  <span className="ri-preview-caption">MATCH OVERVIEW</span>
                  <h2>Software Developer</h2>
                  <p>Compare skills and supporting experience</p>
                </div>
                <div className="ri-score">
                  <span>72<small>/100</small></span>
                  <span>Sample match</span>
                </div>
              </div>
              <div className="ri-preview-divider" />
              <div className="ri-preview-row">
                <span className="ri-preview-row-name"><span className="ri-row-dot ri-dot-green" /> Python</span>
                <span className="ri-match ri-positive">Supported</span>
              </div>
              <div className="ri-preview-row">
                <span className="ri-preview-row-name"><span className="ri-row-dot ri-dot-green" /> SQL</span>
                <span className="ri-match ri-positive">Supported</span>
              </div>
              <div className="ri-preview-row">
                <span className="ri-preview-row-name"><span className="ri-row-dot ri-dot-amber" /> Docker</span>
                <span className="ri-match ri-needs-review">Missing evidence</span>
              </div>
              <div className="ri-preview-insight">
                <span className="ri-insight-symbol" aria-hidden="true">✧</span>
                <div>
                  <strong>Know what to improve</strong>
                  <p>Use the gaps in your report to tailor your resume to the role.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="ri-section ri-container" aria-labelledby="ri-features-title">
          <div className="ri-section-head">
            <span className="ri-overline">BUILT FOR JOB SEEKERS</span>
            <h2 id="ri-features-title">A clearer picture of your resume</h2>
            <p>Less guesswork when preparing your next application.</p>
          </div>
          <div className="ri-feature-grid">
            {features.map((feature) => (
              <article className="ri-feature-card" key={feature.title}>
                <span className="ri-feature-icon" aria-hidden="true">{feature.symbol}</span>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="how-it-works" className="ri-section ri-how" aria-labelledby="ri-how-title">
          <div className="ri-container">
            <div className="ri-section-head">
              <span className="ri-overline">HOW IT WORKS</span>
              <h2 id="ri-how-title">Three simple steps</h2>
              <p>From resume upload to a clearer understanding of the role.</p>
            </div>
            <div className="ri-steps">
              {steps.map((step) => (
                <article className="ri-step" key={step.number}>
                  <span className="ri-step-number">{step.number}</span>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="pricing" className="ri-section ri-container" aria-labelledby="ri-pricing-title">
          <div className="ri-section-head">
            <span className="ri-overline">SIMPLE PRICING</span>
            <h2 id="ri-pricing-title">Try it free. Add credits when you need more.</h2>
            <p>No recurring subscription required for the planned credit pack.</p>
          </div>
          <div className="ri-pricing-grid">
            <article className="ri-price-card">
              <span className="ri-plan-name">Starter</span>
              <div className="ri-price-value">₹0</div>
              <p>Start exploring resume-job matching.</p>
              <div className="ri-price-rule" />
              <ul>
                <li>2 free analyses on signup</li>
                <li>Resume-to-job comparison</li>
                <li>Skill gaps and match details</li>
              </ul>
              <button type="button" className="ri-button ri-button-outline" onClick={() => goToAccount("signup")}>
                Create free account
              </button>
            </article>
            <article className="ri-price-card ri-price-featured">
              <span className="ri-pricing-badge">PAY AS YOU GO</span>
              <span className="ri-plan-name">Credit pack</span>
              <div className="ri-price-value">₹99 <small>one-time</small></div>
              <p>More analyses when you're ready to apply.</p>
              <div className="ri-price-rule" />
              <ul>
                <li>5 additional analysis credits</li>
                <li>One-time purchase, no subscription</li>
                <li>Credits added after verified payment</li>
              </ul>
              <button type="button" className="ri-button" onClick={() => goToAccount("login")}>
                Sign in to view credits
              </button>
              <p className="ri-price-test-note">Checkout is currently in test mode. Live purchases are not available yet.</p>
            </article>
          </div>
        </section>

        <section id="resumeiq-auth" className="ri-account-section" aria-labelledby="ri-auth-title">
          <div className="ri-container ri-account-grid">
            <div className="ri-account-copy">
              <span className="ri-overline">GET STARTED</span>
              <h2>Make your next application more informed.</h2>
              <p>Create an account and start with two free analyses, or log in to continue where you left off.</p>
            </div>
            <div className="ri-auth-card">
              <div className="ri-auth-tabs" role="group" aria-label="Account action">
                <button
                  type="button"
                  aria-pressed={mode === "signup"}
                  className={mode === "signup" ? "ri-tab ri-tab-active" : "ri-tab"}
                  onClick={() => onModeChange("signup")}
                >Create account</button>
                <button
                  type="button"
                  aria-pressed={mode === "login"}
                  className={mode === "login" ? "ri-tab ri-tab-active" : "ri-tab"}
                  onClick={() => onModeChange("login")}
                >Log in</button>
              </div>
              <h3 id="ri-auth-title">{mode === "signup" ? "Create your free account" : "Welcome back"}</h3>
              <p className="ri-auth-subtitle">{mode === "signup" ? "Get 2 analyses to try ResumeIQ." : "Sign in to access your ResumeIQ dashboard."}</p>
              <form onSubmit={onSubmit} className="ri-auth-form">
                <label htmlFor="ri-email">Email address</label>
                <input
                  id="ri-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => onEmailChange(event.target.value)}
                  placeholder="you@example.com"
                  required
                />
                <label htmlFor="ri-password">Password</label>
                <input
                  id="ri-password"
                  type="password"
                  autoComplete={mode === "signup" ? "new-password" : "current-password"}
                  value={password}
                  onChange={(event) => onPasswordChange(event.target.value)}
                  minLength={6}
                  required
                />
                <button type="submit" className="ri-button" disabled={busy}>
                  {busy ? "Please wait…" : mode === "signup" ? "Create account" : "Log in"}
                </button>
              </form>
              {message && <p role="status" aria-live="polite" className="ri-auth-message">{message}</p>}
              <p className="ri-auth-footnote">
                {mode === "signup" ? "Already have an account?" : "New to ResumeIQ?"}{" "}
                <button
                  type="button"
                  className="ri-auth-inline"
                  onClick={() => onModeChange(mode === "signup" ? "login" : "signup")}
                >{mode === "signup" ? "Log in" : "Create an account"}</button>
              </p>
            </div>
          </div>
        </section>
      </main>
      <footer className="ri-footer">
        <div className="ri-container ri-footer-inner">
          <a className="ri-brand" href="#top"><span className="ri-brand-icon">R</span><span>Resume<span className="ri-brand-highlight">IQ</span></span></a>
          <p>© {new Date().getFullYear()} ResumeIQ. Resume insights are informational and do not guarantee hiring outcomes.</p>
          <LegalLinks className="ri-footer-policies" />
        </div>
      </footer>
    </div>
  );
}
