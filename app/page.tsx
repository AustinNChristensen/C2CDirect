const repoUrl = process.env.NEXT_PUBLIC_SOURCE_URL ?? 'https://github.com/AustinNChristensen/C2CDirect';

const ArrowIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 20 20">
    <path d="M4 10h11M11 5l5 5-5 5" />
  </svg>
);

const CheckIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 20 20">
    <path d="m4 10 4 4 8-9" />
  </svg>
);

const Mark = () => (
  <span className="landingMark" aria-hidden="true">
    C2C<span>D</span>
  </span>
);

export default function LandingPage() {
  return (
    <main className="landingPage">
      <nav className="landingNav" aria-label="Primary navigation">
        <a className="landingBrand" href="#top" aria-label="C2CDirect home">
          <Mark />
          <span>C2CDirect</span>
        </a>
        <div className="landingNavLinks">
          <a href="#product">Product</a>
          <a href="#bring-your-own-ai">Bring your own AI</a>
          <a href="#deploy-core">Open Core</a>
          <a href="#hosted">Hosted</a>
        </div>
        <a className="navCta" href="/core">
          Open Core <ArrowIcon />
        </a>
      </nav>

      <section className="landingHero" id="top">
        <div className="heroNoise" aria-hidden="true" />
        <div className="heroCopy">
          <p className="eyebrow"><span /> Open-source opportunity intelligence</p>
          <h1>
            Find the contract.<br />
            <em>Verify the chain.</em><br />
            Win the work.
          </h1>
          <p className="heroLede">
            C2CDirect is the contract pursuit system built for independent engineers.
            It turns noisy job feeds into evidence-backed C2C opportunities—and keeps
            every application, recruiter, decision, and dollar in one pipeline.
          </p>
          <div className="heroActions">
            <a className="primaryLandingButton" href="/core">
              Explore the core product <ArrowIcon />
            </a>
            <a className="textLandingButton" href="#deploy-core">
              Self-host C2CDirect Core
            </a>
          </div>
          <div className="heroProof" aria-label="Core product attributes">
            <span><CheckIcon /> AGPL-3.0 Core</span>
            <span><CheckIcon /> Your infrastructure</span>
            <span><CheckIcon /> Your model</span>
          </div>
        </div>

        <div className="productPreview" aria-label="C2CDirect product preview">
          <div className="previewChrome">
            <span className="previewLogo">C2CDirect</span>
            <div className="previewTabs"><b>Opportunities</b><span>Pipeline</span><span>Control Room</span></div>
            <span className="previewLive"><i /> Live</span>
          </div>
          <div className="previewBody">
            <div className="previewHeader">
              <div><small>OPPORTUNITY FEED</small><strong>Best work, first.</strong></div>
              <button>Scan sources <span>↗</span></button>
            </div>
            <div className="previewFilters">
              <span>AI / ML <b>×</b></span><span>Remote <b>×</b></span><span>$130+/hr <b>×</b></span>
            </div>
            <article className="previewJob previewJobActive">
              <div className="previewScore"><strong>94</strong><small>FIT</small></div>
              <div className="previewJobMain">
                <div><small>NORTHSTAR HEALTH · 18M AGO</small><strong>Senior AI Application Engineer</strong></div>
                <b className="confirmed">C2C CONFIRMED</b>
                <p>$155–175/hr · Remote · 12 months</p>
                <div><span>TypeScript</span><span>Python</span><span>LangGraph</span></div>
              </div>
            </article>
            <article className="previewJob">
              <div className="previewScore"><strong>91</strong><small>FIT</small></div>
              <div className="previewJobMain">
                <div><small>SUMMIT COMMERCE · 42M AGO</small><strong>Staff Full-Stack Engineer</strong></div>
                <b className="confirmed">C2C CONFIRMED</b>
                <p>$140–160/hr · Hybrid · 9 months</p>
                <div><span>Next.js</span><span>AWS</span><span>Systems</span></div>
              </div>
            </article>
            <div className="previewDetail">
              <small>WHY THIS MATCHED</small>
              <strong>Evidence, not a black box.</strong>
              <ul><li>Above target rate</li><li>Direct-vendor language</li><li>Strong agent engineering fit</li></ul>
              <div className="confidenceMeter"><span><i /></span><b>95% confidence</b></div>
            </div>
          </div>
          <div className="previewGlow" aria-hidden="true" />
        </div>
      </section>

      <section className="signalBar" aria-label="C2CDirect capabilities">
        <p>Built for the contract market—not retrofitted from a full-time job board.</p>
        <div>
          <span><b>01</b> C2C verification</span>
          <span><b>02</b> Rate extraction</span>
          <span><b>03</b> Vendor-chain evidence</span>
          <span><b>04</b> Pursuit learning</span>
        </div>
      </section>

      <section className="productStory sectionShell" id="product">
        <div className="sectionIntro">
          <p className="eyebrow darkEyebrow"><span /> One operating system</p>
          <h2>From scattered listings<br />to a focused pursuit.</h2>
          <p>
            C2CDirect does more than collect jobs. It creates a feedback loop around
            the work you actually want, the terms you will accept, and the sources
            that consistently produce real opportunities.
          </p>
        </div>
        <div className="storyGrid">
          <article>
            <span className="storyNumber">01</span>
            <div className="storyIcon">⌁</div>
            <h3>Intake every signal</h3>
            <p>Normalize job feeds, recruiter messages, ATS listings, and direct imports into one evidence-backed record.</p>
            <ul><li>Source provenance</li><li>Rate and term extraction</li><li>Technology normalization</li></ul>
          </article>
          <article>
            <span className="storyNumber">02</span>
            <div className="storyIcon">◎</div>
            <h3>Qualify what is real</h3>
            <p>Separate confirmed C2C work from weak signals, duplicate posts, and vendor-chain ambiguity.</p>
            <ul><li>C2C confidence</li><li>Fit and seniority scoring</li><li>Recruiter discovery</li></ul>
          </article>
          <article>
            <span className="storyNumber">03</span>
            <div className="storyIcon">↗</div>
            <h3>Run the pursuit</h3>
            <p>Move the best work through a living pipeline and record why you applied, passed, or were denied.</p>
            <ul><li>Application pipeline</li><li>Decision feedback</li><li>Model-ready outcomes</li></ul>
          </article>
        </div>
      </section>

      <section className="aiSection" id="bring-your-own-ai">
        <div className="aiGrid">
          <div className="aiCopy">
            <p className="eyebrow"><span /> Model freedom, by design</p>
            <h2>Bring the AI<br />you already trust.</h2>
            <p>
              C2CDirect Core is model-agnostic. Connect an OpenAI-compatible endpoint,
              run a local model, or start in deterministic mode without an AI bill.
              Your provider can change without rebuilding your workflow.
            </p>
            <div className="aiBullets">
              <div><CheckIcon /><span><b>OpenAI-compatible</b><small>Use a hosted provider or your own inference gateway.</small></span></div>
              <div><CheckIcon /><span><b>Local-first option</b><small>Keep sensitive candidate and opportunity data on your machine.</small></span></div>
              <div><CheckIcon /><span><b>Visible cost controls</b><small>See usage, budgets, and model spending in Control Room.</small></span></div>
            </div>
          </div>
          <div className="controlPreview">
            <div className="controlTop"><span>CONTROL ROOM</span><b><i /> Runtime healthy</b></div>
            <h3>Your model. Your limits.</h3>
            <div className="controlMetrics">
              <div><small>TODAY</small><strong>$0.84</strong><span>12 runs</span></div>
              <div><small>THIS MONTH</small><strong>$18.40</strong><span>284 runs</span></div>
              <div><small>AVG. RUN</small><strong>$0.07</strong><span>within policy</span></div>
            </div>
            <div className="modelRoute">
              <div><span className="routeDot" /> <b>C2CDirect</b><small>screen opportunity</small></div>
              <span className="routeLine" />
              <div><span className="routeDot lime" /> <b>Your endpoint</b><small>openai-compatible / v1</small></div>
            </div>
            <div className="policyRows">
              <span><small>Daily budget</small><b>$5.00</b></span>
              <span><small>Per-run ceiling</small><b>$0.25</b></span>
              <span><small>Approval threshold</small><b>$0.15</b></span>
            </div>
          </div>
        </div>
      </section>

      <section className="coreSection sectionShell" id="deploy-core">
        <div className="coreHeading">
          <div>
            <p className="eyebrow darkEyebrow"><span /> C2CDirect Core</p>
            <h2>Own the whole stack.</h2>
          </div>
          <p>
            Core ships as a self-hosted web app, API, PostgreSQL database, and model
            runtime. Start small on one machine, then adapt it to your infrastructure.
          </p>
        </div>
        <div className="installPanel">
          <div className="installSteps">
            <article><span>01</span><div><b>Get the repository</b><p>Clone C2CDirect from GitHub and keep the full stack on infrastructure you control.</p></div></article>
            <article><span>02</span><div><b>Choose your runtime</b><p>Use deterministic mode or configure any OpenAI-compatible model endpoint.</p></div></article>
            <article><span>03</span><div><b>Launch locally</b><p>The guided setup prepares your database, app, API, and Control Room.</p></div></article>
          </div>
          <div className="terminalCard" aria-label="Core installation example">
            <div className="terminalBar"><i /><i /><i /><span>c2cdirect — setup</span></div>
            <pre><span>$</span> git clone https://github.com/AustinNChristensen/C2CDirect.git{"\n"}<span>$</span> cd C2CDirect{"\n"}<span>$</span> ./scripts/setup-core.sh{"\n\n"}<em>✓</em> Database ready{"\n"}<em>✓</em> C2CDirect Core running{"\n"}<em>→</em> http://localhost:8080</pre>
            {repoUrl ? (
              <a className="repoButton" href={repoUrl} target="_blank" rel="noreferrer">
                View repository <ArrowIcon />
              </a>
            ) : (
              <span className="repoButton repoButtonSoon">Git repository · Coming soon</span>
            )}
          </div>
        </div>
        <div className="coreFacts">
          <span>Docker-ready</span><span>PostgreSQL</span><span>OpenAI-compatible</span><span>Observable</span><span>Self-hosted</span>
        </div>
      </section>

      <section className="hostedSection" id="hosted">
        <div className="hostedHalo" aria-hidden="true" />
        <div className="hostedCard">
          <div className="soonPill">COMING SOON</div>
          <p className="eyebrow"><span /> C2CDirect Hosted</p>
          <h2>All the signal.<br />None of the setup.</h2>
          <p>
            A managed C2CDirect experience is on the way—with hosted infrastructure,
            automatic updates, connected intake, and a faster path from first signal
            to first application.
          </p>
          <div className="hostedFeatures">
            <span><CheckIcon /> Managed deployment</span>
            <span><CheckIcon /> Connected opportunity sources</span>
            <span><CheckIcon /> Automatic product updates</span>
          </div>
          <button disabled>Hosted access coming soon</button>
        </div>
      </section>

      <section className="finalCta">
        <div>
          <p className="eyebrow"><span /> Built for independent engineers</p>
          <h2>Stop browsing.<br />Start pursuing.</h2>
        </div>
        <div>
          <p>Run C2CDirect Core on your own infrastructure today, with your own model and your own rules.</p>
          <a className="primaryLandingButton lightButton" href="/core">Explore C2CDirect Core <ArrowIcon /></a>
        </div>
      </section>

      <footer className="landingFooter">
        <a className="landingBrand" href="#top"><Mark /><span>C2CDirect</span></a>
        <p>Opportunity intelligence for independent engineers.</p>
        <div><a href="#product">Product</a><a href="#deploy-core">Core</a><a href="#hosted">Hosted</a></div>
        <small>© 2026 C2CDirect. Core licensed AGPL-3.0.</small>
      </footer>
    </main>
  );
}
